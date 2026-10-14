import { usePreferences } from '@/hooks/usePreferences'
import { bn } from './bn'
import { en, type Copy } from './en'

export const COPY: Record<'en' | 'bn', Copy> = { en, bn }

export function useCopy(): Copy {
  const { prefs } = usePreferences()
  return COPY[prefs.uiLanguage] ?? en
}

export type { Copy }
