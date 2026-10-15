import { cva, type VariantProps } from 'class-variance-authority'
import { Slot } from 'radix-ui'
import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  // Neo-brutalist: 2px ink border, hard offset shadow that collapses when pressed.
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md border-2 border-ink font-bold tracking-tight transition-[background-color,color,box-shadow,transform] duration-150 ease-out disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0 dark:border-foreground',
  {
    variants: {
      variant: {
        primary: 'press bg-primary text-primary-foreground',
        accent: 'press bg-accent text-accent-foreground',
        secondary: 'press bg-surface-solid text-foreground',
        ghost: 'border-transparent text-foreground hover:border-ink hover:bg-highlight hover:text-ink dark:border-transparent dark:hover:border-foreground',
        subtle: 'border-transparent bg-muted text-foreground hover:border-ink dark:border-transparent dark:hover:border-foreground',
        outline: 'bg-transparent text-foreground hover:bg-highlight hover:text-ink',
        danger: 'press bg-danger text-white',
        link: 'border-transparent text-foreground underline decoration-2 underline-offset-4 hover:bg-highlight hover:text-ink dark:border-transparent',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-5 text-sm',
        lg: 'h-12 px-7 text-base',
        icon: 'size-9',
        'icon-sm': 'size-8',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
)

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, type, ...props }, ref) => {
    const Comp = asChild ? Slot.Root : 'button'
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...(asChild ? {} : { type: type ?? 'button' })}
        {...props}
      />
    )
  },
)
Button.displayName = 'Button'
