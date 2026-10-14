export const CITE_RE = /\[(S\d{1,2})\]/g

/** Turn validated "[S1]" markers into links the markdown renderer can show as chips. */
export function linkCitations(text: string, available: Set<string>): string {
  return text.replace(CITE_RE, (match, id: string) => (available.has(id) ? `[${id}](#cite-${id})` : match))
}
