import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MotionConfig } from 'motion/react'
import { lazy, Suspense, useState, type ReactNode } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router'
import { Toaster } from 'sonner'
import { PublicLayout } from '@/components/layout/PublicLayout'
import { ScrollManager } from '@/components/layout/ScrollManager'
import { TooltipProvider } from '@/components/ui/primitives'
import { PreferencesProvider, usePreferences } from '@/hooks/usePreferences'
import LandingPage from '@/pages/LandingPage'

const ChatPage = lazy(() => import('@/pages/ChatPage'))
const SettingsPage = lazy(() => import('@/pages/SettingsPage'))
const KnowledgePage = lazy(() => import('@/pages/KnowledgePage'))
const AboutPage = lazy(() => import('@/pages/InfoPages').then((m) => ({ default: m.AboutPage })))
const PrivacyPage = lazy(() => import('@/pages/InfoPages').then((m) => ({ default: m.PrivacyPage })))
const SafetyPage = lazy(() => import('@/pages/InfoPages').then((m) => ({ default: m.SafetyPage })))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'))

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { refetchOnWindowFocus: false, staleTime: 10_000 } },
  })
}

function PageFallback() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center" role="status" aria-live="polite">
      <span className="flex gap-1.5" aria-label="Loading">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-2 rounded-full bg-lavender"
            style={{ animation: `dot-pulse 1.2s ${i * 0.15}s infinite ease-in-out` }}
          />
        ))}
      </span>
    </div>
  )
}

function ThemedShell({ children }: { children: ReactNode }) {
  const { resolvedTheme, reducedMotion } = usePreferences()
  return (
    <MotionConfig reducedMotion={reducedMotion ? 'always' : 'never'}>
      <TooltipProvider>
        {children}
        <Toaster
          theme={resolvedTheme}
          position="bottom-right"
          toastOptions={{ className: 'font-sans !rounded-md !border-border !bg-surface-solid !text-foreground !shadow-lift' }}
        />
      </TooltipProvider>
    </MotionConfig>
  )
}

export function AppRoutes() {
  return (
    <Suspense fallback={<PageFallback />}>
      <ScrollManager />
      <Routes>
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:conversationId" element={<ChatPage />} />
        <Route element={<PublicLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/safety" element={<SafetyPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

export default function App() {
  const [queryClient] = useState(createQueryClient)
  return (
    <QueryClientProvider client={queryClient}>
      <PreferencesProvider>
        <ThemedShell>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </ThemedShell>
      </PreferencesProvider>
    </QueryClientProvider>
  )
}
