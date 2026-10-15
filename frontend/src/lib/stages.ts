import type { RelationshipStage } from '@/types/api'

/** Display order of relationship stages (shared by the welcome screen, context panel and settings). */
export const RELATIONSHIP_STAGES: readonly RelationshipStage[] = [
  'unspecified',
  'single',
  'one_sided',
  'situationship',
  'dating',
  'long_distance',
  'engaged',
  'married',
]
