import { Library, MessageSquareText, Plus, Search, Settings, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Wordmark } from '@/components/layout/Brand'
import { ModelStatusPill } from '@/components/layout/ModelStatus'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/overlay'
import { Skeleton } from '@/components/ui/primitives'
import { useConversations } from '@/hooks/useBackend'
import { useCopy } from '@/i18n'
import { cn } from '@/lib/utils'
import { TOPIC_ICONS, TOPIC_IDS, type TopicId } from '@/lib/topics'
import { api } from '@/services/api'
import { useQueryClient } from '@tanstack/react-query'

interface SidebarProps {
  activeId: string | null
  onNew: () => void
  onTopic: (topic: TopicId) => void
  onDeleted: (id: string | null) => void
}

export function ChatSidebar({ activeId, onNew, onTopic, onDeleted }: SidebarProps) {
  const t = useCopy()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [pendingDelete, setPendingDelete] = useState<string | null>(null)
  const [confirmAll, setConfirmAll] = useState(false)
  const conversations = useConversations(query.trim() || undefined)

  async function deleteOne(id: string) {
    try {
      await api.deleteConversation(id)
      toast.success(t.chat.deleted)
      onDeleted(id)
      await qc.invalidateQueries({ queryKey: ['conversations'] })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err))
    }
  }

  async function deleteAll() {
    try {
      await api.deleteAllConversations()
      toast.success(t.chat.clearHistoryDone)
      onDeleted(null)
      await qc.invalidateQueries({ queryKey: ['conversations'] })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err))
    }
  }

  const items = conversations.data?.items ?? []

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 pb-2 pt-4">
        <Wordmark />
      </div>
      <div className="px-3 pt-2">
        <Button className="w-full justify-start" onClick={onNew}>
          <Plus /> {t.chat.newConversation}
        </Button>
        <div className="relative mt-3">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.chat.searchPlaceholder}
            aria-label={t.chat.searchPlaceholder}
            maxLength={100}
            className="h-9 w-full rounded-full border border-border bg-surface-solid pl-9 pr-3 text-sm outline-none placeholder:text-muted-foreground focus:border-border-strong"
          />
        </div>
      </div>

      <div className="mt-4 min-h-0 flex-1 overflow-y-auto px-3">
        <h2 className="px-2 text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{t.chat.recent}</h2>
        <div className="mt-2">
          {conversations.isPending ? (
            <div className="space-y-2 px-2 py-1">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : conversations.isError ? (
            <p className="px-2 py-2 text-xs text-muted-foreground">{t.common.backendOffline}</p>
          ) : items.length === 0 ? (
            <p className="px-2 py-2 text-xs leading-relaxed text-muted-foreground">
              {query ? t.chat.noMatches : t.chat.noConversations}
            </p>
          ) : (
            <ul className="space-y-0.5">
              {items.map((c) => (
                <li key={c.id} className="group relative">
                  <button
                    type="button"
                    onClick={() => navigate(`/chat/${c.id}`)}
                    aria-current={c.id === activeId ? 'page' : undefined}
                    className={cn(
                      'flex w-full items-center gap-2.5 rounded-lg py-2 pl-2.5 pr-9 text-left text-sm transition-colors',
                      c.id === activeId ? 'bg-muted text-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                    )}
                  >
                    <MessageSquareText className="size-4 shrink-0 opacity-60" />
                    <span className="truncate">{c.title || t.chat.untitled}</span>
                  </button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`${t.chat.deleteConversation}: ${c.title}`}
                    onClick={() => setPendingDelete(c.id)}
                    className="absolute right-1 top-1/2 size-7 -translate-y-1/2 text-muted-foreground opacity-100 hover:text-danger sm:opacity-0 sm:group-focus-within:opacity-100 sm:group-hover:opacity-100"
                  >
                    <Trash2 className="!size-3.5" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
          {conversations.data && (
            <p className="mt-3 px-2 text-[0.7rem] leading-relaxed text-muted-foreground">
              {conversations.data.persistence_enabled ? t.chat.historyOn : t.chat.historyOff}
            </p>
          )}
        </div>

        <h2 className="mt-6 px-2 text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{t.chat.topics}</h2>
        <ul className="mt-2 space-y-0.5 pb-4">
          {TOPIC_IDS.map((id) => {
            const Icon = TOPIC_ICONS[id]
            return (
              <li key={id}>
                <button
                  type="button"
                  onClick={() => onTopic(id)}
                  className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  <Icon className="size-4 shrink-0 opacity-70" />
                  {t.topics.items[id].title}
                </button>
              </li>
            )
          })}
        </ul>
      </div>

      <div className="space-y-1 border-t border-border p-3">
        <Link to="/knowledge" className="flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground">
          <Library className="size-4" /> {t.chat.knowledgeSources}
        </Link>
        <Link to="/settings" className="flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground">
          <Settings className="size-4" /> {t.chat.settings}
        </Link>
        <button
          type="button"
          onClick={() => setConfirmAll(true)}
          className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm text-muted-foreground hover:bg-muted hover:text-danger"
        >
          <Trash2 className="size-4" /> {t.chat.clearHistory}
        </button>
        <div className="px-1 pt-2">
          <ModelStatusPill />
        </div>
      </div>

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title={t.chat.deleteConversationTitle}
        description={t.chat.deleteConversationBody}
        confirmLabel={t.common.delete}
        cancelLabel={t.common.cancel}
        onConfirm={() => pendingDelete && void deleteOne(pendingDelete)}
      />
      <ConfirmDialog
        open={confirmAll}
        onOpenChange={setConfirmAll}
        title={t.chat.clearHistoryTitle}
        description={t.chat.clearHistoryBody}
        confirmLabel={t.common.delete}
        cancelLabel={t.common.cancel}
        onConfirm={() => void deleteAll()}
      />
    </div>
  )
}
