import { BookOpenText, Cpu, Languages } from 'lucide-react'
import { useEntrance } from '@/hooks/useEntrance'
import { motion } from 'motion/react'
import { LogoMark } from '@/components/layout/Brand'
import { Badge } from '@/components/ui/primitives'
import { useCopy } from '@/i18n'

const ease = [0.22, 1, 0.36, 1] as const

/**
 * An illustrative, clearly-labelled preview of the chat experience. It is static content written for
 * the landing page — it is not a real conversation and not model output.
 */
export function ChatPreview() {
  const t = useCopy()
  const enter = useEntrance()
  return (
    <div className="relative mx-auto w-full max-w-[34rem]">
      {/* Organic backdrop */}
      <svg
        aria-hidden
        viewBox="0 0 400 400"
        className="pointer-events-none absolute -inset-10 -z-10 h-[calc(100%+5rem)] w-[calc(100%+5rem)] opacity-90 blur-2xl"
      >
        <defs>
          <linearGradient id="hero-blob" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--glow-a)" />
            <stop offset="100%" stopColor="var(--glow-b)" />
          </linearGradient>
        </defs>
        <path
          fill="url(#hero-blob)"
          d="M318 82c38 39 52 104 33 160s-71 104-131 116-128-14-161-63S24 175 51 121 139 34 199 31s81 12 119 51z"
        />
      </svg>

      <motion.figure
        initial={enter({ opacity: 0, y: 24, scale: 0.98 })}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.9, ease, delay: 0.15 }}
        className="glass relative overflow-hidden rounded-[1.75rem] shadow-lift"
        aria-label={`${t.hero.previewLabel}. ${t.hero.previewNote}`}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
          <div className="flex items-center gap-2">
            <LogoMark className="size-5" />
            <span className="text-sm font-medium">CoupleCare</span>
          </div>
          <Badge tone="outline">{t.hero.previewLabel}</Badge>
        </div>

        <div className="space-y-4 px-5 py-6 sm:px-6">
          <motion.p
            initial={enter({ opacity: 0, y: 10 })}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease, delay: 0.6 }}
            className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-3 text-sm leading-relaxed text-primary-foreground"
          >
            {t.hero.previewUser}
          </motion.p>

          <motion.div
            initial={enter({ opacity: 0, y: 10 })}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease, delay: 1.2 }}
            className="max-w-[92%]"
          >
            <p className="rounded-2xl rounded-bl-md border border-border bg-surface-solid px-4 py-3 text-sm leading-relaxed text-foreground">
              {t.hero.previewAssistant}
              <span className="ml-1 inline-flex translate-y-[-1px] items-center rounded-md bg-lavender-soft px-1.5 text-[0.7rem] font-semibold text-lavender">
                S1
              </span>
            </p>
            <motion.div
              initial={enter({ opacity: 0, y: 8 })}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease, delay: 1.8 }}
              className="mt-3 flex items-start gap-3 rounded-xl border border-border bg-surface-sunken px-3.5 py-3"
            >
              <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg bg-lavender-soft text-lavender">
                <BookOpenText className="size-3.5" />
              </span>
              <span className="min-w-0">
                <span className="block text-xs font-semibold text-foreground">
                  S1 · {t.hero.previewSource}
                </span>
                <span className="block text-xs text-muted-foreground">{t.hero.previewSourceMeta}</span>
              </span>
            </motion.div>
          </motion.div>
        </div>
        <figcaption className="border-t border-border px-5 py-2.5 text-center text-[0.7rem] uppercase tracking-[0.16em] text-muted-foreground">
          {t.hero.previewNote}
        </figcaption>
      </motion.figure>

      <motion.div
        aria-hidden
        initial={enter({ opacity: 0, x: -12 })}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.7, ease, delay: 0.9 }}
        className="glass absolute -top-5 left-8 hidden items-center gap-2 rounded-full px-3.5 py-2 text-xs font-medium shadow-soft sm:flex"
      >
        <Languages className="size-3.5 text-lavender" />
        {t.hero.floatingLanguages}
      </motion.div>
      <motion.div
        aria-hidden
        initial={enter({ opacity: 0, x: 12 })}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.7, ease, delay: 1.1 }}
        className="glass absolute -bottom-5 right-8 hidden items-center gap-2 rounded-full px-3.5 py-2 text-xs font-medium shadow-soft sm:flex"
      >
        <Cpu className="size-3.5 text-accent" />
        {t.hero.floatingLocal}
      </motion.div>
    </div>
  )
}
