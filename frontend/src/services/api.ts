import type {
  ApiErrorBody,
  ChatRequest,
  ChatResponse,
  ConversationDetail,
  ConversationList,
  HealthResponse,
  IngestionErrors,
  KnowledgeStats,
  ModelStatus,
  RebuildInfo,
  RetrievalTestResponse,
  RuntimeSettings,
  SafetyStatus,
  SettingsResponse,
  SourceDetail,
  SourcePage,
} from '@/types/api'
import { getClientId } from '@/services/clientId'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly retryable: boolean

  constructor(status: number, code: string, message: string, retryable = false) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.retryable = retryable
  }
}

const BASE = '/api'

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as ApiErrorBody
    return new ApiError(res.status, body.error.code, body.error.message, body.error.retryable)
  } catch {
    return new ApiError(res.status, 'http_error', `The local server returned an error (HTTP ${res.status}).`)
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        'X-Client-Id': getClientId(),
        ...(init.headers ?? {}),
      },
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError(0, 'backend_unreachable', 'The CoupleCare backend is not running on this computer.', true)
  }
  if (!res.ok) throw await parseError(res)
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

const json = (body: unknown) => JSON.stringify(body)

/** Upload a recording for speech-to-text (cloud mode only). The browser sets the multipart boundary. */
async function transcribe(audio: Blob, language: 'auto' | 'en' | 'bn'): Promise<string> {
  const form = new FormData()
  const type = audio.type.split(';')[0] || 'audio/webm'
  form.append('file', audio, `recording.${type.includes('ogg') ? 'ogg' : type.includes('mp4') ? 'm4a' : 'webm'}`)
  form.append('language', language)
  let res: Response
  try {
    res = await fetch(`${BASE}/transcribe`, { method: 'POST', body: form, headers: { 'X-Client-Id': getClientId() } })
  } catch {
    throw new ApiError(0, 'backend_unreachable', 'The CoupleCare backend is not running on this computer.', true)
  }
  if (!res.ok) throw await parseError(res)
  return ((await res.json()) as { text: string }).text
}

export const api = {
  health: () => request<HealthResponse>('/health'),
  transcribe,
  modelStatus: () => request<ModelStatus>('/model/status'),

  chat: (body: ChatRequest, signal?: AbortSignal) =>
    request<ChatResponse>('/chat', { method: 'POST', body: json(body), signal }),

  conversations: (q?: string) =>
    request<ConversationList>(`/conversations${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  conversation: (id: string) => request<ConversationDetail>(`/conversations/${id}`),
  deleteConversation: (id: string) => request<void>(`/conversations/${id}`, { method: 'DELETE' }),
  deleteAllConversations: () =>
    request<{ deleted: number }>('/conversations', { method: 'DELETE', body: json({ confirm: 'DELETE ALL' }) }),
  feedback: (conversationId: string, messageId: string, rating: 'helpful' | 'not_helpful') =>
    request<void>(`/conversations/${conversationId}/messages/${messageId}/feedback`, {
      method: 'POST',
      body: json({ rating }),
    }),

  settings: () => request<SettingsResponse>('/settings'),
  updateSettings: (values: Partial<RuntimeSettings>) =>
    request<SettingsResponse>('/settings', { method: 'PUT', body: json(values) }),
  resetSettings: () => request<SettingsResponse>('/settings/reset', { method: 'POST' }),

  knowledgeStats: () => request<KnowledgeStats>('/knowledge/stats'),
  knowledgeSources: (params: { q?: string; language?: string; topic?: string; page?: number; pageSize?: number }) => {
    const search = new URLSearchParams()
    if (params.q) search.set('q', params.q)
    if (params.language) search.set('language', params.language)
    if (params.topic) search.set('topic', params.topic)
    search.set('page', String(params.page ?? 1))
    search.set('page_size', String(params.pageSize ?? 12))
    return request<SourcePage>(`/knowledge/sources?${search}`)
  },
  knowledgeSource: (id: string) => request<SourceDetail>(`/knowledge/sources/${encodeURIComponent(id)}`),
  knowledgeErrors: () => request<IngestionErrors>('/knowledge/errors'),
  retrievalTest: (body: { query: string; top_k: number; mode: 'hybrid' | 'dense' | 'bm25'; language: string; topic?: string | null }) =>
    request<RetrievalTestResponse>('/knowledge/search', { method: 'POST', body: json(body) }),
  rebuild: () => request<{ status: string }>('/knowledge/rebuild', { method: 'POST' }),
  rebuildStatus: () => request<RebuildInfo>('/knowledge/rebuild'),
}

// ----------------------------------------------------------------------------- streaming

export type StreamEvent =
  | {
      event: 'meta'
      conversation_id: string
      detected_language: string
      response_language: string
      safety: SafetyStatus
    }
  | { event: 'delta'; text: string }
  | { event: 'done'; response: ChatResponse }
  | { event: 'error'; code: string; message: string; retryable: boolean }

/** Parse a text/event-stream body into events. Exported for tests. */
export function parseSseChunk(buffer: string): { events: StreamEvent[]; rest: string } {
  const events: StreamEvent[] = []
  const blocks = buffer.split('\n\n')
  const rest = blocks.pop() ?? ''
  for (const block of blocks) {
    const data = block
      .split('\n')
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n')
    if (!data) continue
    try {
      events.push(JSON.parse(data) as StreamEvent)
    } catch {
      // Ignore malformed frames rather than breaking the whole response.
    }
  }
  return { events, rest }
}

export async function streamChat(
  body: ChatRequest,
  onEvent: (event: StreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  let res: Response
  try {
    res = await fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Client-Id': getClientId() },
      body: json(body),
      signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiError(0, 'backend_unreachable', 'The CoupleCare backend is not running on this computer.', true)
  }
  if (!res.ok || !res.body) throw await parseError(res)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parsed = parseSseChunk(buffer)
    buffer = parsed.rest
    parsed.events.forEach(onEvent)
  }
  if (buffer.trim()) parseSseChunk(buffer + '\n\n').events.forEach(onEvent)
}
