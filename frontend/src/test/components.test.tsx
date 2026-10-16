import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Composer } from '@/components/chat/Composer'
import { ContextPanel } from '@/components/chat/ContextPanel'
import { SafetyNotice } from '@/components/chat/SafetyNotice'
import { SourceCardView } from '@/components/chat/SourceCardView'
import { ModelStatusPill } from '@/components/layout/ModelStatus'
import type { SourceCard } from '@/types/api'
import { HEALTH_OFFLINE, HEALTH_ONLINE, json, mockFetch, renderWithProviders } from '@/test/utils'

const source: SourceCard = {
  citation_id: 'S1',
  document_id: 'syn-en-communication',
  chunk_id: 'syn-en-communication::000-000',
  title: 'Feeling Unheard',
  organization: 'CoupleCare AI project (synthetic example)',
  excerpt: 'When one partner feels that the other does not listen…',
  language: 'en',
  topic: 'communication',
  url: null,
  license: 'CC0-1.0',
  section: 'Why feeling unheard hurts',
  synthetic: true,
  score: 0.68,
  cited: true,
}

describe('Composer', () => {
  it('sends on Enter, inserts a newline on Shift+Enter, and clears after sending', async () => {
    const onSend = vi.fn()
    renderWithProviders(<Composer onSend={onSend} onStop={() => {}} generating={false} />)
    const box = screen.getByLabelText('Your message')
    await userEvent.type(box, 'First line{Shift>}{Enter}{/Shift}second line')
    expect(box).toHaveValue('First line\nsecond line')
    await userEvent.keyboard('{Enter}')
    expect(onSend).toHaveBeenCalledWith('First line\nsecond line')
    expect(box).toHaveValue('')
  })

  it('validates empty input instead of sending', async () => {
    const onSend = vi.fn()
    renderWithProviders(<Composer onSend={onSend} onStop={() => {}} generating={false} />)
    await userEvent.click(screen.getByRole('button', { name: 'Send message' }))
    expect(onSend).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('Write a message first.')
  })

  it('shows a stop control while generating', async () => {
    const onStop = vi.fn()
    renderWithProviders(<Composer onSend={() => {}} onStop={onStop} generating />)
    expect(screen.queryByRole('button', { name: 'Send message' })).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: 'Stop generating' }))
    expect(onStop).toHaveBeenCalled()
  })

  it('clears the input with the clear control', async () => {
    renderWithProviders(<Composer onSend={() => {}} onStop={() => {}} generating={false} />)
    const box = screen.getByLabelText('Your message')
    await userEvent.type(box, 'draft')
    await userEvent.click(screen.getByRole('button', { name: 'Clear message' }))
    expect(box).toHaveValue('')
  })
})

describe('SourceCardView', () => {
  it('shows provenance and marks synthetic sources', () => {
    renderWithProviders(<SourceCardView source={source} />)
    expect(screen.getByText('Feeling Unheard')).toBeInTheDocument()
    // Technical details (licence, relevance, document id) stay available but out of the way.
    expect(screen.getByText('CC0-1.0').closest('details')).not.toBeNull()
    expect(screen.queryByText('Synthetic example')).toBeNull() // shown once per panel, not on every card
    expect(screen.getByRole('button', { name: 'Read more' })).toBeInTheDocument()
    expect(screen.queryByText('View original')).toBeNull() // no URL → no link
  })

  it('only links https URLs', () => {
    const { unmount } = renderWithProviders(<SourceCardView source={{ ...source, url: 'javascript:alert(1)' }} />)
    expect(screen.queryByText('View original')).toBeNull()
    unmount()
    renderWithProviders(<SourceCardView source={{ ...source, url: 'https://example.org/a' }} />)
    expect(screen.getByText('View original').closest('a')).toHaveAttribute('href', 'https://example.org/a')
  })
})

describe('ContextPanel', () => {
  it('merges passages from the same guide and explains synthetic material once', () => {
    const second = { ...source, citation_id: 'S2', chunk_id: 'syn-en-communication::001-000' }
    const other = { ...source, citation_id: 'S3', document_id: 'syn-en-trust', chunk_id: 'syn-en-trust::000-000', title: 'Trust' }
    renderWithProviders(
      <ContextPanel
        message={{ key: 'a', role: 'assistant', content: 'x', status: 'done', sources: [source, second, other] }}
        activeCitation={null}
      />,
    )
    expect(screen.getAllByText('Feeling Unheard')).toHaveLength(1)
    expect(screen.getByText('S1')).toBeInTheDocument()
    expect(screen.getByText('S2')).toBeInTheDocument()
    expect(screen.getByText('Trust')).toBeInTheDocument()
    expect(screen.getAllByText(/example material written for this project/)).toHaveLength(1)
  })
})

describe('SafetyNotice', () => {
  it('prompts for a region instead of showing numbers when none is selected', () => {
    renderWithProviders(<SafetyNotice safety={{ level: 'support', message: 'Your safety matters.', resources: [] }} />)
    expect(screen.getByRole('note')).toHaveTextContent('Your safety matters.')
    expect(screen.getByRole('link', { name: /Choose your region/ })).toHaveAttribute('href', '/settings#support-region')
  })

  it('renders verified resources with their source', () => {
    renderWithProviders(
      <SafetyNotice
        safety={{
          level: 'urgent',
          message: 'If you are in danger right now, contact your local emergency number.',
          resources: [{ name: 'Emergency 999', description: 'Police', contact: '999', url: null, region: 'Bangladesh', verified_on: '2026-10-14', source_url: 'https://example.org/src' }],
        }}
      />,
    )
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '999' })).toHaveAttribute('href', 'tel:999')
    expect(screen.getByRole('link', { name: '2026-10-14' })).toHaveAttribute('href', 'https://example.org/src')
  })

  it('renders nothing for ordinary replies', () => {
    const { container } = renderWithProviders(<SafetyNotice safety={{ level: 'none', message: null, resources: [] }} />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('ModelStatusPill', () => {
  it('reports the measured offline state', async () => {
    mockFetch({ '/api/health': () => json(HEALTH_OFFLINE) })
    renderWithProviders(<ModelStatusPill />)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('AI generation offline'))
  })

  it('reports online only when the backend says so', async () => {
    mockFetch({ '/api/health': () => json(HEALTH_ONLINE) })
    renderWithProviders(<ModelStatusPill />)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Local model online'))
  })

  it('reports a stopped backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    renderWithProviders(<ModelStatusPill />)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Backend not running'))
  })
})

describe('Voice features', () => {
  beforeEach(() => {
    vi.stubGlobal('MediaRecorder', Object.assign(function MediaRecorder() {}, { isTypeSupported: () => true }))
    Object.defineProperty(navigator, 'mediaDevices', { value: { getUserMedia: vi.fn() }, configurable: true })
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('always shows the microphone', async () => {
    mockFetch({ '/api/health': () => json({ ...HEALTH_ONLINE, voice_input: true }) })
    renderWithProviders(<Composer onSend={() => {}} onStop={() => {}} generating={false} />)
    expect(await screen.findByRole('button', { name: 'Speak your message' })).toBeInTheDocument()
  })

  it('explains cloud mode instead of recording when voice input is unavailable', async () => {
    const getUserMedia = vi.fn()
    Object.defineProperty(navigator, 'mediaDevices', { value: { getUserMedia }, configurable: true })
    mockFetch({ '/api/health': () => json({ ...HEALTH_ONLINE, voice_input: false }) })
    renderWithProviders(<Composer onSend={() => {}} onStop={() => {}} generating={false} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Speak your message' }))
    expect(getUserMedia).not.toHaveBeenCalled()
  })
})
