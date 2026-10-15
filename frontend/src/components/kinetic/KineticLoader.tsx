/**
 * "Thinking…" indicator: letters stretch and squash in a travelling wave.
 * Adapted from Vengeance UI "Kinetic Text Loader" (MIT, © 2025-2026 Ashutoshx7,
 * https://github.com/Ashutoshx7/VengeanceUI) — see THIRD_PARTY_NOTICES.md.
 * Changes: works for any word (including Bangla), uses the app's own fonts (no Google Fonts request),
 * keyframes moved to styles/index.css, and announces itself politely to screen readers.
 */
import type { CSSProperties } from 'react'
import { cn } from '@/lib/utils'

export function KineticLoader({ text, className }: { text: string; className?: string }) {
  // Bangla is split into grapheme clusters so vowel signs stay attached to their consonants.
  const segmenter = typeof Intl !== 'undefined' && 'Segmenter' in Intl ? new Intl.Segmenter(undefined, { granularity: 'grapheme' }) : null
  const letters = segmenter ? Array.from(segmenter.segment(text), (s) => s.segment) : Array.from(text)
  return (
    <span role="status" aria-live="polite" className={cn('kinetic-loader inline-flex items-end font-wide font-black', className)}>
      <span className="sr-only">{text}</span>
      {letters.map((char, i) => (
        <span
          key={i}
          aria-hidden
          className="kinetic-letter inline-block origin-bottom"
          style={{ '--i': i } as CSSProperties}
        >
          {char === ' ' ? ' ' : char}
        </span>
      ))}
      <span aria-hidden className="kinetic-dot ml-1 inline-block size-[0.28em] rounded-full bg-accent" />
    </span>
  )
}
