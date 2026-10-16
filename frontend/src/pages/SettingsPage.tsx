import { useQueryClient } from '@tanstack/react-query'
import { CircleCheck, CircleX, Monitor, Moon, PlugZap, RefreshCw, Sun, Trash2 } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { ConfirmDialog, Select } from '@/components/ui/overlay'
import { Badge, Card, Field, SectionEyebrow, Segmented, Skeleton, Slider, Switch } from '@/components/ui/primitives'
import { keys, useHealth, useModelStatus, useSettings, useUpdateSettings } from '@/hooks/useBackend'
import { FONT_SCALES, usePreferences, type MotionPreference, type ThemePreference } from '@/hooks/usePreferences'
import { useCopy } from '@/i18n'
import { RELATIONSHIP_STAGES } from '@/lib/stages'
import { api } from '@/services/api'
import type { LanguageCode, RelationshipStage, RuntimeSettings } from '@/types/api'

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="scroll-mt-24">
      <h2 id={`${id}-title`} className="font-display text-2xl">
        {title}
      </h2>
      <Card className="mt-4 divide-y divide-border px-5 sm:px-6">{children}</Card>
    </section>
  )
}

/** A slider that only sends the value to the server when the user lets go.
 *  Callers pass key={value} so a new server value resets the local state. */
function ServerSlider({
  name,
  label,
  hint,
  value,
  limits,
  step,
  format = (v) => String(v),
  onCommit,
}: {
  name: keyof RuntimeSettings
  label: string
  hint?: string
  value: number
  limits?: { min?: number; max?: number }
  step: number
  format?: (v: number) => string
  onCommit: (v: number) => void
}) {
  const [local, setLocal] = useState(value)
  return (
    <Field label={label} hint={hint} htmlFor={`slider-${name}`}>
      <div className="flex w-56 items-center gap-3">
        <Slider
          id={`slider-${name}`}
          label={label}
          value={local}
          min={limits?.min ?? 0}
          max={limits?.max ?? 1}
          step={step}
          onValueChange={setLocal}
          onValueCommit={onCommit}
        />
        <span className="w-12 text-right text-sm tabular-nums text-foreground">{format(local)}</span>
      </div>
    </Field>
  )
}

export default function SettingsPage() {
  const t = useCopy()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { prefs, update, reset } = usePreferences()
  const health = useHealth()
  const settings = useSettings()
  const mutation = useUpdateSettings()
  const model = useModelStatus()
  const [confirm, setConfirm] = useState<'all' | 'prefs' | null>(null)

  function save(values: Partial<RuntimeSettings>) {
    mutation.mutate(values, {
      onSuccess: () => toast.success(t.common.saved),
      onError: (err) => toast.error(`${t.settings.saveError}: ${err.message}`),
    })
  }

  async function testConnection() {
    const res = await model.refetch()
    void qc.invalidateQueries({ queryKey: keys.health })
    if (res.data?.reachable) toast.success(t.settings.connected)
    else toast.error(res.data?.detail ?? t.settings.notConnected)
  }

  async function deleteAll() {
    try {
      const res = await api.deleteAllConversations()
      toast.success(`${t.chat.clearHistoryDone} (${res.deleted})`)
      void qc.invalidateQueries({ queryKey: ['conversations'] })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err))
    }
  }

  async function clearPrefs() {
    reset()
    try {
      const data = await api.resetSettings()
      qc.setQueryData(keys.settings, data)
    } catch {
      /* backend offline: local preferences were still cleared */
    }
    toast.success(t.settings.prefsCleared)
  }

  const values = settings.data?.values
  const limits = settings.data?.limits ?? {}

  return (
    <div className="px-4 pb-24 pt-12 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-3xl">
        <SectionEyebrow>CoupleCare AI</SectionEyebrow>
        <h1 className="mt-3 font-display text-[clamp(2.2rem,5vw,3.25rem)] leading-tight">{t.settings.title}</h1>
        <p className="mt-3 text-muted-foreground">{t.settings.lead}</p>

        <div className="mt-12 space-y-12">
          {/* ------------------------------------------------ Appearance */}
          <Section id="appearance" title={t.settings.appearance}>
            <Field label={t.settings.theme}>
              <Segmented<ThemePreference>
                label={t.settings.theme}
                value={prefs.theme}
                onValueChange={(v) => update({ theme: v })}
                options={[
                  { value: 'light', label: t.nav.themeLight, icon: <Sun /> },
                  { value: 'dark', label: t.nav.themeDark, icon: <Moon /> },
                  { value: 'system', label: t.nav.themeSystem, icon: <Monitor /> },
                ]}
              />
            </Field>
            <Field label={t.settings.motion}>
              <Segmented<MotionPreference>
                label={t.settings.motion}
                value={prefs.motion}
                onValueChange={(v) => update({ motion: v })}
                options={[
                  { value: 'system', label: t.settings.motionSystem },
                  { value: 'reduced', label: t.settings.motionReduced },
                  { value: 'full', label: t.settings.motionFull },
                ]}
              />
            </Field>
            <Field label={t.settings.fontSize}>
              <Segmented<string>
                label={t.settings.fontSize}
                value={String(prefs.fontScale)}
                onValueChange={(v) => update({ fontScale: Number(v) })}
                options={FONT_SCALES.map((s) => ({
                  value: String(s),
                  label: <span style={{ fontSize: `${0.8 * s}rem` }}>Aa</span>,
                }))}
              />
            </Field>
          </Section>

          {/* ------------------------------------------------ Language & relationship */}
          <Section id="language" title={t.settings.language}>
            <Field label={t.settings.uiLanguage}>
              <Segmented<'en' | 'bn'>
                label={t.settings.uiLanguage}
                value={prefs.uiLanguage}
                onValueChange={(v) => update({ uiLanguage: v })}
                options={[
                  { value: 'en', label: 'English' },
                  { value: 'bn', label: 'বাংলা' },
                ]}
              />
            </Field>
            <Field label={t.settings.responseLanguage} htmlFor="set-response-lang">
              <Select<LanguageCode>
                id="set-response-lang"
                label={t.settings.responseLanguage}
                value={prefs.responseLanguage}
                onValueChange={(v) => update({ responseLanguage: v })}
                options={(['auto', 'en', 'bn', 'banglish'] as const).map((v) => ({ value: v, label: t.responseLanguages[v] }))}
              />
            </Field>
            <Field label={t.settings.relationship} hint={t.settings.relationshipHint} htmlFor="set-stage">
              <Select<RelationshipStage>
                id="set-stage"
                label={t.settings.relationship}
                value={prefs.relationshipStage}
                onValueChange={(v) => update({ relationshipStage: v })}
                options={RELATIONSHIP_STAGES.map((v) => ({ value: v, label: t.stages[v] }))}
              />
            </Field>
          </Section>

          {/* ------------------------------------------------ Voice */}
          <Section id="voice" title={t.settings.voice}>
            <Field label={t.settings.voiceFeatures} hint={t.settings.voiceFeaturesHint}>
              <Switch label={t.settings.voiceFeatures} checked={prefs.voice} onCheckedChange={(v) => update({ voice: v })} />
            </Field>
            {prefs.voice && (
              <p className="py-4 text-sm leading-relaxed text-foreground/80">
                {health.data?.voice_input ? t.settings.voiceInputCloud : t.settings.voiceInputLocal}{' '}
                {t.settings.voiceReadAloudNote}
              </p>
            )}
          </Section>

          {/* ------------------------------------------------ Privacy */}
          <Section id="privacy" title={t.settings.privacy}>
            <Field label={t.settings.guestMode} hint={t.settings.guestModeHint}>
              <Switch
                label={t.settings.guestMode}
                checked={prefs.guestMode}
                onCheckedChange={(v) => {
                  update({ guestMode: v })
                  if (v && values?.persistence_enabled) save({ persistence_enabled: false })
                }}
              />
            </Field>
            <Field label={t.settings.persistence} hint={t.settings.persistenceHint}>
              {values ? (
                <Switch
                  label={t.settings.persistence}
                  checked={values.persistence_enabled}
                  disabled={prefs.guestMode || mutation.isPending}
                  onCheckedChange={(v) => save({ persistence_enabled: v })}
                />
              ) : (
                <Skeleton className="h-6 w-11 rounded-full" />
              )}
            </Field>
            <div id="support-region" className="scroll-mt-24">
              <Field label={t.settings.supportRegion} hint={t.settings.supportRegionHint} htmlFor="set-region">
                {values && settings.data ? (
                  <Select<RuntimeSettings['support_region']>
                    id="set-region"
                    label={t.settings.supportRegion}
                    value={values.support_region}
                    onValueChange={(v) => save({ support_region: v })}
                    options={[
                      { value: 'unspecified', label: t.settings.regionUnspecified },
                      ...Object.entries(settings.data.support_regions).map(([k, label]) => ({
                        value: k as RuntimeSettings['support_region'],
                        label,
                      })),
                    ]}
                  />
                ) : (
                  <Skeleton className="h-10 w-40 rounded-full" />
                )}
              </Field>
            </div>
            <div className="flex flex-wrap gap-2 py-5">
              <Button variant="secondary" onClick={() => navigate('/chat')}>
                <RefreshCw /> {t.settings.clearCurrent}
              </Button>
              <Button variant="secondary" className="hover:text-danger" onClick={() => setConfirm('all')}>
                <Trash2 /> {t.settings.deleteAll}
              </Button>
              <Button variant="secondary" onClick={() => setConfirm('prefs')}>
                {t.settings.clearPrefs}
              </Button>
            </div>
            <div className="py-5">
              <h3 className="text-sm font-medium">{t.settings.storedTitle}</h3>
              <ul className="mt-3 space-y-2 text-sm leading-relaxed text-muted-foreground">
                {t.settings.stored.map((s) => (
                  <li key={s} className="flex gap-2">
                    <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-lavender" />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          </Section>

          {/* ------------------------------------------------ Local AI */}
          <Section id="ai" title={t.settings.ai}>
            {settings.isError ? (
              <p className="py-6 text-sm text-muted-foreground">{t.common.backendOffline}</p>
            ) : !values || !settings.data ? (
              <div className="space-y-4 py-6">
                <Skeleton className="h-6 w-2/3" />
                <Skeleton className="h-6 w-1/2" />
                <Skeleton className="h-6 w-3/4" />
              </div>
            ) : (
              <>
                <Field label={t.settings.currentModel} htmlFor="set-model">
                  <Select<string>
                    id="set-model"
                    label={t.settings.currentModel}
                    value={values.model_id}
                    onValueChange={(v) => save({ model_id: v })}
                    options={settings.data.models.map((m) => ({ value: m.id, label: m.display_name }))}
                  />
                </Field>
                <Field
                  label={t.settings.connection}
                  hint={model.data?.detail ?? model.data?.server_model ?? undefined}
                  aside={
                    <Button variant="secondary" size="sm" onClick={() => void testConnection()} disabled={model.isFetching}>
                      <PlugZap /> {t.settings.testConnection}
                    </Button>
                  }
                >
                  {model.isPending ? (
                    <Skeleton className="h-6 w-24 rounded-full" />
                  ) : model.data?.reachable ? (
                    <Badge tone="success">
                      <CircleCheck /> {t.settings.connected}
                    </Badge>
                  ) : (
                    <Badge tone="warning">
                      <CircleX /> {t.settings.notConnected}
                    </Badge>
                  )}
                </Field>
                <Field label={t.settings.embeddingModel}>
                  <span className="text-right text-sm text-muted-foreground">
                    {settings.data.embedding_model} · {settings.data.embedding_device.toUpperCase()}
                  </span>
                </Field>
                <ServerSlider key={values.retrieval_top_k} name="retrieval_top_k" label={t.settings.retrievalDepth} value={values.retrieval_top_k} limits={limits.retrieval_top_k} step={1} onCommit={(v) => save({ retrieval_top_k: v })} />
                <ServerSlider key={values.temperature} name="temperature" label={t.settings.temperature} value={values.temperature} limits={limits.temperature} step={0.05} format={(v) => v.toFixed(2)} onCommit={(v) => save({ temperature: Number(v.toFixed(2)) })} />
                <ServerSlider key={values.max_output_tokens} name="max_output_tokens" label={t.settings.maxLength} value={values.max_output_tokens} limits={limits.max_output_tokens} step={32} onCommit={(v) => save({ max_output_tokens: v })} />
                <details className="group py-2">
                  <summary className="cursor-pointer list-none py-3 text-sm font-medium text-foreground marker:hidden">
                    <span className="inline-flex items-center gap-2">
                      {t.settings.advanced}
                      <span className="text-muted-foreground transition-transform group-open:rotate-90">›</span>
                    </span>
                  </summary>
                  <div className="divide-y divide-border">
                    <ServerSlider key={values.relevance_threshold} name="relevance_threshold" label={t.settings.threshold} value={values.relevance_threshold} limits={limits.relevance_threshold} step={0.05} format={(v) => v.toFixed(2)} onCommit={(v) => save({ relevance_threshold: Number(v.toFixed(2)) })} />
                    <Field label={t.settings.rerank} hint={settings.data.reranker_configured ? undefined : t.settings.rerankUnavailable}>
                      <Switch label={t.settings.rerank} checked={values.rerank_enabled} disabled={!settings.data.reranker_configured} onCheckedChange={(v) => save({ rerank_enabled: v })} />
                    </Field>
                    <Field label={t.settings.expansion}>
                      <Switch label={t.settings.expansion} checked={values.query_expansion_enabled} onCheckedChange={(v) => save({ query_expansion_enabled: v })} />
                    </Field>
                  </div>
                </details>
              </>
            )}
          </Section>

          {/* ------------------------------------------------ About */}
          <Section id="about" title={t.settings.about}>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-1 py-5 text-sm sm:grid-cols-[auto_minmax(0,1fr)] sm:gap-y-3 [&_dd]:mb-2 [&_dd]:min-w-0 [&_dd]:break-words sm:[&_dd]:mb-0">
              <dt className="text-muted-foreground">{t.settings.appVersion}</dt>
              <dd>{settings.data?.about.app_version ?? __APP_VERSION__}</dd>
              <dt className="text-muted-foreground">{t.settings.promptVersion}</dt>
              <dd className="break-all">{settings.data?.about.prompt_version ?? t.common.unknown}</dd>
              <dt className="text-muted-foreground">{t.settings.kbVersion}</dt>
              <dd className="break-all">{settings.data?.about.knowledge_base_version ?? t.common.unknown}</dd>
              <dt className="text-muted-foreground">{t.settings.currentModel}</dt>
              <dd>{model.data?.display_name ?? t.common.unknown}</dd>
              <dt className="text-muted-foreground">{t.settings.modelLicense}</dt>
              <dd>{model.data?.license ?? t.common.unknown}</dd>
            </dl>
            <p className="py-5 text-sm leading-relaxed text-muted-foreground">{t.settings.limitations}</p>
          </Section>
        </div>
      </div>

      <ConfirmDialog
        open={confirm === 'all'}
        onOpenChange={(o) => !o && setConfirm(null)}
        title={t.chat.clearHistoryTitle}
        description={t.chat.clearHistoryBody}
        confirmLabel={t.common.delete}
        cancelLabel={t.common.cancel}
        onConfirm={() => void deleteAll()}
      />
      <ConfirmDialog
        open={confirm === 'prefs'}
        onOpenChange={(o) => !o && setConfirm(null)}
        title={t.settings.clearPrefsTitle}
        description={t.settings.clearPrefsBody}
        confirmLabel={t.common.confirm}
        cancelLabel={t.common.cancel}
        onConfirm={() => void clearPrefs()}
      />
    </div>
  )
}
