import { ExternalLink, LifeBuoy, Phone, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router'
import { useCopy } from '@/i18n'
import { cn } from '@/lib/utils'
import type { SafetyStatus, SupportResource } from '@/types/api'

export function SupportResourceList({ resources }: { resources: SupportResource[] }) {
  const t = useCopy()
  return (
    <ul className="space-y-2.5">
      {resources.map((r) => (
        <li key={r.name} className="rounded-sm border-2 border-ink bg-surface-solid p-3 text-foreground">
          <p className="text-sm font-medium text-foreground">{r.name}</p>
          <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{r.description}</p>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
            {r.contact && (
              <a href={`tel:${r.contact.replace(/[^\d+]/g, '')}`} className="inline-flex items-center gap-1.5 font-semibold text-foreground">
                <Phone className="size-3.5 text-accent" />
                {r.contact}
              </a>
            )}
            {r.url && (
              <a href={r.url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 font-semibold underline decoration-2 underline-offset-2">
                <ExternalLink className="size-3" />
                {new URL(r.url).hostname}
              </a>
            )}
            <span className="text-muted-foreground">
              {r.region} · {t.chat.verifiedOn}{' '}
              <a href={r.source_url} target="_blank" rel="noreferrer noopener" className="underline decoration-dotted">
                {r.verified_on}
              </a>
            </span>
          </div>
        </li>
      ))}
    </ul>
  )
}

/** Shown under an assistant message when the safety layer raised the level. */
export function SafetyNotice({ safety }: { safety: SafetyStatus }) {
  const t = useCopy()
  if (safety.level === 'none' || safety.level === 'declined' || !safety.message) return null
  const urgent = safety.level === 'urgent'
  return (
    <div
      role={urgent ? 'alert' : 'note'}
      className={cn(
        'mt-4 rounded-md border-2 border-ink p-4 text-ink shadow-soft',
        urgent ? 'bg-accent' : 'bg-highlight',
      )}
    >
      <p className="flex items-start gap-2.5 text-sm font-bold text-ink">
        {urgent ? <ShieldAlert className="mt-0.5 size-4 shrink-0 text-ink" /> : <LifeBuoy className="mt-0.5 size-4 shrink-0 text-ink" />}
        {safety.message}
      </p>
      {safety.resources.length > 0 ? (
        <div className="mt-3">
          <SupportResourceList resources={safety.resources} />
        </div>
      ) : (
        <p className="mt-2 text-xs text-ink/80">
          <Link to="/settings#support-region" className="font-bold underline decoration-2">
            {t.chat.regionHint}
          </Link>
        </p>
      )}
    </div>
  )
}
