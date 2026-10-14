import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/services/api'
import type { RuntimeSettings } from '@/types/api'

export const keys = {
  health: ['health'] as const,
  model: ['model-status'] as const,
  settings: ['settings'] as const,
  conversations: (q?: string) => ['conversations', q ?? ''] as const,
  conversation: (id: string) => ['conversation', id] as const,
  knowledgeStats: ['knowledge', 'stats'] as const,
  knowledgeSources: (params: object) => ['knowledge', 'sources', params] as const,
  knowledgeSource: (id: string) => ['knowledge', 'source', id] as const,
  knowledgeErrors: ['knowledge', 'errors'] as const,
}

/** Backend + model-server health, polled so the UI reflects the model starting or stopping. */
export function useHealth() {
  return useQuery({
    queryKey: keys.health,
    queryFn: api.health,
    refetchInterval: 15_000,
    retry: false,
    staleTime: 5_000,
  })
}

export function useModelStatus(enabled = true) {
  return useQuery({ queryKey: keys.model, queryFn: api.modelStatus, enabled, retry: false })
}

export function useSettings() {
  return useQuery({ queryKey: keys.settings, queryFn: api.settings, retry: 1 })
}

export function useUpdateSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (values: Partial<RuntimeSettings>) => api.updateSettings(values),
    onSuccess: (data) => {
      qc.setQueryData(keys.settings, data)
      void qc.invalidateQueries({ queryKey: ['conversations'] })
    },
  })
}

export function useConversations(q?: string) {
  return useQuery({ queryKey: keys.conversations(q), queryFn: () => api.conversations(q), retry: false })
}

export function useKnowledgeStats(poll = false) {
  return useQuery({
    queryKey: keys.knowledgeStats,
    queryFn: api.knowledgeStats,
    refetchInterval: poll ? 1_500 : false,
    retry: false,
  })
}
