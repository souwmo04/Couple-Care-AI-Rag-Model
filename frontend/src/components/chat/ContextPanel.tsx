import { BookOpenText, LifeBuoy } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Link } from 'react-router'
import { SupportResourceList } from '@/components/chat/SafetyNotice'
import { SourceCardView } from '@/components/chat/SourceCardView'
import { Select } from '@/components/ui/overlay'
import type { UiMessage } from '@/hooks/useChat'
import { usePreferences } from '@/hooks/usePreferences'
import { useCopy } from '@/i18n'
import type { LanguageCode, RelationshipStage } from '@/types/api'

interface ContextPanelProps {
  message: UiMessage | null
  activeCitation: string | null
}

/** Right-hand panel: sources for the selected reply, plus this conversation's settings. */
export function ContextPanel({ message, activeCitation }: ContextPanelProps) {
  const t = useCopy()
  const { prefs, update } = usePreferences()
  const refs = useRef(new Map<string, HTMLDivElement>())

  useEffect(() => {
    if (!activeCitation) return
    const el = refs.current.get(activeCitation)
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    el?.focus({ preventScroll: true })
  }, [activeCitation, message])

  const sources = message?.sources ?? []
  const resources = message?.safety?.resources ?? []

  return (
    <div className="flex h-full flex-col">
      <section className="min-h-0 flex-1 overflow-y-auto p-4" aria-labelledby="context-sources">
        <h2 id="context-sources" className="flex items-center gap-2 text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          <BookOpenText className="size-3.5" /> {t.chat.sources}
        </h2>
        {!message || message.status === 'error' ? (
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{t.chat.selectMessage}</p>
        ) : sources.length === 0 ? (
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            {message.status === 'streaming' ? t.chat.thinking : t.chat.noSources}
          </p>
        ) : (
          <div className="mt-4 space-y-3">
            {sources.map((s) => (
              <SourceCardView
                key={s.chunk_id}
                source={s}
                active={activeCitation === s.citation_id}
                ref={(el) => {
                  if (el) refs.current.set(s.citation_id, el)
                  else refs.current.delete(s.citation_id)
                }}
              />
            ))}
          </div>
        )}

        {resources.length > 0 && (
          <div className="mt-8">
            <h2 className="flex items-center gap-2 text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              <LifeBuoy className="size-3.5" /> {t.chat.supportResources}
            </h2>
            <div className="mt-3">
              <SupportResourceList resources={resources} />
            </div>
          </div>
        )}
      </section>

      <section className="space-y-4 border-t border-border p-4" aria-labelledby="context-settings">
        <h2 id="context-settings" className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          {t.chat.conversationSettings}
        </h2>
        <div className="flex items-center justify-between gap-3">
          <label htmlFor="ctx-language" className="text-sm text-foreground">
            {t.chat.welcomeLanguage}
          </label>
          <Select<LanguageCode>
            id="ctx-language"
            size="sm"
            label={t.chat.welcomeLanguage}
            value={prefs.responseLanguage}
            onValueChange={(v) => update({ responseLanguage: v })}
            options={(['auto', 'en', 'bn', 'banglish'] as const).map((v) => ({ value: v, label: t.responseLanguages[v] }))}
          />
        </div>
        <div className="flex items-center justify-between gap-3">
          <label htmlFor="ctx-stage" className="text-sm text-foreground">
            {t.chat.welcomeStage}
          </label>
          <Select<RelationshipStage>
            id="ctx-stage"
            size="sm"
            label={t.chat.welcomeStage}
            value={prefs.relationshipStage}
            onValueChange={(v) => update({ relationshipStage: v })}
            options={(['unspecified', 'dating', 'engaged', 'married'] as const).map((v) => ({ value: v, label: t.stages[v] }))}
          />
        </div>
        <Link to="/settings" className="inline-block text-xs text-lavender hover:underline">
          {t.nav.settings} →
        </Link>
      </section>
    </div>
  )
}
