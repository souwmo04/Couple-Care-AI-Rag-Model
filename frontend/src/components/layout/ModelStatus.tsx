import { useModelState } from '@/hooks/useModelState'
import { useCopy } from '@/i18n'
import { cn } from '@/lib/utils'


/** A small status pill. Reflects the *measured* state of the local model server, never an assumption. */
export function ModelStatusPill({ className, showLabel = true }: { className?: string; showLabel?: boolean }) {
  const t = useCopy()
  const state = useModelState()
  const label = {
    online: t.status.modelOnline,
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
        'inline-flex items-center gap-2 rounded-full border border-border bg-surface px-2.5 py-1 text-xs font-medium text-muted-foreground',
        className,
      )}
      title={label}
    >
      <span className="relative flex size-2">
        {state === 'online' && (
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-40 [animation-iteration-count:3]" />
        )}
        <span className={cn('relative inline-flex size-2 rounded-full', dot)} />
      </span>
      {showLabel ? label : <span className="sr-only">{label}</span>}
    </span>
  )
}
