import { Outlet } from 'react-router'
import { SiteFooter } from '@/components/layout/SiteFooter'
import { SiteHeader } from '@/components/layout/SiteHeader'
import { useCopy } from '@/i18n'

export function PublicLayout() {
  const t = useCopy()
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-primary px-4 py-2 text-primary-foreground focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        {t.nav.skip}
      </a>
      <SiteHeader />
      <main id="main" className="flex-1 overflow-x-clip">
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  )
}
