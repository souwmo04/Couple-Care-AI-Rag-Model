import { Eraser, Menu, PanelLeftClose, PanelLeftOpen, PanelRight, Settings } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { ChatSidebar } from '@/components/chat/ChatSidebar'
import { Composer, type ComposerHandle } from '@/components/chat/Composer'
import { ContextPanel } from '@/components/chat/ContextPanel'
import { AssistantMessage, UserMessage } from '@/components/chat/MessageItem'
import { WelcomeState } from '@/components/chat/WelcomeState'
import { ThemeToggle } from '@/components/layout/Controls'
import { ModelStatusPill } from '@/components/layout/ModelStatus'
import { useModelState } from '@/hooks/useModelState'
import { useCloudMode } from '@/hooks/useProvider'
import { Button } from '@/components/ui/button'
import { Sheet } from '@/components/ui/overlay'
import { Badge, Skeleton, Tooltip } from '@/components/ui/primitives'
import { useChat, type SendOptions } from '@/hooks/useChat'
import { usePreferences } from '@/hooks/usePreferences'
import { useCopy } from '@/i18n'
import { cn } from '@/lib/utils'
import { TOPIC_IDS, TOPIC_STARTERS, type TopicId } from '@/lib/topics'

export default function ChatPage() {
  const t = useCopy()
  const { prefs } = usePreferences()
  const navigate = useNavigate()
  const { conversationId: routeId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const composerRef = useRef<ComposerHandle>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)

  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileNav, setMobileNav] = useState(false)
  const [mobileContext, setMobileContext] = useState(false)
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [activeCitation, setActiveCitation] = useState<string | null>(null)

  const validRouteId = routeId && /^[0-9a-f]{32}$/.test(routeId) ? routeId : null
  const onCreated = useCallback((id: string) => navigate(`/chat/${id}`, { replace: true }), [navigate])
  const chat = useChat(validRouteId, onCreated)
  const modelState = useModelState()
  const cloud = useCloudMode()
  const opts: SendOptions = { language: prefs.responseLanguage, stage: prefs.relationshipStage }

  // Topic deep links (/chat?topic=communication) prefill the composer — never auto-send.
  const starterLanguage = prefs.responseLanguage === 'auto' ? prefs.uiLanguage : prefs.responseLanguage
  const fillComposer = useCallback(
    (topic: TopicId) => composerRef.current?.setText(TOPIC_STARTERS[starterLanguage][topic]),
    [starterLanguage],
  )
  const prefillTopic = (topic: TopicId) => {
    fillComposer(topic)
    setMobileNav(false)
  }
  // Syncs from the URL (an external source); the mobile menu is closed on a fresh page load anyway.
  useEffect(() => {
    const topic = searchParams.get('topic') as TopicId | null
    if (topic && (TOPIC_IDS as readonly string[]).includes(topic)) {
      fillComposer(topic)
      setSearchParams({}, { replace: true })
    }
  }, [searchParams, setSearchParams, fillComposer])

  // Keep the newest content in view unless the reader has scrolled up.
  useEffect(() => {
    const el = scrollRef.current
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight
  }, [chat.messages])

  const lastAssistant = useMemo(() => [...chat.messages].reverse().find((m) => m.role === 'assistant') ?? null, [chat.messages])
  const selectedMessage = chat.messages.find((m) => m.key === selectedKey) ?? lastAssistant
  const title = chat.messages.find((m) => m.role === 'user')?.content.slice(0, 80) || t.chat.newConversation

  function newConversation() {
    chat.reset()
    setSelectedKey(null)
    setActiveCitation(null)
    setMobileNav(false)
    navigate('/chat')
    composerRef.current?.focus()
  }

  function cite(messageKey: string, citationId: string) {
    setSelectedKey(messageKey)
    setActiveCitation(citationId)
    if (window.matchMedia('(max-width: 1279px)').matches) setMobileContext(true)
  }

  const sidebar = (
    <ChatSidebar
      activeId={chat.conversationId}
      onNew={newConversation}
      onTopic={prefillTopic}
      onDeleted={(id) => {
        if (id === null || id === chat.conversationId) newConversation()
      }}
    />
  )
  const context = <ContextPanel message={selectedMessage} activeCitation={activeCitation} />

  return (
    <div className="flex h-dvh overflow-hidden bg-background">
      <a href="#composer" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground">
        {t.nav.skip}
      </a>

      {/* Desktop sidebar */}
      <aside
        aria-label={t.chat.recent}
        className={cn(
          'hidden shrink-0 overflow-hidden border-r border-border bg-surface-sunken transition-[width] duration-300 ease-out-soft lg:block',
          sidebarOpen ? 'w-72' : 'w-0 border-r-0',
        )}
      >
        <div className="h-full w-72">{sidebar}</div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border px-3 sm:px-4">
          <Button variant="ghost" size="icon" className="lg:hidden" aria-label={t.chat.openMenu} onClick={() => setMobileNav(true)}>
            <Menu />
          </Button>
          <Tooltip content={sidebarOpen ? t.chat.collapseSidebar : t.chat.expandSidebar}>
            <Button
              variant="ghost"
              size="icon"
              className="hidden lg:inline-flex"
              aria-label={sidebarOpen ? t.chat.collapseSidebar : t.chat.expandSidebar}
              aria-expanded={sidebarOpen}
              onClick={() => setSidebarOpen((v) => !v)}
            >
              {sidebarOpen ? <PanelLeftClose /> : <PanelLeftOpen />}
            </Button>
          </Tooltip>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-foreground">{title}</p>
            <div className="hidden items-center gap-1.5 sm:flex">
              <Badge tone="outline" className="py-0 text-[0.68rem]">
                {t.chat.languageBadge}: {t.responseLanguages[prefs.responseLanguage]}
              </Badge>
              <Badge tone="outline" className="py-0 text-[0.68rem]">
                {t.chat.stageBadge}: {t.stages[prefs.relationshipStage]}
              </Badge>
            </div>
          </div>
          <ModelStatusPill className="hidden md:inline-flex" />
          <ModelStatusPill className="md:hidden" showLabel={false} />
          {chat.messages.length > 0 && (
            <Tooltip content={t.chat.clearConversation}>
              <Button variant="ghost" size="icon" aria-label={t.chat.clearConversation} onClick={newConversation}>
                <Eraser />
              </Button>
            </Tooltip>
          )}
          <ThemeToggle className="hidden sm:inline-flex" />
          <Tooltip content={t.nav.settings}>
            <Button asChild variant="ghost" size="icon" aria-label={t.nav.settings}>
              <Link to="/settings">
                <Settings />
              </Link>
            </Button>
          </Tooltip>
          <Button variant="ghost" size="icon" className="xl:hidden" aria-label={t.chat.openContext} onClick={() => setMobileContext(true)}>
            <PanelRight />
          </Button>
        </header>

        <div className="flex min-h-0 flex-1">
          <main id="main" className="flex min-w-0 flex-1 flex-col">
            <div
              ref={scrollRef}
              onScroll={(e) => {
                const el = e.currentTarget
                stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80
              }}
              className="min-h-0 flex-1 overflow-y-auto"
              aria-live="polite"
              aria-busy={chat.isGenerating}
            >
              {chat.loading ? (
                <div className="mx-auto max-w-3xl space-y-6 px-4 py-10">
                  <Skeleton className="ml-auto h-12 w-2/3 rounded-lg" />
                  <Skeleton className="h-24 w-full rounded-lg" />
                  <Skeleton className="ml-auto h-10 w-1/2 rounded-lg" />
                </div>
              ) : chat.loadError ? (
                <div className="mx-auto max-w-xl px-4 py-16 text-center">
                  <p className="font-display text-2xl">{t.chat.errorTitle}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{chat.loadError.message}</p>
                  <div className="mt-6 flex justify-center gap-2">
                    <Button variant="secondary" onClick={() => void chat.load(validRouteId)}>
                      {t.common.retry}
                    </Button>
                    <Button onClick={newConversation}>{t.chat.newConversation}</Button>
                  </div>
                </div>
              ) : chat.messages.length === 0 ? (
                <WelcomeState onTopic={prefillTopic} />
              ) : (
                <div className="mx-auto flex max-w-3xl flex-col gap-7 px-4 py-8">
                  {chat.messages.map((m, i) =>
                    m.role === 'user' ? (
                      <UserMessage key={m.key} message={m} />
                    ) : (
                      <AssistantMessage
                        key={m.key}
                        message={m}
                        conversationId={chat.conversationId}
                        isLast={i === chat.messages.length - 1}
                        canRegenerate={!chat.isGenerating}
                        selected={selectedMessage?.key === m.key}
                        onSelect={() => setSelectedKey(m.key)}
                        onCite={(id) => cite(m.key, id)}
                        onRegenerate={() => chat.regenerate(opts)}
                        onRetry={() => chat.retry(opts)}
                      />
                    ),
                  )}
                </div>
              )}
            </div>

            <div className="shrink-0 bg-gradient-to-t from-background via-background to-transparent px-4 pb-3 pt-2">
              <div className="mx-auto max-w-3xl">
                {modelState === 'offline' && (
                  <p role="status" className="mb-2 rounded-md border border-border bg-surface-sunken px-3.5 py-2 text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">{t.status.modelOffline}.</span> {cloud ? t.status.offlineHelpCloud : t.status.offlineHelp}
                  </p>
                )}
                {modelState === 'backend-down' && (
                  <p role="status" className="mb-2 rounded-md border border-border bg-surface-sunken px-3.5 py-2 text-xs text-muted-foreground">
                    {t.common.backendOffline}
                  </p>
                )}
                <Composer
                  ref={composerRef}
                  generating={chat.isGenerating}
                  onStop={chat.stop}
                  onSend={(text) => {
                    stickToBottom.current = true
                    setSelectedKey(null)
                    setActiveCitation(null)
                    void chat.send(text, opts)
                  }}
                />
              </div>
            </div>
          </main>

          {/* Desktop context panel */}
          <aside aria-label={t.chat.contextPanel} className="hidden w-80 shrink-0 border-l border-border bg-surface-sunken xl:block">
            {context}
          </aside>
        </div>
      </div>

      <Sheet open={mobileNav} onOpenChange={setMobileNav} side="left" title={t.nav.menu} closeLabel={t.common.close}>
        {sidebar}
      </Sheet>
      <Sheet open={mobileContext} onOpenChange={setMobileContext} side="right" title={t.chat.contextPanel} closeLabel={t.common.close}>
        {context}
      </Sheet>
    </div>
  )
}
