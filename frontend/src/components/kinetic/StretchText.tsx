/**
 * Variable-font kinetic type: each letter breathes between narrow/light and wide/black on the Archivo
 * width and weight axes, in a travelling wave; hovering a letter snaps it wide. Static under reduced motion.
 */
import type { CSSProperties } from 'react'
import { usePreferences } from '@/hooks/usePreferences'
import { cn } from '@/lib/utils'

export function StretchText({ children, className }: { children: string; className?: string }) {
  const { reducedMotion } = usePreferences()
  if (reducedMotion) return <span className={cn('font-wide', className)}>{children}</span>
  return (
    <span role="text" aria-label={children} className={cn('stretch-text inline-block', className)}>
      {Array.from(children).map((char, i) => (
        <span key={i} aria-hidden className="stretch-letter inline-block" style={{ '--i': i } as CSSProperties}>
          {char === ' ' ? ' ' : char}
        </span>
      ))}
    </span>
  )
}
