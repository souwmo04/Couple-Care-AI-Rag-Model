import { Accordion as AccordionPrimitive, Slider as SliderPrimitive, Switch as SwitchPrimitive, ToggleGroup, Tooltip as TooltipPrimitive } from 'radix-ui'
import { ChevronDown } from 'lucide-react'
import { forwardRef, type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

// ------------------------------------------------------------------ Badge

const badgeTones = {
  neutral: 'bg-surface-solid text-foreground',
  lavender: 'bg-lavender-soft text-ink dark:text-foreground',
  coral: 'bg-highlight text-ink',
  success: 'bg-mint text-ink',
  warning: 'bg-highlight text-ink',
  danger: 'bg-accent text-ink',
  outline: 'bg-transparent text-foreground',
} as const

export function Badge({
  tone = 'neutral',
  className,
  children,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof badgeTones }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-sm border-2 border-ink px-2 py-0.5 font-mono text-[0.68rem] font-semibold uppercase leading-5 tracking-wide dark:border-foreground [&_svg]:size-3',
        badgeTones[tone],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  )
}

// ------------------------------------------------------------------ Skeleton

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div aria-hidden className={cn('skeleton rounded-md', className)} {...props} />
}

// ------------------------------------------------------------------ Card

export const Card = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('rounded-lg border bg-surface-solid shadow-lift', className)} {...props} />
))
Card.displayName = 'Card'

// ------------------------------------------------------------------ Switch

export function Switch({
  checked,
  onCheckedChange,
  label,
  disabled,
  id,
}: {
  checked: boolean
  onCheckedChange: (v: boolean) => void
  label: string
  disabled?: boolean
  id?: string
}) {
  return (
    <SwitchPrimitive.Root
      id={id}
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      aria-label={label}
      className="peer relative inline-flex h-7 w-12 shrink-0 cursor-pointer items-center rounded-full border-2 border-ink bg-muted transition-colors data-[state=checked]:bg-accent disabled:cursor-not-allowed disabled:opacity-50 dark:border-foreground"
    >
      <SwitchPrimitive.Thumb className="pointer-events-none block size-5 translate-x-0.5 rounded-full border-2 border-ink bg-surface-solid transition-transform duration-200 ease-out-soft data-[state=checked]:translate-x-[1.25rem] dark:border-foreground" />
    </SwitchPrimitive.Root>
  )
}

// ------------------------------------------------------------------ Segmented control

export function Segmented<T extends string>({
  value,
  onValueChange,
  options,
  label,
  className,
  size = 'md',
}: {
  value: T
  onValueChange: (v: T) => void
  options: { value: T; label: ReactNode; icon?: ReactNode }[]
  label: string
  className?: string
  size?: 'sm' | 'md'
}) {
  return (
    <ToggleGroup.Root
      type="single"
      value={value}
      onValueChange={(v) => v && onValueChange(v as T)}
      aria-label={label}
      className={cn('inline-flex flex-wrap gap-1 rounded-md border bg-surface-solid p-1', className)}
    >
      {options.map((o) => (
        <ToggleGroup.Item
          key={o.value}
          value={o.value}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-sm border-2 border-transparent font-semibold text-muted-foreground transition-colors hover:text-foreground data-[state=on]:border-ink data-[state=on]:bg-highlight data-[state=on]:text-ink [&_svg]:size-3.5',
            size === 'sm' ? 'h-7 px-2.5 text-xs' : 'h-8 px-3.5 text-sm',
          )}
        >
          {o.icon}
          {o.label}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  )
}

// ------------------------------------------------------------------ Slider

export function Slider({
  value,
  onValueChange,
  onValueCommit,
  min,
  max,
  step,
  label,
  id,
}: {
  value: number
  onValueChange: (v: number) => void
  onValueCommit?: (v: number) => void
  min: number
  max: number
  step: number
  label: string
  id?: string
}) {
  return (
    <SliderPrimitive.Root
      id={id}
      value={[value]}
      min={min}
      max={max}
      step={step}
      onValueChange={([v]) => onValueChange(v)}
      onValueCommit={([v]) => onValueCommit?.(v)}
      aria-label={label}
      className="relative flex h-5 w-full touch-none select-none items-center"
    >
      <SliderPrimitive.Track className="relative h-2.5 grow overflow-hidden rounded-sm border-2 border-ink bg-muted dark:border-foreground">
        <SliderPrimitive.Range className="absolute h-full bg-accent" />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb
        aria-label={label}
        className="block size-5 rounded-sm border-2 border-ink bg-highlight shadow-soft transition-transform hover:scale-110 dark:border-foreground"
      />
    </SliderPrimitive.Root>
  )
}

// ------------------------------------------------------------------ Tooltip

export function Tooltip({ content, children, side = 'top' }: { content: ReactNode; children: ReactNode; side?: 'top' | 'bottom' | 'left' | 'right' }) {
  return (
    <TooltipPrimitive.Root delayDuration={300}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={6}
          className="z-50 max-w-xs rounded-sm border-2 border-ink bg-primary px-2.5 py-1.5 text-xs font-semibold text-primary-foreground shadow-soft animate-fade-up"
        >
          {content}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  )
}

export const TooltipProvider = TooltipPrimitive.Provider

// ------------------------------------------------------------------ Accordion

export function Accordion({ items }: { items: { q: string; a: string }[] }) {
  return (
    <AccordionPrimitive.Root type="single" collapsible className="divide-y-2 divide-ink border-y-2 border-ink dark:divide-foreground dark:border-foreground">
      {items.map((item, i) => (
        <AccordionPrimitive.Item key={i} value={`item-${i}`}>
          <AccordionPrimitive.Header>
            <AccordionPrimitive.Trigger className="group flex w-full items-center justify-between gap-6 px-2 py-5 text-left font-wide text-lg font-extrabold leading-snug text-foreground transition-colors hover:bg-highlight hover:text-ink sm:text-xl">
              {item.q}
              <ChevronDown className="size-6 shrink-0 rounded-sm border-2 border-current transition-transform duration-300 group-data-[state=open]:rotate-180" />
            </AccordionPrimitive.Trigger>
          </AccordionPrimitive.Header>
          <AccordionPrimitive.Content className="overflow-hidden data-[state=closed]:animate-[collapse_200ms_ease-out] data-[state=open]:animate-[expand_250ms_ease-out]">
            <p className="max-w-3xl px-2 pb-6 text-base leading-relaxed text-foreground/80">{item.a}</p>
          </AccordionPrimitive.Content>
        </AccordionPrimitive.Item>
      ))}
    </AccordionPrimitive.Root>
  )
}

// ------------------------------------------------------------------ Field helpers

export function Field({
  label,
  hint,
  htmlFor,
  children,
  aside,
}: {
  label: ReactNode
  hint?: ReactNode
  htmlFor?: string
  children: ReactNode
  aside?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-3 py-5 sm:flex-row sm:items-center sm:justify-between sm:gap-8">
      <div className="min-w-0 sm:max-w-sm">
        <label htmlFor={htmlFor} className="text-sm font-medium text-foreground">
          {label}
        </label>
        {hint && <p className="mt-1 text-sm text-muted-foreground">{hint}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-3">
        {children}
        {aside}
      </div>
    </div>
  )
}

export function SectionEyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={cn('kicker inline-block rotate-[-1deg] border-2 border-ink bg-highlight px-2.5 py-1 text-ink', className)}>{children}</p>
  )
}
