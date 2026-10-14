import { BookOpenText, Check, ChevronDown, Copy, PlugZap, RefreshCw, ThumbsDown, ThumbsUp, TriangleAlert } from 'lucide-react'
import { useEntrance } from '@/components/landing/Reveal'
import { AnimatePresence, motion } from 'motion/react'
import { memo, useMemo, useState, type ReactNode } from 'react'
import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { toast } from 'sonner'
import { LogoMark } from '@/components/layout/Brand'
import { SafetyNotice } from '@/components/chat/SafetyNotice'
import { SourceCardView } from '@/components/chat/SourceCardView'
import { Button } from '@/components/ui/button'
import { Badge, Tooltip } from '@/components/ui/primitives'
import type { UiMessage } from '@/hooks/useChat'
import { useCopy } from '@/i18n'
import { cn } from '@/lib/utils'
import { api } from '@/services/api'

const CITE_RE = /\[(S\d{1,2})\]/g

/** Turn validated "[S1]" markers into links the markdown renderer can show as chips. */
export function linkCitations(text: string, available: Set<string>): string {
  return text.replace(CITE_RE, (match, id: string) => (available.has(id) ? `[${id}](#cite-${id})` : match))
}

function TypingDots({ label }: { label: string }) {
  return (
    <span role="status" aria-label={label} className="inline-flex items-center gap-1.5 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="size-1.5 rounded-full bg-lavender"
          style={{ animation: `dot-pulse 1.2s ${i * 0.15}s infinite ease-in-out` }}
        />
      ))}
      <span className="ml-2 text-xs text-muted-foreground">{label}</span>
    </span>
  )
}

interface AssistantProps {
  message: UiMessage
  conversationId: string | null
  isLast: boolean
  canRegenerate: boolean
  selected: boolean
  onSelect: () => void
  onCite: (citationId: string) => void
  onRegenerate: () => void
  onRetry: () => void
}

export const AssistantMessage = memo(function AssistantMessage({
  message,
  conversationId,
  isLast,
  canRegenerate,
  selected,
  onSelect,
  onCite,
  onRegenerate,
  onRetry,
}: AssistantProps) {
  const t = useCopy()
  const enter = useEntrance()
  const [copied, setCopied] = useState(false)
  const [rating, setRating] = useState<'helpful' | 'not_helpful' | null>(null)
  const [showEvidence, setShowEvidence] = useState(false)
  const available = useMemo(() => new Set(message.sources.map((s) => s.citation_id)), [message.sources])
  const cited = message.sources.filter((s) => s.cited)
  const related = message.sources.filter((s) => !s.cited)

  const components = useMemo<Components>(
    () => ({
      a: ({ href, children }) => {
        if (href?.startsWith('#cite-')) {
          const id = href.slice(6)
          return (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onCite(id)
              }}
              className="mx-0.5 inline-flex translate-y-[-1px] items-center rounded-md bg-lavender-soft px-1.5 align-baseline text-[0.7rem] font-semibold text-lavender transition-colors hover:bg-lavender hover:text-background"
              aria-label={`${t.chat.sources} ${id}`}
            >
              {children}
            </button>
          )
        }
        return (
          <a href={href} target="_blank" rel="noreferrer noopener" className="text-lavender underline">
            {children}
          </a>
        )
      },
    }),
    [onCite, t.chat.sources],
  )

  async function copy() {
    try {
      await navigator.clipboard.writeText(message.content.replace(CITE_RE, ''))
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      toast.error(t.common.copy)
    }
  }

  async function rate(value: 'helpful' | 'not_helpful') {
    if (!conversationId || !message.messageId || rating) return
    setRating(value)
    try {
      await api.feedback(conversationId, message.messageId, value)
      toast.success(t.chat.feedbackThanks)
    } catch {
      setRating(null)
    }
  }

  const isError = message.status === 'error'
  const offline = message.error?.code === 'model_offline' || message.error?.code === 'backend_unreachable'

  return (
    <motion.article
      initial={enter({ opacity: 0, y: 8 })}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="group flex gap-3 sm:gap-4"
      aria-label={t.chat.assistant}
      onClick={onSelect}
    >
      <span className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-full border border-border bg-surface-solid">
        <LogoMark className="size-5" />
      </span>
      <div className={cn('min-w-0 flex-1 rounded-2xl px-1 py-0.5 transition-colors', selected && message.sources.length > 0 && 'lg:bg-transparent')}>
        {(message.generated === false || (message.status === 'done' && message.grounded === false && message.generated)) && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {message.generated === false && <Badge tone="lavender">{t.chat.notGenerated}</Badge>}
            {message.generated && message.grounded === false && <Badge tone="outline">{t.chat.ungrounded}</Badge>}
          </div>
        )}

        {message.content ? (
          <div
            lang={message.responseLanguage === 'bn' ? 'bn' : undefined}
            className="prose-chat text-[0.95rem] leading-relaxed text-foreground"
          >
            <Markdown remarkPlugins={[remarkGfm]} components={components}>
              {linkCitations(message.content, available)}
            </Markdown>
            {message.status === 'streaming' && (
              <span aria-hidden className="ml-0.5 inline-block h-4 w-0.5 translate-y-0.5 bg-lavender [animation:caret-blink_1s_steps(1)_infinite]" />
            )}
          </div>
        ) : message.status === 'streaming' ? (
          <TypingDots label={t.chat.thinking} />
        ) : null}

        {message.status === 'stopped' && <p className="mt-2 text-xs italic text-muted-foreground">{t.chat.stopped}</p>}

        {isError && message.error && (
          <div
            role="alert"
            className="mt-1 rounded-xl border border-[color-mix(in_oklch,var(--warning)_45%,transparent)] bg-[color-mix(in_oklch,var(--warning)_10%,transparent)] p-4"
          >
            <p className="flex items-center gap-2 text-sm font-medium text-foreground">
              {offline ? <PlugZap className="size-4 text-warning" /> : <TriangleAlert className="size-4 text-warning" />}
              {offline ? t.chat.offlineTitle : t.chat.errorTitle}
            </p>
            <p className="mt-1.5 text-sm text-muted-foreground">{offline ? t.chat.offlineBody : message.error.message}</p>
            {offline && <p className="mt-1 text-xs text-muted-foreground">{t.status.offlineHelp}</p>}
            {message.error.retryable && (
              <Button size="sm" variant="secondary" className="mt-3" onClick={onRetry}>
                <RefreshCw /> {t.common.retry}
              </Button>
            )}
          </div>
        )}

        {message.safety && message.status !== 'error' && <SafetyNotice safety={message.safety} />}

        {message.status === 'done' && message.generated && (
          <div className="mt-4">
            {message.sources.length > 0 ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  setShowEvidence((v) => !v)
                }}
                aria-expanded={showEvidence}
                className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-border-strong hover:text-foreground"
              >
                <BookOpenText className="size-3.5" />
                {showEvidence ? t.chat.hideEvidence : t.chat.showEvidence} · {message.sources.length}
                <ChevronDown className={cn('size-3.5 transition-transform', showEvidence && 'rotate-180')} />
              </button>
            ) : (
              <p className="text-xs text-muted-foreground">{t.chat.noSources}</p>
            )}
            <AnimatePresence initial={false}>
              {showEvidence && (
                <motion.div
                  initial={enter({ height: 0, opacity: 0 })}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  className="overflow-hidden"
                >
                  <EvidenceGroup title={t.chat.sourcesCited} items={cited} />
                  <EvidenceGroup title={t.chat.sourcesRelated} items={related} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {(message.status === 'done' || message.status === 'stopped') && message.content && (
          <div className="mt-3 flex items-center gap-0.5 opacity-100 transition-opacity sm:opacity-0 sm:group-focus-within:opacity-100 sm:group-hover:opacity-100">
            <ActionButton label={copied ? t.common.copied : t.chat.copyResponse} onClick={copy}>
              {copied ? <Check /> : <Copy />}
            </ActionButton>
            {isLast && canRegenerate && message.generated !== false && (
              <ActionButton label={t.chat.regenerate} onClick={onRegenerate}>
                <RefreshCw />
              </ActionButton>
            )}
            {message.generated && message.messageId && (
              <>
                <ActionButton label={t.chat.helpful} onClick={() => rate('helpful')} pressed={rating === 'helpful'}>
                  <ThumbsUp />
                </ActionButton>
                <ActionButton label={t.chat.notHelpful} onClick={() => rate('not_helpful')} pressed={rating === 'not_helpful'}>
                  <ThumbsDown />
                </ActionButton>
              </>
            )}
            {message.durationMs !== undefined && (
              <span className="ml-2 text-[0.7rem] tabular-nums text-muted-foreground">{(message.durationMs / 1000).toFixed(1)}s</span>
            )}
          </div>
        )}
      </div>
    </motion.article>
  )
})

function EvidenceGroup({ title, items }: { title: string; items: UiMessage['sources'] }) {
  if (!items.length) return null
  return (
    <div className="mt-3">
      <p className="mb-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">{title}</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {items.map((s) => (
          <SourceCardView key={s.chunk_id} source={s} />
        ))}
      </div>
    </div>
  )
}

function ActionButton({ label, onClick, children, pressed }: { label: string; onClick: () => void; children: ReactNode; pressed?: boolean }) {
  return (
    <Tooltip content={label}>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label={label}
        aria-pressed={pressed}
        onClick={(e) => {
          e.stopPropagation()
          onClick()
        }}
        className={cn('text-muted-foreground hover:text-foreground', pressed && 'text-lavender')}
      >
        {children}
      </Button>
    </Tooltip>
  )
}

export function UserMessage({ message }: { message: UiMessage }) {
  const t = useCopy()
  const enter = useEntrance()
  return (
    <motion.article
      initial={enter({ opacity: 0, y: 8 })}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex justify-end"
      aria-label={t.chat.you}
    >
      <p className="max-w-[min(85%,36rem)] whitespace-pre-wrap rounded-2xl rounded-br-md bg-primary px-4 py-3 text-[0.95rem] leading-relaxed text-primary-foreground">
        {message.content}
      </p>
    </motion.article>
  )
}
