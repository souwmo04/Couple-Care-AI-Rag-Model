import { ArrowRight, LockKeyhole } from 'lucide-react'
import { useEntrance } from '@/components/landing/Reveal'
import { motion } from 'motion/react'
import { Link } from 'react-router'
import { ChatPreview } from '@/components/landing/ChatPreview'
import { Button } from '@/components/ui/button'
import { SectionEyebrow } from '@/components/ui/primitives'
import { useCopy } from '@/i18n'

const ease = [0.22, 1, 0.36, 1] as const

export function Hero() {
  const t = useCopy()
  const enter = useEntrance()
  return (
    <section className="relative isolate overflow-hidden">
      {/* Quiet, static backdrop: two soft glows and a hairline grid fading out. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-40 left-[-10%] h-[36rem] w-[36rem] rounded-full bg-[radial-gradient(closest-side,var(--glow-b),transparent)]" />
        <div className="absolute right-[-12%] top-24 h-[30rem] w-[30rem] rounded-full bg-[radial-gradient(closest-side,var(--glow-a),transparent)]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] bg-[size:72px_72px] [mask-image:radial-gradient(ellipse_at_top,black_20%,transparent_70%)]" />
      </div>

      <div className="mx-auto grid max-w-7xl items-center gap-14 px-4 pb-20 pt-12 sm:px-6 sm:pt-16 lg:grid-cols-[1.08fr_1fr] lg:gap-10 lg:px-8 lg:pb-28 lg:pt-24">
        <div>
          <motion.div initial={enter({ opacity: 0, y: 10 })} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease }}>
            <SectionEyebrow>{t.hero.eyebrow}</SectionEyebrow>
          </motion.div>
          <motion.h1
            initial={enter({ opacity: 0, y: 18 })}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, ease, delay: 0.08 }}
            className="mt-6 text-balance font-display text-[clamp(2.75rem,7vw,5.5rem)] font-normal leading-[0.98] tracking-[-0.02em] text-foreground"
          >
            {t.hero.titleA}{' '}
            <span className="relative inline-block italic text-lavender">
              {t.hero.titleB}
              <svg aria-hidden viewBox="0 0 300 18" preserveAspectRatio="none" className="absolute -bottom-2 left-0 h-3 w-full">
                <motion.path
                  d="M3 12 C 70 3, 150 3, 297 10"
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth="3"
                  strokeLinecap="round"
                  initial={enter({ pathLength: 0 })}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 1.1, ease, delay: 0.7 }}
                />
              </svg>
            </span>{' '}
            {t.hero.titleC}
          </motion.h1>
          <motion.p
            initial={enter({ opacity: 0, y: 14 })}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease, delay: 0.2 }}
            className="mt-8 max-w-xl text-lg leading-relaxed text-muted-foreground"
          >
            {t.hero.lead}
          </motion.p>
          <motion.div
            initial={enter({ opacity: 0, y: 12 })}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease, delay: 0.3 }}
            className="mt-10 flex flex-wrap items-center gap-3"
          >
            <Button asChild size="lg">
              <Link to="/chat">
                {t.hero.primary}
                <ArrowRight />
              </Link>
            </Button>
            <Button asChild size="lg" variant="ghost">
              <a href="#how-it-works">{t.hero.secondary}</a>
            </Button>
          </motion.div>
          <motion.p
            initial={enter({ opacity: 0 })}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.45 }}
            className="mt-8 flex max-w-lg items-start gap-2.5 text-sm leading-relaxed text-muted-foreground"
          >
            <LockKeyhole className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
            {t.hero.privacy}
          </motion.p>
        </div>
        <ChatPreview />
      </div>
    </section>
  )
}
