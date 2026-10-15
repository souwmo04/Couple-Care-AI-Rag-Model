import { AlertDialog, Dialog, Select as SelectPrimitive } from 'radix-ui'
import { Check, ChevronDown, X } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

// ------------------------------------------------------------------ Confirm dialog

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel,
  onConfirm,
  destructive = true,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: string
  confirmLabel: string
  cancelLabel: string
  onConfirm: () => void
  destructive?: boolean
}) {
  return (
    <AlertDialog.Root open={open} onOpenChange={onOpenChange}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-50 bg-[oklch(0.17_0.035_268/0.45)] backdrop-blur-sm animate-fade-up" />
        <AlertDialog.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100vw-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-surface-solid p-6 shadow-lift animate-fade-up">
          <AlertDialog.Title className="font-display text-xl text-foreground">{title}</AlertDialog.Title>
          <AlertDialog.Description className="mt-2 text-sm leading-relaxed text-muted-foreground">
            {description}
          </AlertDialog.Description>
          <div className="mt-6 flex justify-end gap-2">
            <AlertDialog.Cancel asChild>
              <Button variant="ghost">{cancelLabel}</Button>
            </AlertDialog.Cancel>
            <AlertDialog.Action asChild>
              <Button variant={destructive ? 'danger' : 'primary'} onClick={onConfirm}>
                {confirmLabel}
              </Button>
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}

// ------------------------------------------------------------------ Sheet (side drawer)

export function Sheet({
  open,
  onOpenChange,
  side = 'left',
  title,
  closeLabel,
  children,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  side?: 'left' | 'right'
  title: string
  closeLabel: string
  children: ReactNode
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-[oklch(0.17_0.035_268/0.4)] backdrop-blur-sm" />
        <Dialog.Content
          aria-describedby={undefined}
          className={cn(
            'fixed inset-y-0 z-50 flex w-[min(22rem,88vw)] flex-col border-border bg-background shadow-lift outline-none',
            side === 'left' ? 'left-0 border-r animate-[slide-in-left_280ms_var(--ease-out-soft)]' : 'right-0 border-l animate-[slide-in-right_280ms_var(--ease-out-soft)]',
          )}
        >
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <Dialog.Title className="font-display text-lg">{title}</Dialog.Title>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon-sm" aria-label={closeLabel}>
                <X />
              </Button>
            </Dialog.Close>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

// ------------------------------------------------------------------ Modal

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  closeLabel,
  children,
  wide,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  closeLabel: string
  children: ReactNode
  wide?: boolean
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-[oklch(0.17_0.035_268/0.45)] backdrop-blur-sm" />
        <Dialog.Content
          aria-describedby={description ? undefined : undefined}
          className={cn(
            'fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col rounded-lg border border-border bg-surface-solid shadow-lift animate-fade-up',
            wide ? 'max-w-3xl' : 'max-w-lg',
          )}
        >
          <div className="flex items-start justify-between gap-4 border-b border-border p-5">
            <div className="min-w-0">
              <Dialog.Title className="font-display text-xl">{title}</Dialog.Title>
              {description ? (
                <Dialog.Description className="mt-1 text-sm text-muted-foreground">{description}</Dialog.Description>
              ) : (
                <Dialog.Description className="sr-only">{title}</Dialog.Description>
              )}
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon-sm" aria-label={closeLabel}>
                <X />
              </Button>
            </Dialog.Close>
          </div>
          <div className="min-h-0 overflow-y-auto p-5">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

// ------------------------------------------------------------------ Select

export function Select<T extends string>({
  value,
  onValueChange,
  options,
  label,
  id,
  className,
  size = 'md',
}: {
  value: T
  onValueChange: (v: T) => void
  options: { value: T; label: string }[]
  label: string
  id?: string
  className?: string
  size?: 'sm' | 'md'
}) {
  return (
    <SelectPrimitive.Root value={value} onValueChange={(v) => onValueChange(v as T)}>
      <SelectPrimitive.Trigger
        id={id}
        aria-label={label}
        className={cn(
          'inline-flex min-w-36 items-center justify-between gap-2 rounded-full border border-border-strong bg-surface-solid text-foreground transition-colors hover:bg-muted data-[placeholder]:text-muted-foreground',
          size === 'sm' ? 'h-8 px-3 text-xs' : 'h-10 px-4 text-sm',
          className,
        )}
      >
        <SelectPrimitive.Value />
        <SelectPrimitive.Icon>
          <ChevronDown className="size-4 text-muted-foreground" />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          position="popper"
          sideOffset={6}
          className="z-50 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md border border-border bg-surface-solid p-1 shadow-lift animate-fade-up"
        >
          <SelectPrimitive.Viewport>
            {options.map((o) => (
              <SelectPrimitive.Item
                key={o.value}
                value={o.value}
                className="relative flex cursor-pointer select-none items-center rounded-lg py-2 pl-8 pr-3 text-sm text-foreground outline-none data-[highlighted]:bg-muted"
              >
                <SelectPrimitive.ItemIndicator className="absolute left-2.5">
                  <Check className="size-3.5 text-lavender" />
                </SelectPrimitive.ItemIndicator>
                <SelectPrimitive.ItemText>{o.label}</SelectPrimitive.ItemText>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  )
}
