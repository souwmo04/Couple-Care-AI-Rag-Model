import { ArrowRight, Check } from 'lucide-react'
import { Link } from 'react-router'
import { Reveal } from '@/components/landing/Reveal'
import { Button } from '@/components/ui/button'
import { SectionEyebrow } from '@/components/ui/primitives'
import { usePreferences } from '@/hooks/usePreferences'
import { useCloudMode } from '@/hooks/useProvider'
import { useCopy } from '@/i18n'
import { INFO, type InfoPage } from '@/pages/infoContent'

function slug(text: string, index: number) {
  return `section-${index}-${text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`
}

function InfoLayout({ page, highlight }: { page: InfoPage; highlight?: string }) {
  const t = useCopy()
  return (
    <article className="px-4 pb-24 pt-14 sm:px-6 sm:pt-20 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <Reveal className="max-w-3xl">
          <SectionEyebrow>{page.eyebrow}</SectionEyebrow>
          <h1 className="mt-5 text-balance font-wide text-[clamp(2.2rem,5.2vw,3.8rem)] font-black uppercase leading-[0.98]">
            {page.title}
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-muted-foreground">{page.lead}</p>
        </Reveal>

        {highlight && (
          <Reveal className="mt-10 rounded-lg border-2 border-ink bg-highlight p-5 text-sm font-medium leading-relaxed text-ink shadow-soft">
            {highlight}
          </Reveal>
        )}

        <div className="mt-14 grid gap-12 lg:grid-cols-[14rem_1fr]">
          <nav aria-label="On this page" className="hidden lg:block">
            <ul className="sticky top-24 space-y-2 border-l border-border pl-4 text-sm">
              {page.sections.map((s, i) => (
                <li key={s.heading}>
                  <a href={`#${slug(s.heading, i)}`} className="text-muted-foreground hover:text-foreground">
                    {s.heading}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
          <div className="max-w-3xl space-y-12">
            {page.sections.map((section, i) => (
              <Reveal key={section.heading}>
                <section id={slug(section.heading, i)} className="scroll-mt-24">
                  <h2 className="font-display text-2xl sm:text-3xl">{section.heading}</h2>
                  {section.body?.map((p) => (
                    <p key={p.slice(0, 32)} className="mt-4 text-base leading-relaxed text-muted-foreground">
                      {p}
                    </p>
                  ))}
                  {section.list && (
                    <ul className="mt-5 space-y-3">
                      {section.list.map((item) => (
                        <li key={item} className="flex gap-3 text-base leading-relaxed text-foreground">
                          <Check className="mt-1 size-4 shrink-0 text-lavender" aria-hidden />
                          {item}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </Reveal>
            ))}
            <div className="flex flex-wrap gap-3 border-t border-border pt-10">
              <Button asChild>
                <Link to="/chat">
                  {t.nav.start} <ArrowRight />
                </Link>
              </Button>
              <Button asChild variant="secondary">
                <Link to="/settings">{t.nav.settings}</Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </article>
  )
}

function usePage(key: 'about' | 'privacy' | 'safety') {
  const { prefs } = usePreferences()
  return INFO[prefs.uiLanguage][key]
}

export function AboutPage() {
  return <InfoLayout page={usePage('about')} />
}

export function PrivacyPage() {
  const t = useCopy()
  // In cloud mode the page's "stays on this computer" statements no longer hold for generation; say so first.
  return <InfoLayout page={usePage('privacy')} highlight={useCloudMode() ? t.hero.privacyCloud : undefined} />
}

export function SafetyPage() {
  const t = useCopy()
  return <InfoLayout page={usePage('safety')} highlight={t.limits.emergency} />
}
