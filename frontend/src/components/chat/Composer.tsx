import { ArrowUp, Square, X } from 'lucide-react'
import { forwardRef, useEffect, useImperativeHandle, useRef, useState, type KeyboardEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/overlay'
import { usePreferences } from '@/hooks/usePreferences'
import { useCopy } from '@/i18n'
import { cn } from '@/lib/utils'
import type { LanguageCode } from '@/types/api'

export const MAX_MESSAGE_CHARS = 4000

export interface ComposerHandle {
  setText: (text: string) => void
  focus: () => void
}

interface ComposerProps {
  onSend: (text: string) => void
  onStop: () => void
  generating: boolean
  disabled?: boolean
  className?: string
}

export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer(
  { onSend, onStop, generating, disabled, className },
  ref,
) {
  const t = useCopy()
  const { prefs, update } = usePreferences()
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const areaRef = useRef<HTMLTextAreaElement>(null)

  useImperativeHandle(ref, () => ({
    setText: (value: string) => {
      setText(value)
      setError(null)
      requestAnimationFrame(() => {
        const el = areaRef.current
        if (el) {
          el.focus()
          el.setSelectionRange(value.length, value.length)
        }
      })
    },
    focus: () => areaRef.current?.focus(),
  }))

  // Auto-grow up to a comfortable maximum.
  useEffect(() => {
    const el = areaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`
  }, [text])

  function submit() {
    if (generating) return
    const trimmed = text.trim()
    if (!trimmed) {
      setError(t.chat.emptyInput)
      areaRef.current?.focus()
      return
    }
    if (trimmed.length > MAX_MESSAGE_CHARS) {
      setError(t.chat.tooLong)
      return
    }
    setError(null)
    onSend(trimmed)
    setText('')
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit()
    }
  }

  const over = text.length > MAX_MESSAGE_CHARS
  const near = text.length > MAX_MESSAGE_CHARS * 0.85

  return (
    <form
      className={cn('w-full', className)}
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
    >
      <div
        className={cn(
          'rounded-[1.4rem] border bg-surface-solid shadow-soft transition-[border-color,box-shadow] focus-within:border-border-strong focus-within:shadow-lift',
          error || over ? 'border-danger' : 'border-border',
        )}
      >
        <label htmlFor="composer" className="sr-only">
          {t.chat.composerLabel}
        </label>
        <textarea
          id="composer"
          ref={areaRef}
          value={text}
          rows={1}
          disabled={disabled}
          onChange={(e) => {
            setText(e.target.value)
            if (error) setError(null)
          }}
          onKeyDown={onKeyDown}
          placeholder={t.chat.composerPlaceholder}
          aria-invalid={!!error || over}
          aria-describedby={error ? 'composer-error' : undefined}
          className="block max-h-[220px] min-h-[3.25rem] w-full resize-none bg-transparent px-5 pb-1 pt-4 text-[0.95rem] leading-relaxed text-foreground outline-none placeholder:text-muted-foreground disabled:opacity-60"
        />
        <div className="flex items-center justify-between gap-2 px-3 pb-3 pt-1">
          <Select<LanguageCode>
            size="sm"
            label={t.chat.welcomeLanguage}
            value={prefs.responseLanguage}
            onValueChange={(v) => update({ responseLanguage: v })}
            className="min-w-0 border-transparent bg-transparent"
            options={(['auto', 'en', 'bn', 'banglish'] as const).map((v) => ({ value: v, label: t.responseLanguages[v] }))}
          />
          <div className="flex items-center gap-1.5">
            {near && (
              <span className={cn('text-xs tabular-nums', over ? 'text-danger' : 'text-muted-foreground')}>
                {text.length}/{MAX_MESSAGE_CHARS}
              </span>
            )}
            {text && !generating && (
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={t.chat.clearInput}
                onClick={() => {
                  setText('')
                  areaRef.current?.focus()
                }}
              >
                <X />
              </Button>
            )}
            {generating ? (
              <Button type="button" size="icon" variant="secondary" aria-label={t.chat.stop} onClick={onStop}>
                <Square className="fill-current" />
              </Button>
            ) : (
              <Button type="submit" size="icon" aria-label={t.chat.send} disabled={disabled}>
                <ArrowUp />
              </Button>
            )}
          </div>
        </div>
      </div>
      <p id="composer-error" role="alert" className="mt-2 min-h-4 px-2 text-xs text-danger">
        {error}
      </p>
    </form>
  )
})
