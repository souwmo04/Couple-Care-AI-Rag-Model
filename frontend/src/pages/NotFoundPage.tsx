import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router'
import { LogoMark } from '@/components/layout/Brand'
import { Button } from '@/components/ui/button'
import { useCopy } from '@/i18n'

export default function NotFoundPage() {
  const t = useCopy()
  return (
    <section className="flex min-h-[60vh] flex-col items-center justify-center px-4 py-24 text-center">
      <LogoMark className="size-12 text-muted-foreground" />
      <p className="mt-8 font-display text-6xl italic text-lavender">404</p>
      <h1 className="mt-4 font-display text-3xl">{t.pages.notFoundTitle}</h1>
      <p className="mt-3 max-w-md text-muted-foreground">{t.pages.notFoundBody}</p>
      <Button asChild className="mt-8">
        <Link to="/">
          <ArrowLeft /> {t.pages.home}
        </Link>
      </Button>
    </section>
  )
}
