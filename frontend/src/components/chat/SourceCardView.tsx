import { ChevronDown, ExternalLink } from 'lucide-react'
import { forwardRef, useState } from 'react'
import { useCopy } from '@/i18n'
import { languageLabel } from '@/lib/languages'
import { topicTitle } from '@/lib/topics'
import { cn } from '@/lib/utils'
import type { SourceCard } from '@/types/api'

function safeUrl(url: string | null): string | null {
  if (!url) return null
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' ? parsed.toString() : null
  } catch {
    return null
  }
}

/**
 * A citation card. Only rendered for passages the backend actually retrieved.
 * Shows what a reader needs (which guide, a short excerpt); licence, relevance score and document
 * id stay available under "Technical details" instead of cluttering every card.
 */
export const SourceCardView = forwardRef<
  HTMLDivElement,
  { source: SourceCard; active?: boolean; compact?: boolean; citationIds?: string[] }
>(({ source, active, compact, citationIds }, ref) => {
    const t = useCopy()
    const [expanded, setExpanded] = useState(false)
    const topic = topicTitle(t, source.topic)
    const url = safeUrl(source.url)
    return (
      <div
        ref={ref}
        id={`source-${source.chunk_id}`}
        tabIndex={-1}
        className={cn(
          'rounded-md border bg-surface-solid p-4 outline-none transition-[box-shadow,transform] duration-200',
          active ? 'bg-highlight text-ink shadow-lift' : 'shadow-soft',
        )}
      >
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex shrink-0 flex-col gap-1">
            {(citationIds ?? [source.citation_id]).map((id) => (
              <span key={id} className="flex h-7 min-w-7 items-center justify-center rounded-sm border-2 border-ink bg-mint px-1 font-mono text-[0.68rem] font-bold text-ink">
                {id}
              </span>
            ))}
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-bold leading-snug">{source.title}</p>
            <p className={cn('mt-0.5 text-xs', active ? 'text-ink/70' : 'text-muted-foreground')}>
              {t.chat.sourceTopic.replace('{topic}', topic)}
            </p>
          </div>
        </div>
        {!compact && (
          <>
            <p
              lang={source.language === 'bn' ? 'bn' : undefined}
              className={cn('mt-3 text-sm leading-relaxed', !expanded && 'line-clamp-3')}
            >
              {source.excerpt}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1">
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                aria-expanded={expanded}
                className="text-xs font-bold underline decoration-2 underline-offset-2"
              >
                {expanded ? t.chat.readLess : t.chat.readMore}
              </button>
              {url && (
                <a href={url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-xs font-bold underline decoration-2 underline-offset-2">
                  <ExternalLink className="size-3.5" />
                  {t.chat.viewSource}
                </a>
              )}
            </div>
            <details className="group mt-3 text-xs">
              <summary className={cn('flex cursor-pointer list-none items-center gap-1 font-mono uppercase tracking-wide', active ? 'text-ink/70' : 'text-muted-foreground')}>
                <ChevronDown className="size-3.5 transition-transform group-open:rotate-180" aria-hidden />
                {t.chat.technicalDetails}
              </summary>
              <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                <dt>{t.chat.language}</dt>
                <dd>{languageLabel(source.language)}</dd>
                <dt>{t.chat.relevance}</dt>
                <dd>{Math.round(source.score * 100)}%</dd>
                {source.license && (
                  <>
                    <dt>{t.chat.license}</dt>
                    <dd className="break-words">{source.license}</dd>
                  </>
                )}
                <dt>{t.chat.documentId}</dt>
                <dd className="break-all font-mono">{source.document_id}</dd>
              </dl>
            </details>
          </>
        )}
      </div>
    )
  },
)
SourceCardView.displayName = 'SourceCardView'
