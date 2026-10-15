import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Database, FileText, Hammer, Play, RefreshCw, Search } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { languageLabel } from '@/lib/languages'
import { Button } from '@/components/ui/button'
import { ConfirmDialog, Modal, Select } from '@/components/ui/overlay'
import { Badge, Card, SectionEyebrow, Segmented, Skeleton } from '@/components/ui/primitives'
import { keys, useKnowledgeStats } from '@/hooks/useBackend'
import { useCopy } from '@/i18n'
import { topicTitle } from '@/lib/topics'
import { cn } from '@/lib/utils'
import { ApiError, api } from '@/services/api'
import type { KnowledgeStats, RetrievalTestResponse } from '@/types/api'

const ALL = '__all__'

function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card className="p-5">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-foreground">{value}</p>
      {sub && <p className="mt-1 truncate text-xs text-muted-foreground" title={sub}>{sub}</p>}
    </Card>
  )
}

/** Single-series horizontal bars (one hue). Each row is also a readable table row: label + count. */
function Distribution({ title, data, labelFor }: { title: string; data: Record<string, number>; labelFor: (k: string) => string }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1])
  const max = Math.max(1, ...entries.map(([, v]) => v))
  const total = entries.reduce((s, [, v]) => s + v, 0)
  return (
    <Card className="p-5">
      <h3 className="text-sm font-medium text-foreground">{title}</h3>
      <ul className="mt-4 space-y-3">
        {entries.map(([key, value]) => (
          <li key={key} className="group grid grid-cols-[minmax(6rem,9rem)_1fr_auto] items-center gap-3 text-sm" title={`${labelFor(key)}: ${value} (${Math.round((value / total) * 100)}%)`}>
            <span className="truncate text-muted-foreground">{labelFor(key)}</span>
            <span className="h-2.5 rounded-r-[4px] bg-transparent">
              <span
                className="block h-full rounded-r-[4px] bg-lavender transition-opacity group-hover:opacity-80"
                style={{ width: `${(value / max) * 100}%` }}
              />
            </span>
            <span className="tabular-nums text-foreground">{value}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}

function healthBadge(t: ReturnType<typeof useCopy>, stats: KnowledgeStats) {
  const map = {
    healthy: { tone: 'success', label: t.knowledge.healthy },
    lexical_only: { tone: 'warning', label: t.knowledge.lexicalOnly },
    dense_unavailable: { tone: 'warning', label: t.knowledge.denseUnavailable },
    loading: { tone: 'neutral', label: t.knowledge.loadingEmbedder },
    missing: { tone: 'neutral', label: t.knowledge.missing },
    error: { tone: 'danger', label: t.knowledge.error },
  } as const
  const h = map[stats.health]
  return <Badge tone={h.tone}>{h.label}</Badge>
}

export default function KnowledgePage() {
  const t = useCopy()
  const qc = useQueryClient()
  const [confirmRebuild, setConfirmRebuild] = useState(false)
  const stats = useKnowledgeStats(true)
  const rebuilding = stats.data?.rebuild.status === 'running'
  const prevStatus = useRef<string | undefined>(undefined)

  // Announce rebuild completion and refresh dependent views.
  useEffect(() => {
    const status = stats.data?.rebuild.status
    if (prevStatus.current === 'running' && status && status !== 'running') {
      if (status === 'succeeded') toast.success(`${t.knowledge.rebuildDone} — ${stats.data?.rebuild.message ?? ''}`)
      else toast.error(`${t.knowledge.rebuildFailed}: ${stats.data?.rebuild.message ?? ''}`)
      void qc.invalidateQueries({ queryKey: ['knowledge'] })
    }
    prevStatus.current = status
  }, [stats.data, qc, t])

  async function rebuild() {
    try {
      await api.rebuild()
      void qc.invalidateQueries({ queryKey: keys.knowledgeStats })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err))
    }
  }

  const topicLabel = (k: string) => topicTitle(t, k)

  return (
    <div className="px-4 pb-24 pt-12 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <SectionEyebrow>CoupleCare AI</SectionEyebrow>
            <h1 className="mt-3 font-display text-[clamp(2.2rem,5vw,3.25rem)] leading-tight">{t.knowledge.title}</h1>
            <p className="mt-3 text-muted-foreground">{t.knowledge.lead}</p>
          </div>
          <Button onClick={() => setConfirmRebuild(true)} disabled={rebuilding || stats.isError}>
            {rebuilding ? <RefreshCw className="animate-spin" /> : <Hammer />}
            {rebuilding ? t.knowledge.rebuilding : t.knowledge.rebuild}
          </Button>
        </div>

        {stats.isPending ? (
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </div>
        ) : stats.isError ? (
          <Card className="mt-10 p-8 text-center">
            <p className="text-muted-foreground">{stats.error instanceof ApiError ? stats.error.message : t.common.backendOffline}</p>
            <Button variant="secondary" className="mt-4" onClick={() => void stats.refetch()}>
              {t.common.retry}
            </Button>
          </Card>
        ) : !stats.data.available ? (
          <Card className="mt-10 flex flex-col items-center p-12 text-center">
            <Database className="size-10 text-muted-foreground" />
            <p className="mt-4 font-display text-2xl">{t.knowledge.emptyTitle}</p>
            <p className="mt-2 max-w-md text-sm text-muted-foreground">{t.knowledge.emptyBody}</p>
            <Button className="mt-6" onClick={() => setConfirmRebuild(true)} disabled={rebuilding}>
              <Hammer /> {t.knowledge.rebuild}
            </Button>
          </Card>
        ) : (
          <>
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatTile label={t.knowledge.documents} value={String(stats.data.documents)} sub={`${t.knowledge.synthetic}: ${stats.data.synthetic_documents}`} />
              <StatTile label={t.knowledge.passages} value={String(stats.data.passages)} sub={stats.data.chunk_size ? `${stats.data.chunk_size} / ${stats.data.chunk_overlap} chars` : undefined} />
              <StatTile label={t.knowledge.lastBuild} value={stats.data.built_at ? new Date(stats.data.built_at).toLocaleDateString() : '—'} sub={stats.data.version ?? undefined} />
              <Card className="p-5">
                <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">{t.knowledge.health}</p>
                <div className="mt-3">{healthBadge(t, stats.data)}</div>
                <p className="mt-3 truncate text-xs text-muted-foreground" title={stats.data.embedding_model ?? ''}>
                  {t.knowledge.embedding}: {stats.data.embedding_model ?? '—'}
                  {stats.data.embedding_dimension ? ` · ${stats.data.embedding_dimension}d` : ''}
                </p>
              </Card>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <Distribution title={t.knowledge.languages} data={stats.data.languages} labelFor={languageLabel} />
              <Distribution title={t.knowledge.topics} data={stats.data.topics} labelFor={topicLabel} />
            </div>
            <SourceBrowser />
            <RetrievalTest />
            <IngestionErrors count={stats.data.ingestion_errors} lastFailure={stats.data.rebuild.status === 'failed' ? stats.data.rebuild.message : null} />
          </>
        )}
      </div>

      <ConfirmDialog
        open={confirmRebuild}
        onOpenChange={setConfirmRebuild}
        title={t.knowledge.rebuildTitle}
        description={t.knowledge.rebuildBody}
        confirmLabel={t.knowledge.rebuild}
        cancelLabel={t.common.cancel}
        destructive={false}
        onConfirm={() => void rebuild()}
      />
    </div>
  )
}

function SourceBrowser() {
  const t = useCopy()
  const [q, setQ] = useState('')
  const [language, setLanguage] = useState(ALL)
  const [topic, setTopic] = useState(ALL)
  const [page, setPage] = useState(1)
  const [openId, setOpenId] = useState<string | null>(null)
  const params = { q: q.trim() || undefined, language: language === ALL ? undefined : language, topic: topic === ALL ? undefined : topic, page, pageSize: 8 }
  const sources = useQuery({ queryKey: keys.knowledgeSources(params), queryFn: () => api.knowledgeSources(params), placeholderData: (prev) => prev })
  const detail = useQuery({ queryKey: keys.knowledgeSource(openId ?? ''), queryFn: () => api.knowledgeSource(openId!), enabled: !!openId })
  const totalPages = sources.data ? Math.max(1, Math.ceil(sources.data.total / sources.data.page_size)) : 1

  return (
    <section className="mt-14" aria-labelledby="browse-title">
      <h2 id="browse-title" className="font-display text-2xl">{t.knowledge.browse}</h2>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="relative flex-1 sm:min-w-64">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input
            type="search"
            value={q}
            maxLength={100}
            onChange={(e) => {
              setQ(e.target.value)
              setPage(1)
            }}
            placeholder={t.knowledge.searchSources}
            aria-label={t.knowledge.searchSources}
            className="h-10 w-full rounded-full border border-border-strong bg-surface-solid pl-10 pr-4 text-sm outline-none focus:border-lavender"
          />
        </div>
        <Select<string>
          label={t.knowledge.languages}
          value={language}
          onValueChange={(v) => {
            setLanguage(v)
            setPage(1)
          }}
          options={[{ value: ALL, label: t.knowledge.allLanguages }, ...['en', 'bn', 'banglish', 'mixed'].map((v) => ({ value: v, label: languageLabel(v) }))]}
        />
        <Select<string>
          label={t.knowledge.topics}
          value={topic}
          onValueChange={(v) => {
            setTopic(v)
            setPage(1)
          }}
          options={[
            { value: ALL, label: t.knowledge.allTopics },
            ...Object.entries(t.topics.items).map(([k, v]) => ({ value: k, label: v.title })),
            { value: 'safety', label: t.nav.safety },
          ]}
        />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {sources.isPending
          ? [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-28 rounded-xl" />)
          : sources.data?.items.map((s) => (
              <button
                key={s.document_id}
                type="button"
                onClick={() => setOpenId(s.document_id)}
                className="rounded-xl border border-border bg-surface-solid p-4 text-left transition-[border-color,box-shadow] hover:border-border-strong hover:shadow-soft"
              >
                <div className="flex items-start gap-3">
                  <FileText className="mt-0.5 size-4 shrink-0 text-lavender" />
                  <div className="min-w-0">
                    <p className="font-medium text-foreground" lang={s.language === 'bn' ? 'bn' : undefined}>{s.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{s.organization ?? '—'}</p>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {s.synthetic && <Badge tone="coral">{t.common.syntheticBadge}</Badge>}
                  <Badge>{languageLabel(s.language)}</Badge>
                  <Badge>{topicTitle(t, s.topic)}</Badge>
                  <Badge tone="outline">
                    {s.passages} {t.knowledge.passagesCount}
                  </Badge>
                </div>
              </button>
            ))}
      </div>
      {sources.data && sources.data.items.length === 0 && <p className="mt-4 text-sm text-muted-foreground">{t.knowledge.noSources}</p>}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-end gap-2 text-sm">
          <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            ‹
          </Button>
          <span className="tabular-nums text-muted-foreground">
            {page} / {totalPages}
          </span>
          <Button size="sm" variant="secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            ›
          </Button>
        </div>
      )}

      <Modal open={!!openId} onOpenChange={(o) => !o && setOpenId(null)} title={detail.data?.title ?? t.common.loading} closeLabel={t.common.close} wide>
        {detail.isPending ? (
          <Skeleton className="h-40" />
        ) : detail.data ? (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">{t.knowledge.provenance}</h3>
            <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
              <dt className="text-muted-foreground">ID</dt>
              <dd className="break-all">{detail.data.document_id}</dd>
              <dt className="text-muted-foreground">{t.chat.license}</dt>
              <dd>{detail.data.license ?? '—'}</dd>
              <dt className="text-muted-foreground">{t.knowledge.permission}</dt>
              <dd>{detail.data.permission ?? '—'}</dd>
              <dt className="text-muted-foreground">{t.knowledge.path}</dt>
              <dd className="break-all font-mono text-xs">{detail.data.path ?? '—'}</dd>
              <dt className="text-muted-foreground">{t.knowledge.checksum}</dt>
              <dd className="break-all font-mono text-xs">{detail.data.sha256 ?? '—'}</dd>
              {detail.data.url && (
                <>
                  <dt className="text-muted-foreground">URL</dt>
                  <dd className="break-all">{detail.data.url}</dd>
                </>
              )}
            </dl>
            <h3 className="mt-8 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              {t.knowledge.passages} · {detail.data.sections.length}
            </h3>
            <ol className="mt-3 space-y-3">
              {detail.data.sections.map((s) => (
                <li key={s.chunk_id} className="rounded-lg border border-border bg-surface-sunken p-3">
                  <p className="font-mono text-[0.7rem] text-muted-foreground">
                    {s.chunk_id}
                    {s.section ? ` · ${s.section}` : ''}
                  </p>
                  <p className="mt-1.5 text-sm leading-relaxed" lang={s.language === 'bn' ? 'bn' : undefined}>{s.text}</p>
                </li>
              ))}
            </ol>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{detail.error?.message}</p>
        )}
      </Modal>
    </section>
  )
}

function RetrievalTest() {
  const t = useCopy()
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<'hybrid' | 'dense' | 'bm25'>('hybrid')
  const [result, setResult] = useState<RetrievalTestResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)

  async function run(e: FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setRunning(true)
    setError(null)
    try {
      setResult(await api.retrievalTest({ query: query.trim(), top_k: 6, mode, language: 'auto' }))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setRunning(false)
    }
  }

  return (
    <section className="mt-14" aria-labelledby="rt-title">
      <h2 id="rt-title" className="font-display text-2xl">{t.knowledge.retrievalTest}</h2>
      <p className="mt-2 text-sm text-muted-foreground">{t.knowledge.retrievalTestLead}</p>
      <form onSubmit={run} className="mt-4 flex flex-col gap-3 md:flex-row md:items-center">
        <label htmlFor="rt-query" className="sr-only">{t.knowledge.query}</label>
        <input
          id="rt-query"
          value={query}
          maxLength={1000}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="amar shami amar kotha shune na"
          className="h-10 flex-1 rounded-full border border-border-strong bg-surface-solid px-4 text-sm outline-none focus:border-lavender"
        />
        <Segmented
          size="sm"
          label={t.knowledge.mode}
          value={mode}
          onValueChange={setMode}
          options={[
            { value: 'hybrid', label: 'Hybrid' },
            { value: 'dense', label: 'Dense' },
            { value: 'bm25', label: 'BM25' },
          ]}
        />
        <Button type="submit" disabled={running || !query.trim()}>
          {running ? <RefreshCw className="animate-spin" /> : <Play />} {t.knowledge.run}
        </Button>
      </form>
      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
      {result && (
        <div className="mt-5" aria-live="polite">
          <div className="flex flex-wrap gap-1.5 text-xs">
            <Badge>{result.mode}</Badge>
            <Badge>{languageLabel(result.detected_language)}</Badge>
            <Badge tone="outline">{result.duration_ms} ms</Badge>
            {!result.dense_available && <Badge tone="warning">{t.knowledge.denseUnavailable}</Badge>}
            {result.expanded_terms.length > 0 && (
              <Badge tone="lavender">
                {t.knowledge.expanded}: {result.expanded_terms.join(', ')}
              </Badge>
            )}
          </div>
          <ol className="mt-4 space-y-3">
            {result.passages.map((p) => (
              <li key={p.chunk_id} className={cn('rounded-xl border bg-surface-solid p-4', p.above_threshold ? 'border-border' : 'border-dashed border-border opacity-70')}>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="font-semibold text-foreground">#{p.rank}</span>
                  <span className="font-medium text-foreground">{p.title}</span>
                  <span className="text-muted-foreground">
                    {Math.round(p.score * 100)}% · dense {p.dense_rank ?? '—'} · bm25 {p.bm25_rank ?? '—'}
                  </span>
                  {!p.above_threshold && <Badge tone="warning">{t.knowledge.belowThreshold}</Badge>}
                </div>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground" lang={p.language === 'bn' ? 'bn' : undefined}>{p.text}</p>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  )
}

function IngestionErrors({ count, lastFailure }: { count: number; lastFailure: string | null }) {
  const t = useCopy()
  const errors = useQuery({ queryKey: keys.knowledgeErrors, queryFn: api.knowledgeErrors })
  return (
    <section className="mt-14" aria-labelledby="errors-title">
      <h2 id="errors-title" className="font-display text-2xl">{t.knowledge.errors}</h2>
      {lastFailure && (
        <p role="alert" className="mt-3 flex gap-2 rounded-xl border border-border bg-surface-sunken p-3 text-sm text-danger">
          <AlertTriangle className="size-4 shrink-0" /> {lastFailure}
        </p>
      )}
      {count === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">{t.knowledge.noErrors}</p>
      ) : (
        <ul className="mt-4 space-y-2">
          {errors.data?.errors.map((e) => (
            <li key={`${e.document_id}-${e.stage}`} className="rounded-xl border border-border bg-surface-solid p-3 text-sm">
              <span className="font-medium">{e.document_id}</span>
              <span className="text-muted-foreground"> · {e.stage}{e.path ? ` · ${e.path}` : ''}</span>
              <p className="mt-1 text-muted-foreground">{e.error}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
