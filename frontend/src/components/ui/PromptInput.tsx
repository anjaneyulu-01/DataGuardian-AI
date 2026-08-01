import { ArrowUp, Sparkles } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { cn } from '@/utils'

interface PromptInputProps {
  onSubmit: (prompt: string) => void
  placeholder?: string
  /** Example prompts rendered as one-click chips under the input. */
  examples?: string[]
  disabled?: boolean
  /** Large hero variant for the Investigator landing state. */
  size?: 'default' | 'hero'
}

/** The AI prompt box — the product's front door. */
export function PromptInput({
  onSubmit,
  placeholder = 'Ask DataGuardian…',
  examples = [],
  disabled,
  size = 'default',
}: PromptInputProps) {
  const [value, setValue] = useState('')

  const submit = (prompt: string) => {
    const trimmed = prompt.trim()
    if (!trimmed || disabled) return
    onSubmit(trimmed)
    setValue('')
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    submit(value)
  }

  return (
    <div>
      <form
        onSubmit={handleSubmit}
        className={cn(
          'card focus-within:shadow-glow flex items-center gap-3 transition-shadow',
          size === 'hero' ? 'px-5 py-4' : 'px-4 py-2.5',
        )}
      >
        <Sparkles
          className={cn(
            'text-brand-strong shrink-0',
            size === 'hero' ? 'size-5' : 'size-4',
          )}
        />
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className={cn(
            'text-ink placeholder:text-faint w-full bg-transparent outline-none',
            size === 'hero' ? 'text-[15px]' : 'text-sm',
          )}
          aria-label="Ask DataGuardian"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          aria-label="Send prompt"
          className={cn(
            'grid shrink-0 place-items-center rounded-lg transition-all',
            size === 'hero' ? 'size-9' : 'size-7',
            value.trim() && !disabled
              ? 'bg-brand text-white shadow-glow'
              : 'bg-raised text-faint',
          )}
        >
          <ArrowUp className={size === 'hero' ? 'size-4.5' : 'size-3.5'} />
        </button>
      </form>

      {examples.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {examples.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => submit(example)}
              disabled={disabled}
              className="border-line bg-surface/60 text-muted hover:border-brand/40 hover:text-ink rounded-full border px-3 py-1.5 text-[12px] transition-colors"
            >
              {example}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}
