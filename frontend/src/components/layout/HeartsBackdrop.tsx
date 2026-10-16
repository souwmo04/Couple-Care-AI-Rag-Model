/**
 * Decorative pink/red hearts behind page content. Positions are fixed (seeded), the layer ignores pointer
 * events and is hidden from assistive technology, and hearts stop floating under reduced motion. On phones only the
 * hearts near the left and right edges are shown, so none drift over the text.
 */
import type { CSSProperties } from 'react'
import { usePreferences } from '@/hooks/usePreferences'
import { cn } from '@/lib/utils'

const HEART = 'M12 21s-6.7-4.35-9.33-8.04C.57 9.94 1.9 5.5 5.9 4.6c2.2-.5 4.3.5 6.1 2.6 1.8-2.1 3.9-3.1 6.1-2.6 4 .9 5.33 5.34 3.23 8.36C18.7 16.65 12 21 12 21z'
type Style = 'pink' | 'red' | 'outline'

function seeded(seed: number) {
  let x = seed
  return () => {
    x = (x * 16807) % 2147483647
    return (x - 1) / 2147483646
  }
}

function makeHearts(count: number, seed: number) {
  const rand = seeded(seed)
  const styles: Style[] = ['pink', 'red', 'outline', 'pink', 'outline']
  return Array.from({ length: count }, (_, i) => ({
    left: rand() * 96,
    top: rand() * 96,
    size: 18 + rand() * 46,
    rotate: -25 + rand() * 50,
    duration: 7 + rand() * 7,
    delay: -rand() * 10,
    style: styles[i % styles.length],
  }))
}

export function HeartsBackdrop({ count = 18, seed = 7, className }: { count?: number; seed?: number; className?: string }) {
  const { reducedMotion } = usePreferences()
  const hearts = makeHearts(count, seed)
  return (
    <div aria-hidden className={cn('pointer-events-none absolute inset-0 -z-10 overflow-hidden', className)}>
      {hearts.map((h, i) => (
        <svg
          key={i}
          viewBox="0 0 24 24"
          className={cn(
            'heart absolute',
            !reducedMotion && 'heart-float',
            `heart-${h.style}`,
            h.left > 6 && h.left < 84 && 'max-sm:hidden',
          )}
          style={
            {
              left: `${h.left}%`,
              top: `${h.top}%`,
              width: h.size,
              height: h.size,
              '--heart-rotate': `${h.rotate}deg`,
              animationDuration: `${h.duration}s`,
              animationDelay: `${h.delay}s`,
            } as CSSProperties
          }
        >
          <path d={HEART} />
        </svg>
      ))}
    </div>
  )
}
