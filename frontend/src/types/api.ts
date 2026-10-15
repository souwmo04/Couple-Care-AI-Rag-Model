// Types mirroring backend/app/core/schemas.py and the API routers.

export type LanguageCode = 'auto' | 'en' | 'bn' | 'banglish'
export type DetectedLanguage = 'en' | 'bn' | 'banglish' | 'mixed' | 'unknown'
export type RelationshipStage = 'dating' | 'engaged' | 'married' | 'unspecified'
export type SafetyLevel = 'none' | 'caution' | 'support' | 'urgent' | 'declined'

export interface SourceCard {
  citation_id: string
  document_id: string
  chunk_id: string
  title: string
  organization: string | null
  excerpt: string
  language: string
  topic: string
  url: string | null
  license: string | null
  section: string | null
  synthetic: boolean
  score: number
  cited: boolean
}

export interface SupportResource {
  name: string
  description: string
  contact: string | null
  url: string | null
  region: string
  verified_on: string
  source_url: string
}

export interface SafetyStatus {
  level: SafetyLevel
  message: string | null
  resources: SupportResource[]
}

export interface ChatRequest {
  message: string
  conversation_id: string | null
  language: LanguageCode
  relationship_stage: RelationshipStage
  regenerate?: boolean
}

export interface ChatResponse {
  conversation_id: string
  message_id: string
  answer: string
  detected_language: DetectedLanguage
  response_language: string
  sources: SourceCard[]
  grounded: boolean
  safety: SafetyStatus
  needs_clarification: boolean
  model_id: string | null
  generated: boolean
  /** Cloud mode: the reply came from the local model because the cloud model was rate-limited/unavailable. */
  fallback_reason?: 'rate_limited' | 'unavailable' | null
  duration_ms: number
}

export interface StoredMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  sources: SourceCard[]
  safety: SafetyStatus | null
  language: string | null
  grounded: boolean | null
  generated: boolean | null
}

export interface ConversationSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
  relationship_stage: RelationshipStage
  language: string
}

export interface ConversationDetail extends ConversationSummary {
  messages: StoredMessage[]
}

export interface ConversationList {
  persistence_enabled: boolean
  items: ConversationSummary[]
  total: number
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  version: string
  model_server: 'online' | 'offline'
  /** 'groq' = cloud mode: messages are sent to Groq. */
  provider?: 'local' | 'groq'
  index: 'ready' | 'missing' | 'building' | 'error'
  embeddings: 'ready' | 'loading' | 'unavailable' | 'fallback'
}

export interface ModelStatus {
  configured: boolean
  reachable: boolean
  model_id: string | null
  display_name: string | null
  server_model: string | null
  context_length: number | null
  license: string | null
  revision: string | null
  detail: string | null
  checked_at: string
  provider?: 'local' | 'groq'
}

export interface RuntimeSettings {
  model_id: string
  temperature: number
  max_output_tokens: number
  retrieval_top_k: number
  dense_top_k: number
  bm25_top_k: number
  relevance_threshold: number
  rerank_enabled: boolean
  query_expansion_enabled: boolean
  history_turns: number
  persistence_enabled: boolean
  support_region: 'unspecified' | 'BD' | 'IN' | 'GB' | 'US'
}

export interface SettingsResponse {
  values: RuntimeSettings
  models: { id: string; display_name: string; license: string; context_length: number }[]
  embedding_model: string
  embedding_device: string
  reranker_configured: boolean
  support_regions: Record<string, string>
  limits: Record<string, { min?: number; max?: number }>
  about: { app_version: string; prompt_version: string; knowledge_base_version: string | null }
}

export interface RebuildInfo {
  status: 'idle' | 'running' | 'succeeded' | 'failed'
  started_at: string | null
  finished_at: string | null
  message: string | null
  version: string | null
}

export interface KnowledgeStats {
  available: boolean
  version: string | null
  built_at: string | null
  documents: number
  passages: number
  languages: Record<string, number>
  topics: Record<string, number>
  synthetic_documents: number
  embedding_model: string | null
  embedding_dimension: number | null
  dense_index: boolean
  dense_active: boolean
  embedder_state: string
  embedder_error: string | null
  chunk_size: number | null
  chunk_overlap: number | null
  ingestion_errors: number
  health: 'healthy' | 'lexical_only' | 'dense_unavailable' | 'loading' | 'missing' | 'error'
  rebuild: RebuildInfo
}

export interface SourceSummary {
  document_id: string
  title: string
  organization: string | null
  language: string
  topic: string
  url: string | null
  license: string | null
  permission: string | null
  synthetic: boolean
  passages: number
}

export interface SourcePage {
  items: SourceSummary[]
  total: number
  page: number
  page_size: number
}

export interface SourceDetail extends SourceSummary {
  path: string | null
  sha256: string | null
  sections: { chunk_id: string; section: string | null; text: string; language: string }[]
}

export interface RetrievedPassage {
  rank: number
  chunk_id: string
  document_id: string
  title: string
  text: string
  language: string
  topic: string
  section: string | null
  score: number
  dense_rank: number | null
  bm25_rank: number | null
  above_threshold: boolean
}

export interface RetrievalTestResponse {
  query: string
  normalized_query: string
  expanded_terms: string[]
  detected_language: DetectedLanguage
  mode: string
  passages: RetrievedPassage[]
  duration_ms: number
  dense_available: boolean
}

export interface IngestionErrors {
  version: string | null
  errors: { document_id: string; path?: string; stage: string; error: string }[]
  last_rebuild_failure: string | null
}

export interface ApiErrorBody {
  error: { code: string; message: string; retryable: boolean; details?: { field: string; message: string }[] }
}
