import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import axe from 'axe-core'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router'
import { TooltipProvider } from '@/components/ui/primitives'
import { PreferencesProvider, type Preferences } from '@/hooks/usePreferences'

export function renderWithProviders(ui: ReactElement, { route = '/', prefs }: { route?: string; prefs?: Partial<Preferences> } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <PreferencesProvider initial={{ motion: 'reduced', ...prefs }}>
        <TooltipProvider>
          <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
        </TooltipProvider>
      </PreferencesProvider>
    </QueryClientProvider>,
  )
}

/** Run axe on a container and return only serious/critical violations. */
export async function criticalA11yViolations(container: HTMLElement) {
  const results = await axe.run(container, {
    // Colour contrast needs real layout/CSS, which jsdom does not compute.
    rules: { 'color-contrast': { enabled: false }, region: { enabled: false } },
  })
  return results.violations
    .filter((v) => v.impact === 'serious' || v.impact === 'critical')
    .map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)
}

type Handler = (url: string, init?: RequestInit) => Response | Promise<Response>

/** Install a fetch mock that routes by URL substring. */
export function mockFetch(routes: Record<string, Handler>) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const key = Object.keys(routes).find((k) => url.includes(k))
    if (!key) return new Response(JSON.stringify({ error: { code: 'not_found', message: 'nf', retryable: false } }), { status: 404 })
    return routes[key](url, init)
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

export const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

export function sseResponse(events: object[]) {
  const text = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('')
  const bytes = new TextEncoder().encode(text)
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(bytes)
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

export const HEALTH_OFFLINE = { status: 'degraded', version: '0.1.0', model_server: 'offline', index: 'ready', embeddings: 'ready' }
export const HEALTH_ONLINE = { ...HEALTH_OFFLINE, status: 'ok', model_server: 'online' }
