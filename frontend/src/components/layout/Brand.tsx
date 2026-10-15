import { Link } from 'react-router'
import { cn } from '@/lib/utils'

/** Two people holding hands with a heart above them. Figures use the text colour; heart and joined hands use the accent. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={cn('size-7', className)}>
      <path
        d="M16 9.6s-3.5-2.2-3.5-4.6c0-1.25 1-2.15 2.05-2.15.7 0 1.15.3 1.45.85.3-.55.75-.85 1.45-.85 1.05 0 2.05.9 2.05 2.15 0 2.4-3.5 4.6-3.5 4.6z"
        fill="var(--accent)"
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinejoin="round"
      />
      <circle cx="7.5" cy="10.8" r="3.1" fill="currentColor" />
      <circle cx="24.5" cy="10.8" r="3.1" fill="currentColor" />
      <path d="M3.9 29v-8.3a3.6 3.6 0 0 1 7.2 0V29z" fill="currentColor" />
      <path d="M20.9 29v-8.3a3.6 3.6 0 0 1 7.2 0V29z" fill="currentColor" />
      <path
        d="M10.4 17.6 L15.2 23.4 M21.6 17.6 L16.8 23.4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <circle cx="16" cy="23.6" r="2" fill="var(--accent)" stroke="currentColor" strokeWidth="1.1" />
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
      <LogoMark className="size-8" />
      <span className="font-wide text-[1.05rem] font-black uppercase tracking-tight">
        CoupleCare{' '}
        <span className="rounded-sm border-2 border-ink bg-accent px-1 text-ink dark:border-foreground">AI</span>
      </span>
    </Link>
  )
}
