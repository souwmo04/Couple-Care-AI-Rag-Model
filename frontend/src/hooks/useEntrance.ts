import { usePreferences } from '@/hooks/usePreferences'

/** Entrance props for one-off hero animations; disabled entirely under reduced motion. */
export function useEntrance() {
  const { reducedMotion } = usePreferences()
  return (from: Record<string, number>) => (reducedMotion ? false : from)
}
