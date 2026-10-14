import { BookOpenText, ExternalLink } from 'lucide-react'
import { forwardRef } from 'react'
import { Badge } from '@/components/ui/primitives'
import { useCopy } from '@/i18n'
import { cn } from '@/lib/utils'
import type { SourceCard } from '@/types/api'

const LANGUAGE_LABELS: Record<string, string> = { en: 'English', bn: 'বাংলা', banglish: 'Banglish', mixed: 'Mixed' }

export function languageLabel(code: string): string {
  return LANGUAGE_LABELS[code] ?? code
}

function safeUrl(url: string | null): string | null {
  if (!url) return null
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' ? parsed.toString() : null
  } catch {
    return null
  }
}

/** A citation card. Only rendered for passages the backend actually retrieved. */
export const SourceCardView = forwardRef<HTMLDivElement, { source: SourceCard; active?: boolean; compact?: boolean }>(
  ({ source, active, compact }, ref) => {
    const t = useCopy()
    const topic = t.topics.items[source.topic as keyof typeof t.topics.items]?.title ?? source.topic
    const url = safeUrl(source.url)
    return (
      <div
        ref={ref}
        id={`source-${source.chunk_id}`}
        tabIndex={-1}
        className={cn(
          'rounded-xl border bg-surface-solid p-4 transition-[border-color,box-shadow] duration-300 outline-none',
          active ? 'border-lavender shadow-[0_0_0_3px_var(--lavender-soft)]' : 'border-border',
        )}
      >
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg bg-lavender-soft text-[0.7rem] font-semibold text-lavender">
            {source.citation_id}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium leading-snug text-foreground">{source.title}</p>
            {source.organization && <p className="mt-0.5 text-xs text-muted-foreground">{source.organization}</p>}
          </div>
        </div>
        {!compact && (
          <blockquote
            lang={source.language === 'bn' ? 'bn' : undefined}
            className="mt-3 border-l-2 border-border-strong pl-3 text-sm leading-relaxed text-muted-foreground"
          >
            {source.excerpt}
          </blockquote>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {source.synthetic && <Badge tone="coral">{t.common.syntheticBadge}</Badge>}
          <Badge>{languageLabel(source.language)}</Badge>
          <Badge>{topic}</Badge>
          {source.section && !compact && <Badge tone="outline">{source.section}</Badge>}
        </div>
        {!compact && (
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {source.license && (
              <>
                <dt>{t.chat.license}</dt>
                <dd className="truncate text-foreground">{source.license}</dd>
              </>
            )}
            <dt>{t.chat.relevance}</dt>
            <dd className="text-foreground">{Math.round(source.score * 100)}%</dd>
          </dl>
        )}
        {url && !compact && (
          <a
            href={url}
            target="_blank"
            rel="noreferrer noopener"
            className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-lavender hover:underline"
          >
            <ExternalLink className="size-3.5" />
            {t.chat.viewSource}
          </a>
        )}
        {!url && !compact && (
          <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <BookOpenText className="size-3.5" />
            {source.document_id}
          </p>
        )}
      </div>
    )
  },
)
SourceCardView.displayName = 'SourceCardView'
