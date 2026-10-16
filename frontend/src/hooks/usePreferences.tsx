/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { RELATIONSHIP_STAGES } from '@/lib/stages'
import type { ChatMode, LanguageCode, RelationshipStage } from '@/types/api'

export type ThemePreference = 'light' | 'dark' | 'system'
export type MotionPreference = 'system' | 'reduced' | 'full'
export type UiLanguage = 'en' | 'bn'

export interface Preferences {
  theme: ThemePreference
  motion: MotionPreference
  fontScale: number
  uiLanguage: UiLanguage
  responseLanguage: LanguageCode
  relationshipStage: RelationshipStage
  chatMode: ChatMode
  guestMode: boolean
}

export const DEFAULT_PREFERENCES: Preferences = {
  // Light by default (the neo-brutalist light theme is the primary design); 'system' and 'dark' stay available.
  theme: 'light',
  motion: 'system',
  fontScale: 1,
  uiLanguage: 'en',
  responseLanguage: 'auto',
  relationshipStage: 'unspecified',
  chatMode: 'support',
  guestMode: false,
}

const PREFS_KEY = 'couplecare.prefs'
const GUEST_KEY = 'couplecare.guest'
export const FONT_SCALES = [0.9, 1, 1.1, 1.2] as const

function safeGet(storage: () => Storage, key: string): string | null {
  try {
    return storage().getItem(key)
  } catch {
    return null
  }
}

function safeSet(storage: () => Storage, key: string, value: string | null): void {
  try {
    if (value === null) storage().removeItem(key)
    else storage().setItem(key, value)
  } catch {
    /* storage unavailable — preferences simply won't persist */
  }
}

function sanitize(raw: unknown): Preferences {
  const p = { ...DEFAULT_PREFERENCES }
  if (!raw || typeof raw !== 'object') return p
  const r = raw as Record<string, unknown>
  if (r.theme === 'light' || r.theme === 'dark' || r.theme === 'system') p.theme = r.theme
  if (r.motion === 'system' || r.motion === 'reduced' || r.motion === 'full') p.motion = r.motion
  if (typeof r.fontScale === 'number' && (FONT_SCALES as readonly number[]).includes(r.fontScale)) p.fontScale = r.fontScale
  if (r.uiLanguage === 'en' || r.uiLanguage === 'bn') p.uiLanguage = r.uiLanguage
  if (['auto', 'en', 'bn', 'banglish'].includes(r.responseLanguage as string)) p.responseLanguage = r.responseLanguage as LanguageCode
  if ((RELATIONSHIP_STAGES as readonly string[]).includes(r.relationshipStage as string))
    p.relationshipStage = r.relationshipStage as RelationshipStage
  if (r.chatMode === 'support' || r.chatMode === 'coach') p.chatMode = r.chatMode
  return p
}

export function loadPreferences(): Preferences {
  const guest = safeGet(() => localStorage, GUEST_KEY) === '1'
  const source = guest ? () => sessionStorage : () => localStorage
  const raw = safeGet(source, PREFS_KEY)
  let parsed: unknown = null
  try {
    parsed = raw ? JSON.parse(raw) : null
  } catch {
    parsed = null
  }
  return { ...sanitize(parsed), guestMode: guest }
}

function savePreferences(prefs: Preferences): void {
  const { guestMode, ...rest } = prefs
  safeSet(() => localStorage, GUEST_KEY, guestMode ? '1' : null)
  if (guestMode) {
    // Guest mode: nothing but the guest flag itself is written to persistent storage.
    safeSet(() => localStorage, PREFS_KEY, null)
    safeSet(() => sessionStorage, PREFS_KEY, JSON.stringify(rest))
  } else {
    safeSet(() => sessionStorage, PREFS_KEY, null)
    safeSet(() => localStorage, PREFS_KEY, JSON.stringify(rest))
  }
}

export function clearStoredPreferences(): void {
  safeSet(() => localStorage, PREFS_KEY, null)
  safeSet(() => sessionStorage, PREFS_KEY, null)
  safeSet(() => localStorage, GUEST_KEY, null)
}

function systemPrefersDark(): boolean {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches
}

interface PreferencesContextValue {
  prefs: Preferences
  resolvedTheme: 'light' | 'dark'
  reducedMotion: boolean
  update: (patch: Partial<Preferences>) => void
  reset: () => void
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null)

export function PreferencesProvider({ children, initial }: { children: ReactNode; initial?: Partial<Preferences> }) {
  const [prefs, setPrefs] = useState<Preferences>(() => ({ ...loadPreferences(), ...initial }))
  const [systemDark, setSystemDark] = useState(systemPrefersDark)
  const [systemReduced, setSystemReduced] = useState(
    () => typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
  )

  useEffect(() => {
    const dark = window.matchMedia?.('(prefers-color-scheme: dark)')
    const motion = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    const onDark = (e: MediaQueryListEvent) => setSystemDark(e.matches)
    const onMotion = (e: MediaQueryListEvent) => setSystemReduced(e.matches)
    dark?.addEventListener?.('change', onDark)
    motion?.addEventListener?.('change', onMotion)
    return () => {
      dark?.removeEventListener?.('change', onDark)
      motion?.removeEventListener?.('change', onMotion)
    }
  }, [])

  const resolvedTheme: 'light' | 'dark' = prefs.theme === 'system' ? (systemDark ? 'dark' : 'light') : prefs.theme
  const reducedMotion = prefs.motion === 'reduced' || (prefs.motion === 'system' && systemReduced)

  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle('dark', resolvedTheme === 'dark')
    root.dataset.theme = resolvedTheme
    root.dataset.motion = reducedMotion ? 'reduced' : 'full'
    root.style.setProperty('--font-scale', String(prefs.fontScale))
    root.lang = prefs.uiLanguage === 'bn' ? 'bn' : 'en'
  }, [resolvedTheme, reducedMotion, prefs.fontScale, prefs.uiLanguage])

  useEffect(() => savePreferences(prefs), [prefs])

  const update = useCallback((patch: Partial<Preferences>) => setPrefs((p) => ({ ...p, ...patch })), [])
  const reset = useCallback(() => {
    clearStoredPreferences()
    setPrefs({ ...DEFAULT_PREFERENCES })
  }, [])

  const value = useMemo(
    () => ({ prefs, resolvedTheme, reducedMotion, update, reset }),
    [prefs, resolvedTheme, reducedMotion, update, reset],
  )
  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>
}

export function usePreferences(): PreferencesContextValue {
  const ctx = useContext(PreferencesContext)
  if (!ctx) throw new Error('usePreferences must be used inside PreferencesProvider')
  return ctx
}
