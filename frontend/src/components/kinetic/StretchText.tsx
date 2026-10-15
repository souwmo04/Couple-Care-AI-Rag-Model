/**
 * Variable-font kinetic type: each letter breathes between narrow/light and wide/black on the Archivo
 * width and weight axes, in a travelling wave; hovering a letter snaps it wide. Static under reduced motion.
 *
 * Layout never changes while it animates: every letter sits in a slot sized by an invisible copy of itself
 * at its widest/heaviest, and the animated glyph is centred inside that slot. Words never break internally,
 * so a line can only wrap between words — and it wraps the same way on every frame.
 */
import { Fragment, useMemo, type CSSProperties } from 'react'
import { usePreferences } from '@/hooks/usePreferences'
import { cn } from '@/lib/utils'

const BENGALI_RE = /[ঀ-৿]/

export function StretchText({ children, className }: { children: string; className?: string }) {
  const { reducedMotion } = usePreferences()
  // Each word with the global index of its first letter (drives the wave delay).
  const words = useMemo(
    () =>
      children.split(' ').reduce<{ word: string; start: number }[]>((acc, word) => {
        const prev = acc.at(-1)
        return [...acc, { word, start: prev ? prev.start + Array.from(prev.word).length : 0 }]
      }, []),
    [children],
  )
  if (reducedMotion) return <span className={cn('font-wide', className)}>{children}</span>
  return (
    <span role="text" aria-label={children} className={cn('stretch-text', className)}>
      {words.map(({ word, start }, w) => (
        <Fragment key={w}>
          {w > 0 && ' '}
          <span aria-hidden className="inline-block whitespace-nowrap">
            {/* Bangla is never split: vowel signs and conjuncts must stay attached, so the word breathes as one. */}
            {(BENGALI_RE.test(word) ? [word] : Array.from(word)).map((char, c) => (
              <span key={c} className="relative inline-block">
                <span className="stretch-ghost invisible">{char}</span>
                <span
                  className="stretch-letter absolute inset-0 flex justify-center"
                  style={{ '--i': start + c } as CSSProperties}
                >
                  {char}
                </span>
              </span>
            ))}
          </span>
        </Fragment>
      ))}
    </span>
  )
}
