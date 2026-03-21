import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'secondary' | 'ghost' | 'destructive' | 'outline'
  size?: 'sm' | 'md' | 'lg' | 'icon'
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'md', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center font-medium transition-colors rounded-sm',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary',
          'disabled:pointer-events-none disabled:opacity-50',
          {
            'bg-accent-primary text-white hover:bg-accent-hover': variant === 'default',
            'bg-bg-elevated text-text-primary hover:bg-bg-hover': variant === 'secondary',
            'hover:bg-bg-hover text-text-secondary hover:text-text-primary': variant === 'ghost',
            'bg-status-error text-white hover:bg-status-error/80': variant === 'destructive',
            'border border-bg-elevated bg-transparent hover:bg-bg-hover text-text-primary': variant === 'outline',
          },
          {
            'h-8 px-3 text-caption': size === 'sm',
            'h-10 px-4 text-body': size === 'md',
            'h-12 px-6 text-body': size === 'lg',
            'h-10 w-10': size === 'icon',
          },
          className
        )}
        {...props}
      />
    )
  }
)

Button.displayName = 'Button'
export { Button }
