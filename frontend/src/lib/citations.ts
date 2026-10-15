export const CITE_RE = /\[(S\d{1,2})\]/g

/** Turn validated "[S1]" markers into links the markdown renderer can show as chips. */
export function linkCitations(text: string, available: Set<string>): string {
  return text.replace(CITE_RE, (match, id: string) => (available.has(id) ? `[${id}](#cite-${id})` : match))
}

/**
 * Reply text as shown in the chat: citation markers are removed (sources are listed in the side panel,
 * or under "See where this comes from" on small screens). Tidies the spacing and empty brackets left behind.
 */
export function stripCitations(text: string): string {
  return text
    .replace(/[ \t]*\[S\d{1,2}\]/g, '')
    .replace(/[ \t]*\([ \t]*\)/g, '')
    .replace(/[ \t]+([.,;:!?।])/g, '$1')
    .replace(/([^\s]) {2,}/g, '$1 ')
}
