import { DropdownMenu } from 'radix-ui'
import { Check, Languages, Monitor, Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip } from '@/components/ui/primitives'
import { usePreferences, type ThemePreference, type UiLanguage } from '@/hooks/usePreferences'
import { useCopy } from '@/i18n'
import { cn } from '@/lib/utils'

const menuContent =
  'z-50 min-w-40 rounded-xl border border-border bg-surface-solid p-1 shadow-lift animate-fade-up'
const menuItem =
  'flex cursor-pointer select-none items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-foreground outline-none data-[highlighted]:bg-muted [&_svg]:size-4'

export function ThemeToggle({ className }: { className?: string }) {
  const { prefs, resolvedTheme, update } = usePreferences()
  const t = useCopy()
  const options: { value: ThemePreference; label: string; icon: typeof Sun }[] = [
    { value: 'light', label: t.nav.themeLight, icon: Sun },
    { value: 'dark', label: t.nav.themeDark, icon: Moon },
    { value: 'system', label: t.nav.themeSystem, icon: Monitor },
  ]
  const Icon = resolvedTheme === 'dark' ? Moon : Sun
  return (
    <DropdownMenu.Root>
      <Tooltip content={t.nav.theme}>
        <DropdownMenu.Trigger asChild>
          <Button variant="ghost" size="icon" aria-label={`${t.nav.theme}: ${prefs.theme}`} className={className}>
            <Icon />
          </Button>
        </DropdownMenu.Trigger>
      </Tooltip>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="end" sideOffset={8} className={menuContent}>
          <DropdownMenu.RadioGroup value={prefs.theme} onValueChange={(v) => update({ theme: v as ThemePreference })}>
            {options.map(({ value, label, icon: ItemIcon }) => (
              <DropdownMenu.RadioItem key={value} value={value} className={menuItem}>
                <ItemIcon className="text-muted-foreground" />
                <span className="flex-1">{label}</span>
                <DropdownMenu.ItemIndicator>
                  <Check className="text-lavender" />
                </DropdownMenu.ItemIndicator>
              </DropdownMenu.RadioItem>
            ))}
          </DropdownMenu.RadioGroup>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}

export function LanguageSwitcher({ className, compact = false }: { className?: string; compact?: boolean }) {
  const { prefs, update } = usePreferences()
  const t = useCopy()
  const options: { value: UiLanguage; label: string }[] = [
    { value: 'en', label: 'English' },
    { value: 'bn', label: 'বাংলা' },
  ]
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <Button
          variant="ghost"
          size={compact ? 'icon' : 'sm'}
          aria-label={t.nav.language}
          className={cn(!compact && 'gap-1.5 px-2.5', className)}
        >
          <Languages />
          {!compact && <span className="text-sm">{prefs.uiLanguage === 'bn' ? 'বাংলা' : 'EN'}</span>}
        </Button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="end" sideOffset={8} className={menuContent}>
          <DropdownMenu.Label className="px-2.5 py-1.5 text-xs text-muted-foreground">{t.nav.language}</DropdownMenu.Label>
          <DropdownMenu.RadioGroup value={prefs.uiLanguage} onValueChange={(v) => update({ uiLanguage: v as UiLanguage })}>
            {options.map((o) => (
              <DropdownMenu.RadioItem key={o.value} value={o.value} className={menuItem} lang={o.value}>
                <span className="flex-1">{o.label}</span>
                <DropdownMenu.ItemIndicator>
                  <Check className="text-lavender" />
                </DropdownMenu.ItemIndicator>
              </DropdownMenu.RadioItem>
            ))}
          </DropdownMenu.RadioGroup>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
