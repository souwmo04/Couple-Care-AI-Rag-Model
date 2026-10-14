import { motion, type HTMLMotionProps } from 'motion/react'

/** Fades content up once when it scrolls into view. Motion is disabled globally for reduced-motion users. */
export function Reveal({ delay = 0, y = 16, ...props }: HTMLMotionProps<'div'> & { delay?: number; y?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
      {...props}
    />
  )
}
