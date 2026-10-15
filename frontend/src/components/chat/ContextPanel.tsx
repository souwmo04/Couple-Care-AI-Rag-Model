import { BookOpenText, LifeBuoy } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Link } from 'react-router'
import { SupportResourceList } from '@/components/chat/SafetyNotice'
import { SourceCardView } from '@/components/chat/SourceCardView'
import { Select } from '@/components/ui/overlay'
import type { UiMessage } from '@/hooks/useChat'
import { usePreferences } from '@/hooks/usePreferences'
import { useCopy } from '@/i18n'
import { RELATIONSHIP_STAGES } from '@/lib/stages'
import type { LanguageCode, RelationshipStage, SourceCard } from '@/types/api'

/** Passages from the same guide are shown as one card ("S1 S2") instead of repeated titles. */
function groupByDocument(sources: SourceCard[]): SourceCard[][] {
  const groups = new Map<string, SourceCard[]>()
  for (const s of sources) groups.set(s.document_id, [...(groups.get(s.document_id) ?? []), s])
  return [...groups.values()]
}

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
        <h2 id="context-sources" className="flex items-center gap-2 font-wide text-base font-black uppercase leading-tight">
          <BookOpenText className="size-4 shrink-0" /> {t.chat.sourcesTitle}
        </h2>
        {sources.length > 0 && <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{t.chat.sourcesExplain}</p>}
        {!message || message.status === 'error' ? (
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{t.chat.selectMessage}</p>
        ) : sources.length === 0 ? (
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            {message.status === 'streaming' ? t.chat.thinking : t.chat.noSources}
          </p>
        ) : (
          <div className="mt-4 space-y-4">
            {sources.some((s) => s.synthetic) && (
              <p className="rounded-sm border-2 border-dashed border-ink px-3 py-2 text-xs leading-relaxed dark:border-foreground">
                {t.chat.syntheticNote}
              </p>
            )}
            {groupByDocument(sources).map((group) => (
              <SourceCardView
                key={group[0].chunk_id}
                source={group[0]}
                citationIds={group.map((g) => g.citation_id)}
                active={group.some((g) => g.citation_id === activeCitation)}
                ref={(el) => {
                  for (const g of group) {
                    if (el) refs.current.set(g.citation_id, el)
                    else refs.current.delete(g.citation_id)
                  }
                }}
              />
            ))}
          </div>
        )}

        {resources.length > 0 && (
          <div className="mt-8">
            <h2 className="flex items-center gap-2 font-wide text-base font-black uppercase">
              <LifeBuoy className="size-4" /> {t.chat.supportResources}
            </h2>
            <div className="mt-3">
              <SupportResourceList resources={resources} />
            </div>
          </div>
        )}
      </section>

      <section className="space-y-4 border-t p-4" aria-labelledby="context-settings">
        <h2 id="context-settings" className="kicker text-foreground">
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
            options={RELATIONSHIP_STAGES.map((v) => ({ value: v, label: t.stages[v] }))}
          />
        </div>
        <Link to="/settings" className="inline-block text-xs font-bold underline decoration-2 underline-offset-2">
          {t.nav.settings} →
        </Link>
      </section>
    </div>
  )
}
