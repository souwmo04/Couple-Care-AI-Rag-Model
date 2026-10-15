import { useHealth } from '@/hooks/useBackend'

export type ModelState = 'online' | 'offline' | 'backend-down' | 'checking'

export function useModelState(): ModelState {
  const health = useHealth()
  if (health.isPending) return 'checking'
  if (health.isError) return 'backend-down'
  return health.data.model_server === 'online' ? 'online' : 'offline'
}
