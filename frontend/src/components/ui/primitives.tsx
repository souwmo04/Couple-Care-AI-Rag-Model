import { Accordion as AccordionPrimitive, Slider as SliderPrimitive, Switch as SwitchPrimitive, ToggleGroup, Tooltip as TooltipPrimitive } from 'radix-ui'
import { ChevronDown } from 'lucide-react'
import { forwardRef, type HTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

// ------------------------------------------------------------------ Badge

const badgeTones = {
  neutral: 'bg-muted text-muted-foreground',
  lavender: 'bg-lavender-soft text-lavender',
  coral: 'bg-accent-soft text-accent',
  success: 'bg-[color-mix(in_oklch,var(--success)_15%,transparent)] text-success',
  warning: 'bg-[color-mix(in_oklch,var(--warning)_18%,transparent)] text-[color-mix(in_oklch,var(--warning)_70%,var(--foreground))]',
  danger: 'bg-[color-mix(in_oklch,var(--danger)_14%,transparent)] text-danger',
  outline: 'border border-border-strong text-muted-foreground',
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
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium leading-5 [&_svg]:size-3',
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
  <div ref={ref} className={cn('rounded-xl border border-border bg-surface-solid shadow-soft', className)} {...props} />
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
      className="peer relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border border-transparent bg-border-strong transition-colors data-[state=checked]:bg-lavender disabled:cursor-not-allowed disabled:opacity-50"
    >
      <SwitchPrimitive.Thumb className="pointer-events-none block size-5 translate-x-0.5 rounded-full bg-surface-solid shadow-soft transition-transform duration-200 ease-out-soft data-[state=checked]:translate-x-[1.3rem]" />
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
      className={cn('inline-flex flex-wrap gap-1 rounded-full border border-border bg-surface-sunken p-1', className)}
    >
      {options.map((o) => (
        <ToggleGroup.Item
          key={o.value}
          value={o.value}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-full font-medium text-muted-foreground transition-colors hover:text-foreground data-[state=on]:bg-surface-solid data-[state=on]:text-foreground data-[state=on]:shadow-soft [&_svg]:size-3.5',
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
      <SliderPrimitive.Track className="relative h-1.5 grow overflow-hidden rounded-full bg-border-strong">
        <SliderPrimitive.Range className="absolute h-full bg-lavender" />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb
        aria-label={label}
        className="block size-4 rounded-full border-2 border-lavender bg-surface-solid shadow-soft transition-transform hover:scale-110"
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
          className="z-50 max-w-xs rounded-md bg-primary px-2.5 py-1.5 text-xs text-primary-foreground shadow-lift animate-fade-up"
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
    <AccordionPrimitive.Root type="single" collapsible className="divide-y divide-border border-y border-border">
      {items.map((item, i) => (
        <AccordionPrimitive.Item key={i} value={`item-${i}`}>
          <AccordionPrimitive.Header>
            <AccordionPrimitive.Trigger className="group flex w-full items-center justify-between gap-6 py-5 text-left font-display text-lg leading-snug text-foreground transition-colors hover:text-lavender sm:text-xl">
              {item.q}
              <ChevronDown className="size-5 shrink-0 text-muted-foreground transition-transform duration-300 group-data-[state=open]:rotate-180" />
            </AccordionPrimitive.Trigger>
          </AccordionPrimitive.Header>
          <AccordionPrimitive.Content className="overflow-hidden data-[state=closed]:animate-[collapse_200ms_ease-out] data-[state=open]:animate-[expand_250ms_ease-out]">
            <p className="max-w-3xl pb-6 text-base leading-relaxed text-muted-foreground">{item.a}</p>
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
    <p className={cn('text-xs font-semibold uppercase tracking-[0.22em] text-lavender', className)}>{children}</p>
  )
}
