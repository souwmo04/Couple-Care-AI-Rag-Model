import { Link } from 'react-router'
import { LogoMark } from '@/components/layout/Brand'
import { useCopy } from '@/i18n'

const YEAR = new Date().getFullYear()
const REPO = 'https://github.com/souwmo04/Couple-Care-AI-Rag-Model'

export function SiteFooter() {
  const t = useCopy()
  const columns = [
    {
      title: t.footer.product,
      links: [
        { to: '/chat', label: t.nav.chat },
        { to: '/knowledge', label: t.nav.knowledge },
        { to: '/settings', label: t.nav.settings },
      ],
    },
    {
      title: t.footer.project,
      links: [
        { to: '/about', label: t.nav.about },
        { to: '/privacy', label: t.nav.privacy },
        { to: '/safety', label: t.nav.safety },
      ],
    },
  ]
  return (
    <footer className="border-t border-border bg-surface-sunken">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr_1fr] lg:px-8">
        <div className="max-w-sm">
          <div className="flex items-center gap-2.5">
            <LogoMark />
            <span className="font-display text-lg">CoupleCare AI</span>
          </div>
          <p className="mt-4 font-display text-2xl italic leading-snug text-foreground">{t.footer.tagline}</p>
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{t.footer.note}</p>
        </div>
        {columns.map((col) => (
          <div key={col.title}>
            <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{col.title}</h2>
            <ul className="mt-4 space-y-2.5">
              {col.links.map((l) => (
                <li key={l.to}>
                  <Link to={l.to} className="text-sm text-foreground hover:text-lavender">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{t.footer.readme}</h2>
          <ul className="mt-4 space-y-2.5 text-sm">
            <li>
              <a href={`${REPO}#readme`} target="_blank" rel="noreferrer" className="text-foreground hover:text-lavender">
                README
              </a>
            </li>
            <li>
              <a href={`${REPO}/tree/main/docs`} target="_blank" rel="noreferrer" className="text-foreground hover:text-lavender">
                docs/
              </a>
            </li>
            <li>
              <a href={`${REPO}/blob/main/LICENSE`} target="_blank" rel="noreferrer" className="text-foreground hover:text-lavender">
                MIT License
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border">
        <p className="mx-auto max-w-7xl px-4 py-5 text-xs text-muted-foreground sm:px-6 lg:px-8">
          {t.footer.version} {__APP_VERSION__} · © {YEAR} CoupleCare AI contributors
        </p>
      </div>
    </footer>
  )
}
