import { BookOpenText, Cpu, Languages } from 'lucide-react'
import { useEntrance } from '@/hooks/useEntrance'
import { motion } from 'motion/react'
import { LogoMark } from '@/components/layout/Brand'
import { Badge } from '@/components/ui/primitives'
import { useCloudMode } from '@/hooks/useProvider'
import { useCopy } from '@/i18n'

const ease = [0.22, 1, 0.36, 1] as const

/**
 * An illustrative, clearly-labelled preview of the chat experience. It is static content written for
 * the landing page — it is not a real conversation and not model output.
 */
export function ChatPreview() {
  const t = useCopy()
  const enter = useEntrance()
  const cloud = useCloudMode()
  return (
    <div className="relative mx-auto w-full max-w-[34rem]">
      <motion.figure
        initial={enter({ opacity: 0, y: 24, scale: 0.98 })}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.9, ease, delay: 0.15 }}
        className="relative overflow-hidden rounded-lg border-[3px] border-ink bg-surface-solid shadow-[8px_8px_0_0_var(--ink)] dark:border-foreground dark:shadow-[8px_8px_0_0_var(--foreground)]"
        aria-label={`${t.hero.previewLabel}. ${t.hero.previewNote}`}
      >
        <div className="flex items-center justify-between border-b-[3px] border-ink bg-lavender-soft px-5 py-3 text-ink dark:border-foreground">
          <div className="flex items-center gap-2">
            <LogoMark className="size-5" />
            <span className="font-wide text-sm font-black uppercase">CoupleCare</span>
          </div>
          <Badge tone="outline" className="whitespace-nowrap">{t.hero.previewLabel}</Badge>
        </div>

        <div className="space-y-4 px-5 py-6 sm:px-6">
          <motion.p
            initial={enter({ opacity: 0, y: 10 })}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease, delay: 0.6 }}
            className="ml-auto max-w-[85%] rounded-md border-2 border-ink bg-highlight px-4 py-3 text-sm font-medium leading-relaxed text-ink shadow-soft"
          >
            {t.hero.previewUser}
          </motion.p>

          <motion.div
            initial={enter({ opacity: 0, y: 10 })}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease, delay: 1.2 }}
            className="max-w-[92%]"
          >
            <p className="rounded-md border-2 border-ink bg-surface-solid px-4 py-3 text-sm leading-relaxed text-foreground shadow-soft dark:border-foreground">
              {t.hero.previewAssistant}
              <span className="ml-1 inline-flex translate-y-[-1px] items-center rounded-sm border-2 border-ink bg-mint px-1 font-mono text-[0.65rem] font-bold text-ink">
                S1
              </span>
            </p>
            <motion.div
              initial={enter({ opacity: 0, y: 8 })}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease, delay: 1.8 }}
              className="mt-3 flex items-start gap-3 rounded-md border-2 border-dashed border-ink bg-surface-sunken px-3.5 py-3 dark:border-foreground"
            >
              <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-sm border-2 border-ink bg-mint text-ink">
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
        <figcaption className="kicker border-t-[3px] border-ink px-5 py-2.5 text-center text-foreground/70 dark:border-foreground">
          {t.hero.previewNote}
        </figcaption>
      </motion.figure>

      <motion.div
        aria-hidden
        initial={enter({ opacity: 0, x: -12 })}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.7, ease, delay: 0.9 }}
        className="absolute -top-5 left-6 hidden rotate-[-3deg] items-center gap-2 rounded-sm border-2 border-ink bg-mint px-3 py-1.5 text-xs font-bold text-ink shadow-soft sm:flex"
      >
        <Languages className="size-3.5" />
        {t.hero.floatingLanguages}
      </motion.div>
      {!cloud && <motion.div
        aria-hidden
        initial={enter({ opacity: 0, x: 12 })}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.7, ease, delay: 1.1 }}
        className="absolute -bottom-5 right-6 hidden rotate-[2deg] items-center gap-2 rounded-sm border-2 border-ink bg-highlight px-3 py-1.5 text-xs font-bold text-ink shadow-soft sm:flex"
      >
        <Cpu className="size-3.5" />
        {t.hero.floatingLocal}
      </motion.div>}
    </div>
  )
}
