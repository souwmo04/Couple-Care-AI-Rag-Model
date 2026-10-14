import {
  AppWindow,
  ArrowRight,
  ArrowUpRight,
  BookOpenText,
  Check,
  CloudOff,
  Cpu,
  Database,
  Feather,
  Languages,
  LockKeyhole,
  Scale,
  Server,
  ShieldCheck,
  X,
} from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { Reveal } from '@/components/landing/Reveal'
import { Button } from '@/components/ui/button'
import { Accordion, Badge, SectionEyebrow, Segmented } from '@/components/ui/primitives'
import { useCopy } from '@/i18n'
import { cn } from '@/lib/utils'
import { TOPIC_ICONS, TOPIC_IDS, TOPIC_TONES } from '@/lib/topics'

function SectionHeading({ eyebrow, title, lead, align = 'left' }: { eyebrow: string; title: string; lead?: string; align?: 'left' | 'center' }) {
  return (
    <Reveal className={cn('max-w-2xl', align === 'center' && 'mx-auto text-center')}>
      <SectionEyebrow>{eyebrow}</SectionEyebrow>
      <h2 className="mt-4 text-balance font-display text-[clamp(2rem,4.2vw,3.25rem)] leading-[1.05] tracking-[-0.015em]">
        {title}
      </h2>
      {lead && <p className="mt-5 text-lg leading-relaxed text-muted-foreground">{lead}</p>}
    </Reveal>
  )
}

function Container({ children, className, id }: { children: ReactNode; className?: string; id?: string }) {
  return (
    <section id={id} className={cn('scroll-mt-20 px-4 py-20 sm:px-6 sm:py-28 lg:px-8', className)}>
      <div className="mx-auto max-w-7xl">{children}</div>
    </section>
  )
}

// ------------------------------------------------------------------ 1. Problem

export function ProblemSection() {
  const t = useCopy()
  return (
    <Container className="border-t border-border">
      <div className="grid gap-14 lg:grid-cols-[1.1fr_1fr] lg:gap-20">
        <SectionHeading eyebrow={t.problem.eyebrow} title={t.problem.title} lead={t.problem.lead} />
        <div className="space-y-px overflow-hidden rounded-2xl border border-border bg-border">
          {t.problem.points.map((p, i) => (
            <Reveal key={p.title} delay={i * 0.08} className="flex gap-5 bg-background p-6 sm:p-7">
              <span className="font-display text-3xl italic leading-none text-accent">0{i + 1}</span>
              <div>
                <h3 className="font-medium text-foreground">{p.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{p.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </Container>
  )
}

// ------------------------------------------------------------------ 2. Features (bento)

export function FeaturesSection() {
  const t = useCopy()
  const f = t.features.items
  return (
    <Container id="features" className="bg-surface-sunken">
      <SectionHeading eyebrow={t.features.eyebrow} title={t.features.title} />
      <div className="mt-14 grid gap-4 md:grid-cols-6">
        {/* Grounded: mini stacked source cards */}
        <Reveal className="group relative overflow-hidden rounded-2xl border border-border bg-surface-solid p-7 md:col-span-4">
          <FeatureIcon icon={BookOpenText} />
          <h3 className="mt-5 font-display text-2xl">{f.grounded.title}</h3>
          <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">{f.grounded.body}</p>
          <div aria-hidden className="mt-8 flex flex-col gap-2 sm:absolute sm:bottom-7 sm:right-7 sm:mt-0 sm:w-64">
            {['S1', 'S2', 'S3'].map((id, i) => (
              <div
                key={id}
                className="flex items-center gap-3 rounded-xl border border-border bg-surface-sunken px-3 py-2.5 transition-transform duration-500 ease-out-soft group-hover:-translate-x-1"
                style={{ transitionDelay: `${i * 60}ms`, opacity: 1 - i * 0.22 }}
              >
                <span className="rounded-md bg-lavender-soft px-1.5 text-[0.7rem] font-semibold text-lavender">{id}</span>
                <span className="h-1.5 flex-1 rounded-full bg-border-strong" />
                <span className="h-1.5 w-8 rounded-full bg-border" />
              </div>
            ))}
          </div>
        </Reveal>
        {/* Language */}
        <Reveal delay={0.06} className="rounded-2xl border border-border bg-surface-solid p-7 md:col-span-2">
          <FeatureIcon icon={Languages} />
          <h3 className="mt-5 font-display text-2xl">{f.language.title}</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.language.body}</p>
          <div aria-hidden className="mt-6 flex flex-wrap gap-2 text-sm">
            <span className="rounded-full border border-border px-3 py-1">Hello</span>
            <span className="rounded-full border border-border px-3 py-1" lang="bn">
              ভালোবাসা
            </span>
            <span className="rounded-full border border-border px-3 py-1">kemon acho</span>
          </div>
        </Reveal>
        {/* Private */}
        <Reveal delay={0.04} className="rounded-2xl border border-border bg-primary p-7 text-primary-foreground md:col-span-2">
          <span className="flex size-10 items-center justify-center rounded-xl bg-[color-mix(in_oklch,var(--primary-foreground)_12%,transparent)]">
            <LockKeyhole className="size-5" />
          </span>
          <h3 className="mt-5 font-display text-2xl">{f.private.title}</h3>
          <p className="mt-2 text-sm leading-relaxed opacity-75">{f.private.body}</p>
        </Reveal>
        {/* Safety */}
        <Reveal delay={0.08} className="rounded-2xl border border-border bg-surface-solid p-7 md:col-span-2">
          <FeatureIcon icon={ShieldCheck} tone="coral" />
          <h3 className="mt-5 font-display text-2xl">{f.safety.title}</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.safety.body}</p>
        </Reveal>
        {/* Balanced */}
        <Reveal delay={0.12} className="rounded-2xl border border-border bg-surface-solid p-7 md:col-span-2">
          <FeatureIcon icon={Scale} />
          <h3 className="mt-5 font-display text-2xl">{f.balanced.title}</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.balanced.body}</p>
        </Reveal>
      </div>
    </Container>
  )
}

function FeatureIcon({ icon: Icon, tone = 'lavender' }: { icon: typeof BookOpenText; tone?: 'lavender' | 'coral' }) {
  return (
    <span
      className={cn(
        'flex size-10 items-center justify-center rounded-xl',
        tone === 'lavender' ? 'bg-lavender-soft text-lavender' : 'bg-accent-soft text-accent',
      )}
    >
      <Icon className="size-5" />
    </span>
  )
}

// ------------------------------------------------------------------ 3. How it works

export function HowItWorksSection() {
  const t = useCopy()
  return (
    <Container id="how-it-works">
      <SectionHeading eyebrow={t.how.eyebrow} title={t.how.title} lead={t.how.lead} />
      <ol className="relative mt-16 grid gap-10 md:grid-cols-4 md:gap-6">
        <div aria-hidden className="absolute left-0 right-0 top-6 hidden h-px bg-gradient-to-r from-transparent via-border-strong to-transparent md:block" />
        {t.how.steps.map((step, i) => (
          <Reveal key={step.title} delay={i * 0.1} className="relative">
            <li className="list-none">
              <span className="relative flex size-12 items-center justify-center rounded-full border border-border-strong bg-background font-display text-lg italic text-lavender">
                {i + 1}
              </span>
              <h3 className="mt-6 font-display text-xl">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
            </li>
          </Reveal>
        ))}
      </ol>
    </Container>
  )
}

// ------------------------------------------------------------------ 4. Topics

export function TopicsSection() {
  const t = useCopy()
  return (
    <Container className="border-t border-border">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <SectionHeading eyebrow={t.topics.eyebrow} title={t.topics.title} lead={t.topics.lead} />
      </div>
      <div className="mt-12 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {TOPIC_IDS.map((id, i) => {
          const Icon = TOPIC_ICONS[id]
          const item = t.topics.items[id]
          return (
            <Reveal key={id} delay={(i % 4) * 0.05}>
              <Link
                to={`/chat?topic=${id}`}
                className="group flex h-full flex-col justify-between gap-8 rounded-2xl border border-border bg-surface-solid p-5 transition-[transform,box-shadow,border-color] duration-300 ease-out-soft hover:-translate-y-0.5 hover:border-border-strong hover:shadow-lift"
              >
                <span className={cn('flex size-10 items-center justify-center rounded-xl', TOPIC_TONES[id])}>
                  <Icon className="size-5" />
                </span>
                <span>
                  <span className="flex items-center justify-between font-medium text-foreground">
                    {item.title}
                    <ArrowUpRight className="size-4 text-muted-foreground transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground" />
                  </span>
                  <span className="mt-1 block text-sm text-muted-foreground">{item.body}</span>
                </span>
              </Link>
            </Reveal>
          )
        })}
      </div>
    </Container>
  )
}

// ------------------------------------------------------------------ 5. Bilingual

export function BilingualSection() {
  const t = useCopy()
  const [lang, setLang] = useState<'en' | 'bn' | 'banglish'>('bn')
  return (
    <Container className="bg-surface-sunken">
      <div className="grid items-center gap-14 lg:grid-cols-2">
        <div>
          <SectionHeading eyebrow={t.bilingual.eyebrow} title={t.bilingual.title} lead={t.bilingual.lead} />
          <p className="mt-6 max-w-xl text-sm text-muted-foreground">{t.bilingual.note}</p>
        </div>
        <Reveal className="rounded-3xl border border-border bg-surface-solid p-6 shadow-soft sm:p-10">
          <Segmented
            label={t.bilingual.eyebrow}
            value={lang}
            onValueChange={setLang}
            options={[
              { value: 'en', label: 'English' },
              { value: 'bn', label: 'বাংলা' },
              { value: 'banglish', label: 'Banglish' },
            ]}
          />
          <div className="relative mt-10 min-h-36" aria-live="polite">
            <AnimatePresence mode="wait">
              <motion.blockquote
                key={lang}
                lang={lang === 'bn' ? 'bn' : 'en'}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.35 }}
                className="font-display text-[clamp(1.6rem,3vw,2.25rem)] leading-snug text-foreground"
              >
                <span className="text-accent">“</span>
                {t.bilingual.samples[lang]}
                <span className="text-accent">”</span>
              </motion.blockquote>
            </AnimatePresence>
          </div>
        </Reveal>
      </div>
    </Container>
  )
}

// ------------------------------------------------------------------ 6. Privacy architecture

export function PrivacySection() {
  const t = useCopy()
  const nodes = [
    { icon: AppWindow, label: t.privacySection.nodes.browser },
    { icon: Server, label: t.privacySection.nodes.backend },
    { icon: Cpu, label: t.privacySection.nodes.model },
    { icon: Database, label: t.privacySection.nodes.index },
  ]
  return (
    <Container id="privacy">
      <div className="grid items-center gap-14 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <SectionHeading eyebrow={t.privacySection.eyebrow} title={t.privacySection.title} lead={t.privacySection.lead} />
          <Reveal className="mt-8 rounded-xl border border-border bg-surface-sunken p-4 text-sm leading-relaxed text-muted-foreground">
            {t.privacySection.caveat}
          </Reveal>
          <Button asChild variant="link" className="mt-4 px-0">
            <Link to="/privacy">
              {t.privacySection.link} <ArrowRight />
            </Link>
          </Button>
        </div>
        <Reveal delay={0.1}>
          <div className="relative rounded-[2rem] border-2 border-dashed border-border-strong p-6 sm:p-10">
            <span className="absolute -top-3 left-8 bg-background px-3 text-xs font-semibold uppercase tracking-[0.18em] text-lavender">
              {t.privacySection.boundary}
            </span>
            <div className="grid grid-cols-2 gap-4">
              {nodes.map(({ icon: Icon, label }) => (
                <div key={label} className="flex flex-col items-center gap-3 rounded-2xl border border-border bg-surface-solid px-3 py-6 text-center shadow-soft">
                  <Icon className="size-6 text-lavender" />
                  <span className="text-sm font-medium">{label}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-6 flex items-center justify-center gap-3 text-sm text-muted-foreground">
            <CloudOff className="size-5" />
            <span className="line-through decoration-accent decoration-2">AI provider API</span>
          </div>
        </Reveal>
      </div>
    </Container>
  )
}

// ------------------------------------------------------------------ 7. Evidence

export function EvidenceSection() {
  const t = useCopy()
  return (
    <Container className="border-t border-border">
      <div className="grid items-center gap-14 lg:grid-cols-2">
        <SectionHeading eyebrow={t.evidence.eyebrow} title={t.evidence.title} lead={t.evidence.lead} />
        <Reveal className="rounded-3xl border border-border bg-surface-solid p-6 shadow-soft sm:p-8">
          <p className="text-base leading-relaxed text-foreground">
            {t.evidence.sampleAnswer}{' '}
            <span className="rounded-md bg-lavender-soft px-1.5 py-0.5 text-xs font-semibold text-lavender">S1</span>.
          </p>
          <div className="mt-6 rounded-2xl border border-border bg-surface-sunken p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold text-lavender">S1</p>
                <p className="mt-1 font-medium text-foreground">{t.evidence.sampleCard.title}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{t.evidence.sampleCard.meta}</p>
              </div>
              <Badge tone="coral">{t.common.syntheticBadge}</Badge>
            </div>
            <p className="mt-4 border-l-2 border-lavender pl-3 text-sm italic leading-relaxed text-muted-foreground">
              {t.evidence.sampleCard.excerpt}
            </p>
          </div>
          <p className="mt-5 text-xs leading-relaxed text-muted-foreground">{t.evidence.disclaimer}</p>
        </Reveal>
      </div>
    </Container>
  )
}

// ------------------------------------------------------------------ 8. Safety & limits

export function LimitsSection() {
  const t = useCopy()
  return (
    <Container className="bg-surface-sunken">
      <SectionHeading eyebrow={t.limits.eyebrow} title={t.limits.title} />
      <div className="mt-12 grid gap-4 md:grid-cols-2">
        {[
          { title: t.limits.canTitle, items: t.limits.can, icon: Check, tone: 'text-success' },
          { title: t.limits.cantTitle, items: t.limits.cant, icon: X, tone: 'text-accent' },
        ].map((col, i) => (
          <Reveal key={col.title} delay={i * 0.08} className="rounded-2xl border border-border bg-surface-solid p-7">
            <h3 className="font-display text-2xl">{col.title}</h3>
            <ul className="mt-5 space-y-3.5">
              {col.items.map((item) => (
                <li key={item} className="flex gap-3 text-sm leading-relaxed text-foreground">
                  <col.icon className={cn('mt-0.5 size-4 shrink-0', col.tone)} aria-hidden />
                  {item}
                </li>
              ))}
            </ul>
          </Reveal>
        ))}
      </div>
      <Reveal className="mt-6 flex flex-col items-start justify-between gap-4 rounded-2xl border border-[color-mix(in_oklch,var(--accent)_35%,transparent)] bg-accent-soft p-5 sm:flex-row sm:items-center">
        <p className="flex items-center gap-3 text-sm font-medium text-foreground">
          <ShieldCheck className="size-5 shrink-0 text-accent" aria-hidden />
          {t.limits.emergency}
        </p>
        <Button asChild variant="secondary" size="sm">
          <Link to="/safety">{t.limits.link}</Link>
        </Button>
      </Reveal>
    </Container>
  )
}

// ------------------------------------------------------------------ 9. FAQ

export function FaqSection() {
  const t = useCopy()
  return (
    <Container id="faq">
      <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr]">
        <SectionHeading eyebrow={t.faq.eyebrow} title={t.faq.title} />
        <Reveal>
          <Accordion items={t.faq.items} />
        </Reveal>
      </div>
    </Container>
  )
}

// ------------------------------------------------------------------ 10. Final CTA

export function FinalCta() {
  const t = useCopy()
  return (
    <section className="px-4 pb-24 sm:px-6 lg:px-8">
      <Reveal className="relative isolate mx-auto max-w-7xl overflow-hidden rounded-[2rem] bg-[oklch(0.21_0.045_268)] px-6 py-16 text-center text-[oklch(0.965_0.014_82)] sm:px-12 sm:py-24">
        <div aria-hidden className="absolute inset-0 -z-10">
          <div className="absolute -left-20 -top-24 h-80 w-80 rounded-full bg-[radial-gradient(closest-side,oklch(0.69_0.13_35/0.35),transparent)]" />
          <div className="absolute -bottom-32 right-0 h-96 w-96 rounded-full bg-[radial-gradient(closest-side,oklch(0.72_0.075_295/0.4),transparent)]" />
        </div>
        <Feather className="mx-auto size-7 text-[oklch(0.82_0.08_35)]" aria-hidden />
        <h2 className="mx-auto mt-6 max-w-2xl text-balance font-display text-[clamp(2rem,4.5vw,3.5rem)] leading-[1.05]">
          {t.cta.title}
        </h2>
        <p className="mx-auto mt-5 max-w-lg text-base opacity-75">{t.cta.body}</p>
        <div className="mt-10 flex flex-wrap justify-center gap-3">
          <Button asChild size="lg" className="bg-[oklch(0.965_0.014_82)] text-[oklch(0.17_0.035_268)]">
            <Link to="/chat">
              {t.cta.primary}
              <ArrowRight />
            </Link>
          </Button>
          <Button asChild size="lg" variant="ghost" className="text-[oklch(0.965_0.014_82)] hover:bg-white/10">
            <Link to="/about">{t.cta.secondary}</Link>
          </Button>
        </div>
      </Reveal>
    </section>
  )
}
