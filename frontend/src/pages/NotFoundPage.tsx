import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router'
import { FlipText } from '@/components/kinetic/FlipText'
import { LogoMark } from '@/components/layout/Brand'
import { Button } from '@/components/ui/button'
import { useCopy } from '@/i18n'

export default function NotFoundPage() {
  const t = useCopy()
  return (
    <section className="flex min-h-[60vh] flex-col items-center justify-center px-4 py-24 text-center">
      <LogoMark className="size-12" />
      <p className="mt-8 rotate-[-3deg] rounded-md border-[3px] border-ink bg-accent px-6 py-2 font-wide text-7xl font-black text-ink shadow-lift dark:border-foreground">
        <FlipText duration={2.6}>404</FlipText>
      </p>
      <h1 className="mt-10 font-wide text-3xl font-black uppercase">{t.pages.notFoundTitle}</h1>
      <p className="mt-3 max-w-md text-foreground/80">{t.pages.notFoundBody}</p>
      <Button asChild variant="accent" className="mt-8">
        <Link to="/">
          <ArrowLeft /> {t.pages.home}
        </Link>
      </Button>
    </section>
  )
}
