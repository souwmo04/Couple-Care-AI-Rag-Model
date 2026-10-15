import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, api, streamChat } from '@/services/api'
import type { ChatResponse, ConversationDetail, LanguageCode, RelationshipStage, SafetyStatus, SourceCard } from '@/types/api'

export type MessageStatus = 'streaming' | 'done' | 'error' | 'stopped'

export interface UiMessage {
  key: string
  role: 'user' | 'assistant'
  content: string
  status: MessageStatus
  messageId?: string
  sources: SourceCard[]
  safety?: SafetyStatus | null
  generated?: boolean
  fallbackReason?: 'rate_limited' | 'unavailable' | null
  grounded?: boolean
  needsClarification?: boolean
  responseLanguage?: string
  /** 'stream': the server recorded the user turn, then generation failed. 'request': it never arrived. */
  error?: { code: string; message: string; retryable: boolean; phase: 'stream' | 'request' }
  durationMs?: number
}

let counter = 0
const localKey = () => `m${Date.now().toString(36)}${(counter++).toString(36)}`

export function fromDetail(detail: ConversationDetail): UiMessage[] {
  return detail.messages.map((m) => ({
    key: m.id,
    role: m.role,
    content: m.content,
    status: 'done',
    messageId: m.id,
    sources: m.sources ?? [],
    safety: m.safety,
    generated: m.generated ?? undefined,
    grounded: m.grounded ?? undefined,
    responseLanguage: m.language ?? undefined,
  }))
}

function applyResponse(msg: UiMessage, res: ChatResponse): UiMessage {
  return {
    ...msg,
    content: res.answer,
    status: 'done',
    messageId: res.message_id,
    sources: res.sources,
    safety: res.safety,
    generated: res.generated,
    fallbackReason: res.fallback_reason ?? null,
    grounded: res.grounded,
    needsClarification: res.needs_clarification,
    responseLanguage: res.response_language,
    durationMs: res.duration_ms,
  }
}

export interface SendOptions {
  language: LanguageCode
  stage: RelationshipStage
}

export function useChat(initialConversationId: string | null, onConversationCreated?: (id: string) => void) {
  const qc = useQueryClient()
  const [conversationId, setConversationId] = useState<string | null>(initialConversationId)
  const [messages, setMessages] = useState<UiMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<ApiError | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const currentIdRef = useRef<string | null>(null)
  const messagesLoadedRef = useRef(false)
  const isGenerating = messages.some((m) => m.status === 'streaming')

  const load = useCallback(async (id: string | null) => {
    abortRef.current?.abort()
    currentIdRef.current = id
    setConversationId(id)
    setLoadError(null)
    if (!id) {
      setMessages([])
      return
    }
    setLoading(true)
    try {
      setMessages(fromDetail(await api.conversation(id)))
    } catch (err) {
      setMessages([])
      setLoadError(err instanceof ApiError ? err : new ApiError(0, 'unknown', String(err)))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // The route changes to /chat/:id right after a new conversation is created; that conversation
    // is already on screen, so only load when the id actually differs.
    if (initialConversationId !== null && initialConversationId === currentIdRef.current && messagesLoadedRef.current) return
    messagesLoadedRef.current = true
    void load(initialConversationId)
  }, [initialConversationId, load])

  useEffect(() => () => abortRef.current?.abort(), [])

  const run = useCallback(
    async (text: string, opts: SendOptions, regenerate: boolean) => {
      const controller = new AbortController()
      abortRef.current = controller
      const assistantKey = localKey()
      setMessages((prev) => {
        const base = regenerate && prev.at(-1)?.role === 'assistant' ? prev.slice(0, -1) : prev
        const withUser = regenerate
          ? base
          : [...base, { key: localKey(), role: 'user' as const, content: text, status: 'done' as const, sources: [] }]
        return [...withUser, { key: assistantKey, role: 'assistant', content: '', status: 'streaming', sources: [] }]
      })
      const patch = (fn: (m: UiMessage) => UiMessage) =>
        setMessages((prev) => prev.map((m) => (m.key === assistantKey ? fn(m) : m)))

      let createdId: string | null = null
      try {
        await streamChat(
          {
            message: text,
            conversation_id: conversationId,
            language: opts.language,
            relationship_stage: opts.stage,
            regenerate,
          },
          (event) => {
            if (event.event === 'meta') {
              createdId = event.conversation_id
              patch((m) => ({ ...m, safety: event.safety, responseLanguage: event.response_language }))
            } else if (event.event === 'delta') {
              patch((m) => ({ ...m, content: m.content + event.text }))
            } else if (event.event === 'done') {
              patch((m) => applyResponse(m, event.response))
            } else if (event.event === 'error') {
              patch((m) => ({
                ...m,
                status: 'error',
                error: { code: event.code, message: event.message, retryable: event.retryable, phase: 'stream' },
              }))
            }
          },
          controller.signal,
        )
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          patch((m) => ({ ...m, status: 'stopped' }))
        } else {
          const e = err instanceof ApiError ? err : new ApiError(0, 'unknown', 'Something went wrong.')
          patch((m) => ({
            ...m,
            status: 'error',
            error: { code: e.code, message: e.message, retryable: e.retryable, phase: createdId ? 'stream' : 'request' },
          }))
        }
      } finally {
        abortRef.current = null
        if (createdId && createdId !== conversationId) {
          currentIdRef.current = createdId
          setConversationId(createdId)
          onConversationCreated?.(createdId)
        }
        void qc.invalidateQueries({ queryKey: ['conversations'] })
      }
    },
    [conversationId, onConversationCreated, qc],
  )

  const send = useCallback((text: string, opts: SendOptions) => run(text, opts, false), [run])

  const regenerate = useCallback(
    (opts: SendOptions) => {
      const lastUser = [...messages].reverse().find((m) => m.role === 'user')
      if (lastUser) void run(lastUser.content, opts, true)
    },
    [messages, run],
  )

  /**
   * Retry after an error. If the server already stored the user turn, regenerate (so the turn is
   * not duplicated); otherwise drop the local bubbles and send again.
   */
  const retry = useCallback(
    (opts: SendOptions) => {
      const lastUser = [...messages].reverse().find((m) => m.role === 'user')
      const failed = messages.at(-1)
      if (!lastUser) return
      if (failed?.error?.phase === 'stream') {
        void run(lastUser.content, opts, true)
        return
      }
      setMessages((prev) => prev.slice(0, prev.lastIndexOf(lastUser)))
      void run(lastUser.content, opts, false)
    },
    [messages, run],
  )

  const stop = useCallback(() => abortRef.current?.abort(), [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    currentIdRef.current = null
    setConversationId(null)
    setMessages([])
    setLoadError(null)
  }, [])

  return { conversationId, messages, loading, loadError, isGenerating, send, regenerate, retry, stop, reset, load }
}
