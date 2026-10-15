/**
 * Letters that flip over on a loop (CSS 3D).
 * Adapted from Vengeance UI "Flip Text" (MIT, © 2025-2026 Ashutoshx7,
 * https://github.com/Ashutoshx7/VengeanceUI) — see THIRD_PARTY_NOTICES.md.
 * Changes: renders plain text under reduced motion, exposes the text once to screen readers,
 * keyframes renamed (`vui-flip`, `vui-fade`) and moved to styles/index.css.
 */
import { useMemo, type CSSProperties } from 'react'
import { usePreferences } from '@/hooks/usePreferences'
import { cn } from '@/lib/utils'

export function FlipText({
  children,
  className,
  duration = 2.2,
  delay = 0,
  loop = true,
}: {
  children: string
  className?: string
  duration?: number
  delay?: number
  loop?: boolean
}) {
  const { reducedMotion } = usePreferences()
  // Each word with the index of its first character in the whole string (for the sine-eased stagger).
  const words = useMemo(
    () =>
      children.split(' ').reduce<{ word: string; start: number }[]>((acc, word) => {
        const prev = acc.at(-1)
        return [...acc, { word, start: prev ? prev.start + prev.word.length + 1 : 0 }]
      }, []),
    [children],
  )
  if (reducedMotion) return <span className={className}>{children}</span>

  const total = children.length
  return (
    <span role="text" aria-label={children} className={cn('flip-text inline-block leading-none', className)}>
      {words.map(({ word, start }, w) => (
        <span key={w} aria-hidden className="inline-block whitespace-nowrap [transform-style:preserve-3d]">
          {word.split('').map((char, c) => (
            <span
              key={c}
              data-char={char}
              className="flip-char relative inline-block [transform-style:preserve-3d]"
              style={
                {
                  '--flip-duration': `${duration}s`,
                  '--flip-delay': `${Math.sin(((start + c) / total) * (Math.PI / 2)) * (duration * 0.25) + delay}s`,
                  '--flip-iteration': loop ? 'infinite' : '1',
                } as CSSProperties
              }
            >
              {char}
            </span>
          ))}
          {w < words.length - 1 && <span className="inline-block">&nbsp;</span>}
        </span>
      ))}
    </span>
  )
}
