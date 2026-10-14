import { motion, type HTMLMotionProps } from 'motion/react'
import { usePreferences } from '@/hooks/usePreferences'

/**
 * Fades content up once when it scrolls into view. With reduced motion the content renders
 * immediately in its final state — it never depends on an animation to become visible.
 */
export function Reveal({ delay = 0, y = 16, ...props }: HTMLMotionProps<'div'> & { delay?: number; y?: number }) {
  const { reducedMotion } = usePreferences()
  return (
    <motion.div
      initial={reducedMotion ? false : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
      {...props}
    />
  )
}

/** Entrance props for one-off hero animations; disabled entirely under reduced motion. */
export function useEntrance() {
  const { reducedMotion } = usePreferences()
  return (from: Record<string, number>) => (reducedMotion ? false : from)
}
