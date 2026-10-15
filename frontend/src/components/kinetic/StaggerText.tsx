/**
 * Word-by-word (or letter-by-letter) masked rise.
 * Adapted from Vengeance UI "Stagger Text" (MIT, © 2025-2026 Ashutoshx7,
 * https://github.com/Ashutoshx7/VengeanceUI) — see THIRD_PARTY_NOTICES.md.
 * Changes: `motion/react` instead of `framer-motion`, animates on mount (`animateOnMount`) or in view,
 * renders plain text under reduced motion, and keeps the full text available to screen readers.
 */
import { motion } from 'motion/react'
import { usePreferences } from '@/hooks/usePreferences'
import { cn } from '@/lib/utils'

const EASE = [0.22, 1, 0.36, 1] as const

export function StaggerText({
  children,
  delay = 0,
  divideBy = 'word',
  animateOnMount = false,
  className,
}: {
  children: string
  delay?: number
  divideBy?: 'word' | 'letter'
  animateOnMount?: boolean
  className?: string
}) {
  const { reducedMotion } = usePreferences()
  if (reducedMotion) return <span className={className}>{children}</span>

  const parts = divideBy === 'letter' ? children.split('') : children.split(' ')
  const stagger = divideBy === 'letter' ? 0.02 : 0.06
  const container = { hidden: {}, show: { transition: { staggerChildren: stagger, delayChildren: delay } } }
  const item = { hidden: { y: '110%' }, show: { y: '0%', transition: { duration: 0.7, ease: EASE } } }
  const trigger = animateOnMount ? { animate: 'show' } : { whileInView: 'show', viewport: { once: true } }

  return (
    <motion.span
      aria-label={children}
      role="text"
      variants={container}
      initial="hidden"
      {...trigger}
      className={cn('inline-block', className)}
    >
      {parts.map((part, i) => (
        <span key={i} aria-hidden className="relative inline-block overflow-hidden pb-[0.08em] align-top">
          <motion.span variants={item} className="inline-block will-change-transform">
            {divideBy === 'letter' ? (part === ' ' ? ' ' : part) : i < parts.length - 1 ? `${part} ` : part}
          </motion.span>
        </span>
      ))}
    </motion.span>
  )
}
