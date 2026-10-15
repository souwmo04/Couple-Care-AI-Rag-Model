import { useModelState } from '@/hooks/useModelState'
import { useCloudMode } from '@/hooks/useProvider'
import { useCopy } from '@/i18n'
import { cn } from '@/lib/utils'


/** A small status pill. Reflects the *measured* state of the local model server, never an assumption. */
export function ModelStatusPill({ className, showLabel = true }: { className?: string; showLabel?: boolean }) {
  const t = useCopy()
  const state = useModelState()
  const cloud = useCloudMode()
  const label = {
    online: cloud ? t.status.cloudOnline : t.status.modelOnline,
    offline: t.status.modelOffline,
    'backend-down': t.status.backendDown,
    checking: t.status.modelChecking,
  }[state]
  const dot = {
    online: 'bg-success',
    offline: 'bg-warning',
    'backend-down': 'bg-danger',
    checking: 'bg-muted-foreground',
  }[state]
  return (
    <span
      role="status"
      aria-live="polite"
      className={cn(
        'inline-flex items-center gap-2 rounded-sm border-2 border-ink px-2.5 py-0.5 text-xs font-bold dark:border-foreground',
        cloud && state === 'online' ? 'bg-accent text-ink dark:border-ink' : 'bg-surface-solid text-foreground',
        className,
      )}
      title={label}
    >
      <span className="relative flex size-2">
        {state === 'online' && (
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-40 [animation-iteration-count:3]" />
        )}
        <span className={cn('relative inline-flex size-2 rounded-full ring-1 ring-ink', dot)} />
      </span>
      {showLabel ? label : <span className="sr-only">{label}</span>}
    </span>
  )
}
