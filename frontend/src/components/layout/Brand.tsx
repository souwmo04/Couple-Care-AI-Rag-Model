import { Link } from 'react-router'
import { cn } from '@/lib/utils'

/** Two overlapping rings; the shared space between them is the coral lens — "understanding each other". */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={cn('size-7', className)}>
      <defs>
        <clipPath id="cc-left">
          <circle cx="12.5" cy="16" r="8.5" />
        </clipPath>
      </defs>
      <circle cx="12.5" cy="16" r="8.5" fill="none" stroke="currentColor" strokeWidth="2.6" />
      <circle cx="19.5" cy="16" r="8.5" fill="none" stroke="currentColor" strokeWidth="2.6" />
      <circle cx="19.5" cy="16" r="8.5" fill="var(--accent)" clipPath="url(#cc-left)" opacity="1" />
    </svg>
  )
}

export function Wordmark({ className, to = '/' }: { className?: string; to?: string }) {
  return (
    <Link
      to={to}
      className={cn('inline-flex items-center gap-2.5 rounded-md text-foreground', className)}
      aria-label="CoupleCare AI — home"
    >
      <LogoMark />
      <span className="font-wide text-[1.05rem] font-black uppercase tracking-tight">
        CoupleCare{' '}
        <span className="rounded-sm border-2 border-ink bg-accent px-1 text-ink dark:border-foreground">AI</span>
      </span>
    </Link>
  )
}
