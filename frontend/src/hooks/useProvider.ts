import { useHealth } from '@/hooks/useBackend'

/** True when the backend generates replies with a cloud provider (messages leave this computer). */
export function useCloudMode(): boolean {
  return useHealth().data?.provider === 'groq'
}
