import { useCloudMode } from '@/hooks/useProvider'
import { KineticLoader } from '@/components/kinetic/KineticLoader'
import { BookOpenText, Check, ChevronDown, Copy, PlugZap, RefreshCw, ThumbsDown, ThumbsUp, TriangleAlert } from 'lucide-react'
import { useEntrance } from '@/hooks/useEntrance'
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
import { CITE_RE, linkCitations } from '@/lib/citations'
import { cn } from '@/lib/utils'
import { api } from '@/services/api'

function Thinking({ word, label }: { word: string; label: string }) {
  return (
    <span className="flex flex-col items-start gap-1 py-1">
      <KineticLoader text={word} className="text-2xl text-foreground" />
      <span className="text-xs text-muted-foreground">{label}</span>
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
              className="mx-0.5 inline-flex translate-y-[-1px] items-center rounded-sm border-2 border-ink bg-mint px-1 align-baseline font-mono text-[0.65rem] font-bold text-ink transition-colors hover:bg-highlight"
              aria-label={`${t.chat.sources} ${id}`}
            >
              {children}
            </button>
          )
        }
        return (
          <a href={href} target="_blank" rel="noreferrer noopener" className="font-semibold underline decoration-2 underline-offset-2">
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

  const cloud = useCloudMode()
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
      <span className="mt-1 flex size-9 shrink-0 items-center justify-center rounded-sm border-2 border-ink bg-highlight text-ink shadow-soft">
        <LogoMark className="size-5" />
      </span>
      <div
        className={cn(
          'min-w-0 flex-1 rounded-md border-2 border-ink bg-surface-solid px-4 py-3.5 shadow-soft transition-shadow dark:border-foreground sm:px-5',
          selected && message.sources.length > 0 && 'lg:shadow-lift',
        )}
      >
        {(message.generated === false ||
          message.fallbackReason ||
          (message.status === 'done' && message.grounded === false && message.generated)) && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {message.generated === false && <Badge tone="lavender">{t.chat.notGenerated}</Badge>}
            {message.fallbackReason && (
              <Badge tone="warning">
                {message.fallbackReason === 'rate_limited' ? t.chat.fallbackRateLimited : t.chat.fallbackUnavailable}
              </Badge>
            )}
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
              <span aria-hidden className="ml-0.5 inline-block h-4 w-2 translate-y-0.5 bg-accent [animation:caret-blink_1s_steps(1)_infinite]" />
            )}
          </div>
        ) : message.status === 'streaming' ? (
          <Thinking word={t.chat.thinkingShort} label={t.chat.thinking} />
        ) : null}

        {message.status === 'stopped' && <p className="mt-2 text-xs italic text-muted-foreground">{t.chat.stopped}</p>}

        {isError && message.error && (
          <div
            role="alert"
            className="mt-1 rounded-md border-2 border-ink bg-highlight p-4 text-ink"
          >
            <p className="flex items-center gap-2 text-sm font-medium text-ink">
              {offline ? <PlugZap className="size-4 text-ink" /> : <TriangleAlert className="size-4 text-ink" />}
              {offline ? t.chat.offlineTitle : t.chat.errorTitle}
            </p>
            <p className="mt-1.5 text-sm text-ink/80">{offline ? t.chat.offlineBody : message.error.message}</p>
            {offline && <p className="mt-1 text-xs text-ink/80">{cloud ? t.status.offlineHelpCloud : t.status.offlineHelp}</p>}
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
                className="press inline-flex items-center gap-2 rounded-sm border-2 border-ink bg-lavender-soft px-3 py-1.5 text-xs font-bold text-ink dark:border-foreground dark:text-foreground"
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
      <p className="kicker mb-2 text-muted-foreground">{title}</p>
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
        className={cn('text-muted-foreground hover:text-ink', pressed && 'border-ink bg-highlight text-ink')}
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
      <p className="max-w-[min(85%,36rem)] whitespace-pre-wrap rounded-md border-2 border-ink bg-highlight px-4 py-3 text-[0.95rem] font-medium leading-relaxed text-ink shadow-soft">
        {message.content}
      </p>
    </motion.article>
  )
}
