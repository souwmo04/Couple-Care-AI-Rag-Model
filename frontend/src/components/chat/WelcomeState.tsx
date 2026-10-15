import { StaggerText } from '@/components/kinetic/StaggerText'
import { motion } from 'motion/react'
import { useEntrance } from '@/hooks/useEntrance'
import { LogoMark } from '@/components/layout/Brand'
import { Segmented } from '@/components/ui/primitives'
import { usePreferences } from '@/hooks/usePreferences'
import { useCopy } from '@/i18n'
import { RELATIONSHIP_STAGES } from '@/lib/stages'
import { cn } from '@/lib/utils'
import { TOPIC_ICONS, TOPIC_IDS, TOPIC_TONES, type TopicId } from '@/lib/topics'
import type { LanguageCode, RelationshipStage } from '@/types/api'

export function WelcomeState({ onTopic }: { onTopic: (topic: TopicId) => void }) {
  const t = useCopy()
  const enter = useEntrance()
  const { prefs, update } = usePreferences()
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col px-4 pb-8 pt-10 sm:pt-16">
      <motion.div initial={enter({ opacity: 0, y: 10 })} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
        <span className="flex size-12 rotate-[-4deg] items-center justify-center rounded-md border-2 border-ink bg-highlight text-ink shadow-lift">
          <LogoMark className="size-7" />
        </span>
        <h1 className="mt-6 font-wide text-[clamp(2rem,4.6vw,3.25rem)] font-black uppercase leading-[0.98]">
          <StaggerText animateOnMount>{t.chat.welcomeGreeting}</StaggerText>
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted-foreground">{t.chat.welcomeBody}</p>
      </motion.div>

      <motion.div
        initial={enter({ opacity: 0, y: 10 })}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
        className="mt-8 flex flex-col gap-5 sm:flex-row sm:flex-wrap sm:gap-8"
      >
        <div>
          <p id="welcome-language" className="mb-2 text-xs font-medium text-muted-foreground">
            {t.chat.welcomeLanguage}
          </p>
          <Segmented<LanguageCode>
            size="sm"
            label={t.chat.welcomeLanguage}
            value={prefs.responseLanguage}
            onValueChange={(v) => update({ responseLanguage: v })}
            options={(['auto', 'en', 'bn', 'banglish'] as const).map((v) => ({ value: v, label: t.responseLanguages[v] }))}
          />
        </div>
        <div>
          <p className="mb-2 text-xs font-medium text-muted-foreground">{t.chat.welcomeStage}</p>
          <Segmented<RelationshipStage>
            size="sm"
            label={t.chat.welcomeStage}
            value={prefs.relationshipStage}
            onValueChange={(v) => update({ relationshipStage: v })}
            options={RELATIONSHIP_STAGES.map((v) => ({ value: v, label: t.stages[v] }))}
          />
        </div>
      </motion.div>

      <div className="mt-10 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {TOPIC_IDS.map((id, i) => {
          const Icon = TOPIC_ICONS[id]
          return (
            <motion.button
              key={id}
              type="button"
              onClick={() => onTopic(id)}
              initial={enter({ opacity: 0, y: 8 })}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.15 + i * 0.03 }}
              className="press group flex items-center gap-3.5 rounded-md border-2 border-ink bg-surface-solid p-3.5 text-left dark:border-foreground"
            >
              <span className={cn('flex size-9 shrink-0 items-center justify-center rounded-sm border-2 border-ink', TOPIC_TONES[id])}>
                <Icon className="size-4" />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium text-foreground">{t.topics.items[id].title}</span>
                <span className="block truncate text-xs text-muted-foreground">{t.topics.items[id].body}</span>
              </span>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
