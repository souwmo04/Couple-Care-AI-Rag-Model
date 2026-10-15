import { Menu, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router'
import { Wordmark } from '@/components/layout/Brand'
import { LanguageSwitcher, ThemeToggle } from '@/components/layout/Controls'
import { Button } from '@/components/ui/button'
import { useCopy } from '@/i18n'
import { cn } from '@/lib/utils'

export function SiteHeader() {
  const t = useCopy()
  const location = useLocation()
  // The mobile menu is "open at" a location, so navigating anywhere closes it without an effect.
  const here = location.pathname + location.hash
  const [openAt, setOpenAt] = useState<string | null>(null)
  const open = openAt === here
  const setOpen = (fn: (v: boolean) => boolean) => setOpenAt(fn(open) ? here : null)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const links = [
    { to: '/#features', label: t.nav.features },
    { to: '/#how-it-works', label: t.nav.how },
    { to: '/about', label: t.nav.approach },
    { to: '/privacy', label: t.nav.privacy },
  ]

  return (
    <header
      className={cn(
        'sticky top-0 z-40 border-b-[3px] transition-[background-color,border-color] duration-200',
        scrolled || open ? 'border-ink bg-background dark:border-foreground' : 'border-transparent bg-background/0',
      )}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        <Wordmark />
        <nav aria-label="Primary" className="ml-6 hidden items-center gap-1 lg:flex">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className="rounded-sm border-2 border-transparent px-3 py-1 text-sm font-semibold text-foreground transition-colors hover:border-ink hover:bg-highlight hover:text-ink dark:hover:border-foreground"
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-1">
          <LanguageSwitcher className="hidden sm:inline-flex" />
          <ThemeToggle />
          <Button asChild size="sm" variant="accent" className="ml-2 hidden sm:inline-flex">
            <Link to="/chat">{t.nav.start}</Link>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label={open ? t.nav.close : t.nav.menu}
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X /> : <Menu />}
          </Button>
        </div>
      </div>
      <AnimatePresence>
        {open && (
          <motion.nav
            id="mobile-nav"
            aria-label="Mobile"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden border-t-2 border-ink lg:hidden dark:border-foreground"
          >
            <div className="flex flex-col gap-1 px-4 py-4">
              {links.map((l) => (
                <Link key={l.to} to={l.to} className="rounded-sm border-2 border-transparent px-3 py-2.5 font-wide text-lg font-extrabold uppercase text-foreground hover:border-ink hover:bg-highlight hover:text-ink">
                  {l.label}
                </Link>
              ))}
              <div className="mt-2 flex items-center justify-between gap-2 border-t border-border pt-4">
                <LanguageSwitcher />
                <Button asChild size="sm">
                  <Link to="/chat">{t.nav.start}</Link>
                </Button>
              </div>
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  )
}
