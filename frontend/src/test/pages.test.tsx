import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import LandingPage from '@/pages/LandingPage'
import ChatPage from '@/pages/ChatPage'
import { AboutPage, PrivacyPage, SafetyPage } from '@/pages/InfoPages'
import type { ChatResponse } from '@/types/api'
import { HEALTH_OFFLINE, HEALTH_ONLINE, criticalA11yViolations, json, mockFetch, renderWithProviders, sseResponse } from '@/test/utils'

const CONV = 'a'.repeat(32)

function finalResponse(overrides: Partial<ChatResponse> = {}): ChatResponse {
  return {
    conversation_id: CONV,
    message_id: 'b'.repeat(32),
    answer: 'It sounds painful to feel unheard. Try reflective listening [S1].',
    detected_language: 'en',
    response_language: 'en',
    sources: [
      {
        citation_id: 'S1', document_id: 'syn-en-communication', chunk_id: 'c1', title: 'Feeling Unheard', organization: null,
        excerpt: 'Reflective listening means summarising…', language: 'en', topic: 'communication', url: null,
        license: 'CC0-1.0', section: null, synthetic: true, score: 0.7, cited: true,
      },
    ],
    grounded: true,
    safety: { level: 'none', message: null, resources: [] },
    needs_clarification: false,
    model_id: 'qwen3-4b-instruct-2507',
    generated: true,
    duration_ms: 1234,
    ...overrides,
  }
}

function renderChat() {
  return renderWithProviders(
    <Routes>
      <Route path="/chat" element={<ChatPage />} />
      <Route path="/chat/:conversationId" element={<ChatPage />} />
    </Routes>,
    { route: '/chat' },
  )
}

const baseRoutes = {
  '/api/conversations': () => json({ persistence_enabled: false, items: [], total: 0 }),
}

describe('Landing page', () => {
  it('renders the hero, labels the preview as illustrative and links to the chat', () => {
    renderWithProviders(<LandingPage />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Understand Each Other Better.')
    expect(screen.getByRole('figure', { name: /Illustrative preview/ })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Start a conversation/ })[0]).toHaveAttribute('href', '/chat')
  })

  it('switches the interface to Bangla', () => {
    renderWithProviders(<LandingPage />, { prefs: { uiLanguage: 'bn' } })
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('একে অপরকে')
  })

  it('has no serious accessibility violations', async () => {
    const { container } = renderWithProviders(<LandingPage />)
    expect(await criticalA11yViolations(container)).toEqual([])
  })
})

describe('Info pages', () => {
  it.each([
    ['About', AboutPage, 'How local inference works'],
    ['Privacy', PrivacyPage, 'How to delete your data'],
    ['Safety', SafetyPage, 'If you are in immediate danger'],
  ])('%s page renders its key section accessibly', async (_name, Page, heading) => {
    const { container } = renderWithProviders(<Page />)
    expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument()
    expect(await criticalA11yViolations(container)).toEqual([])
  })
})

describe('Chat page', () => {
  it('shows the welcome state and prefills (but does not send) a topic', async () => {
    const fetchMock = mockFetch({ ...baseRoutes, '/api/health': () => json(HEALTH_ONLINE) })
    renderChat()
    expect(screen.getByRole('heading', { name: 'Hello. What is on your mind?' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Feeling heard/ }))
    expect((screen.getByLabelText('Your message') as HTMLTextAreaElement).value).toContain('listen')
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/api/chat'))).toBe(false)
  })

  it('streams a grounded answer and shows its cited source', async () => {
    const fetchMock = mockFetch({
      ...baseRoutes,
      '/api/health': () => json(HEALTH_ONLINE),
      '/api/chat/stream': () =>
        sseResponse([
          { event: 'meta', conversation_id: CONV, detected_language: 'en', response_language: 'en', safety: { level: 'none', message: null, resources: [] } },
          { event: 'delta', text: 'It sounds painful to feel unheard. ' },
          { event: 'delta', text: 'Try reflective listening [S1].' },
          { event: 'done', response: finalResponse() },
        ]),
    })
    renderChat()
    await userEvent.type(screen.getByLabelText('Your message'), 'My partner does not listen to me{Enter}')
    expect(await screen.findByText(/reflective listening/)).toBeInTheDocument()
    // Citation markers are not shown in the reply text; sources are listed in the panel instead.
    expect(screen.queryByRole('button', { name: 'Sources S1' })).toBeNull()
    expect(screen.queryByText(/\[S1\]/)).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: /See where this comes from/ }))
    expect(screen.getAllByText('Feeling Unheard').length).toBeGreaterThan(0)

    const call = fetchMock.mock.calls.find(([url]) => String(url).includes('/api/chat/stream'))!
    const body = JSON.parse(String(call[1]!.body))
    expect(body).toMatchObject({ message: 'My partner does not listen to me', language: 'auto', conversation_id: null, mode: 'support' })
    expect((call[1]!.headers as Record<string, string>)['X-Client-Id']).toMatch(/^[A-Za-z0-9-]{16,64}$/)
  })

  it('shows a clear offline state with retry instead of a fake answer', async () => {
    mockFetch({
      ...baseRoutes,
      '/api/health': () => json(HEALTH_OFFLINE),
      '/api/chat/stream': () =>
        sseResponse([
          { event: 'meta', conversation_id: CONV, detected_language: 'en', response_language: 'en', safety: { level: 'none', message: null, resources: [] } },
          { event: 'error', code: 'model_offline', message: 'The local model server is not running or not reachable.', retryable: true },
        ]),
    })
    renderChat()
    await userEvent.type(screen.getByLabelText('Your message'), 'Hello there, we argue a lot{Enter}')
    const alert = (await screen.findByText('AI generation is offline')).closest('[role="alert"]') as HTMLElement
    expect(alert).not.toBeNull()
    expect(within(alert).getByRole('button', { name: /Try again/ })).toBeInTheDocument()
    await waitFor(() => expect(screen.getAllByText(/AI generation offline/).length).toBeGreaterThan(0))
  })

  it('labels pre-written safety responses as not generated', async () => {
    mockFetch({
      ...baseRoutes,
      '/api/health': () => json(HEALTH_ONLINE),
      '/api/chat/stream': () =>
        sseResponse([
          { event: 'meta', conversation_id: CONV, detected_language: 'en', response_language: 'en', safety: { level: 'urgent', message: 'If you are in danger right now, contact your local emergency number.', resources: [] } },
          { event: 'delta', text: 'I’m really concerned for your safety right now.' },
          {
            event: 'done',
            response: finalResponse({
              answer: 'I’m really concerned for your safety right now.', sources: [], grounded: false, generated: false, model_id: null,
              safety: { level: 'urgent', message: 'If you are in danger right now, contact your local emergency number.', resources: [] },
            }),
          },
        ]),
    })
    renderChat()
    await userEvent.type(screen.getByLabelText('Your message'), 'He is outside my door with a knife{Enter}')
    expect(await screen.findByText(/written in advance, not generated/)).toBeInTheDocument()
    expect(screen.getAllByRole('alert').some((el) => el.textContent?.includes('contact your local emergency number'))).toBe(true)
  })

  it('has no serious accessibility violations in the welcome state', async () => {
    mockFetch({ ...baseRoutes, '/api/health': () => json(HEALTH_ONLINE) })
    const { container } = renderChat()
    expect(await criticalA11yViolations(container)).toEqual([])
  })
})
