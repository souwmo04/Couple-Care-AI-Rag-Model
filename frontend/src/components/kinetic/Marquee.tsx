/**
 * Endless horizontal band of words (kinetic typography). Decorative: hidden from screen readers,
 * paused on hover, and static under reduced motion.
 */
import { Fragment } from 'react'
import { usePreferences } from '@/hooks/usePreferences'
import { cn } from '@/lib/utils'

export function Marquee({
  items,
  className,
  reverse = false,
  speed = 40,
}: {
  items: string[]
  className?: string
  reverse?: boolean
  /** Seconds for one full loop. */
  speed?: number
}) {
  const { reducedMotion } = usePreferences()
  const row = (
    <div className="flex shrink-0 items-center gap-6 pr-6">
      {items.map((item, i) => (
        <Fragment key={i}>
          <span className="whitespace-nowrap">{item}</span>
          <span className="text-[0.6em]">✦</span>
        </Fragment>
      ))}
    </div>
  )
  return (
    <div aria-hidden className={cn('group flex overflow-hidden', className)}>
      <div
        className={cn('flex shrink-0', !reducedMotion && 'marquee-track group-hover:[animation-play-state:paused]')}
        style={{ animationDuration: `${speed}s`, animationDirection: reverse ? 'reverse' : 'normal' }}
      >
        {row}
        {row}
      </div>
    </div>
  )
}
