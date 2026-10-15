import { ArrowRight, CloudUpload, LockKeyhole } from 'lucide-react'
import { motion } from 'motion/react'
import { Link } from 'react-router'
import { Marquee } from '@/components/kinetic/Marquee'
import { StaggerText } from '@/components/kinetic/StaggerText'
import { StretchText } from '@/components/kinetic/StretchText'
import { ChatPreview } from '@/components/landing/ChatPreview'
import { Button } from '@/components/ui/button'
import { useEntrance } from '@/hooks/useEntrance'
import { useCloudMode } from '@/hooks/useProvider'
import { useCopy } from '@/i18n'

const ease = [0.22, 1, 0.36, 1] as const

// Trilingual on purpose — the band says the same thing in English, Bangla and Banglish.
const BAND = ['LISTEN', 'শুনুন', 'SHUNUN', 'UNDERSTAND', 'বুঝুন', 'BUJHUN', 'TALK IT OUT', 'কথা বলুন', 'KOTHA BOLUN', 'REPAIR', 'মিটমাট', 'BOUNDARIES', 'সীমা']

export function Hero() {
  const t = useCopy()
  const enter = useEntrance()
  const cloud = useCloudMode()
  return (
    <section className="relative isolate overflow-hidden border-b">
      {/* Flat dotted paper backdrop */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.18] [background-image:radial-gradient(var(--foreground)_1px,transparent_1.2px)] [background-size:22px_22px]"
      />

      <div className="mx-auto grid max-w-7xl items-center gap-14 px-4 pb-16 pt-10 sm:px-6 sm:pt-14 lg:grid-cols-[1.15fr_0.85fr] lg:gap-12 lg:px-8 lg:pb-24 lg:pt-20">
        <div className="min-w-0">
          <motion.span
            initial={enter({ opacity: 0, x: -12 })}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, ease }}
            className="kicker inline-block rotate-[-1deg] border bg-highlight px-3 py-1.5 text-ink shadow-soft"
          >
            {t.hero.eyebrow}
          </motion.span>

          <h1 className="mt-7 font-wide text-[clamp(2.3rem,9vw,4.4rem)] lg:text-[clamp(3rem,5.3vw,5rem)] font-black uppercase leading-[0.92] text-foreground">
            <span className="block">
              <StaggerText animateOnMount delay={0.05}>
                {t.hero.titleA}
              </StaggerText>
            </span>{' '}
            <motion.span
              initial={enter({ opacity: 0, rotate: 0, scale: 0.9 })}
              animate={{ opacity: 1, rotate: -2, scale: 1 }}
              transition={{ duration: 0.7, ease, delay: 0.35 }}
              className="my-2 inline-block border-[3px] border-ink bg-accent px-3 py-1 text-ink shadow-lift"
            >
              <StretchText>{t.hero.titleB}</StretchText>
            </motion.span>{' '}
            <span className="block">
              <StaggerText animateOnMount delay={0.55}>
                {t.hero.titleC}
              </StaggerText>
            </span>
          </h1>

          <motion.p
            initial={enter({ opacity: 0, y: 14 })}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease, delay: 0.5 }}
            className="mt-8 max-w-xl text-lg leading-relaxed text-foreground/80"
          >
            {t.hero.lead}
          </motion.p>
          <motion.div
            initial={enter({ opacity: 0, y: 12 })}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease, delay: 0.6 }}
            className="mt-10 flex flex-wrap items-center gap-4"
          >
            <Button asChild size="lg" variant="accent">
              <Link to="/chat">
                {t.hero.primary}
                <ArrowRight />
              </Link>
            </Button>
            <Button asChild size="lg" variant="secondary">
              <a href="#how-it-works">{t.hero.secondary}</a>
            </Button>
          </motion.div>
          <motion.p
            initial={enter({ opacity: 0 })}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.75 }}
            className="mt-8 flex max-w-lg items-start gap-2.5 border-l-4 border-ink pl-3 text-sm leading-relaxed text-foreground/80 dark:border-foreground"
          >
            {cloud ? (
              <CloudUpload className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden />
            ) : (
              <LockKeyhole className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
            )}
            {cloud ? t.hero.privacyCloud : t.hero.privacy}
          </motion.p>
        </div>
        <ChatPreview />
      </div>

      <Marquee
        items={BAND}
        speed={38}
        className="border-t-[3px] border-ink bg-highlight py-3 font-wide text-2xl font-black text-ink sm:text-3xl dark:border-foreground"
      />
    </section>
  )
}
