import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Composer } from '@/components/chat/Composer'
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
    expect(screen.getByText('Synthetic example')).toBeInTheDocument()
    expect(screen.getByText('CC0-1.0')).toBeInTheDocument()
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
