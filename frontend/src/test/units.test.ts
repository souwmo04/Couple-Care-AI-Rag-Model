import { linkCitations } from '@/lib/citations'
import { DEFAULT_PREFERENCES, loadPreferences } from '@/hooks/usePreferences'
import { bn } from '@/i18n/bn'
import { en } from '@/i18n/en'
import { parseSseChunk } from '@/services/api'
import { getClientId } from '@/services/clientId'

describe('parseSseChunk', () => {
  it('parses complete frames and keeps the remainder', () => {
    const buffer = 'event: meta\ndata: {"event":"delta","text":"Hi"}\n\ndata: {"event":"del'
    const { events, rest } = parseSseChunk(buffer)
    expect(events).toEqual([{ event: 'delta', text: 'Hi' }])
    expect(rest).toBe('data: {"event":"del')
  })

  it('ignores malformed frames', () => {
    const { events } = parseSseChunk('data: {not json}\n\ndata: {"event":"delta","text":"ok"}\n\n')
    expect(events).toEqual([{ event: 'delta', text: 'ok' }])
  })
})

describe('linkCitations', () => {
  it('links only citations that were actually retrieved', () => {
    const out = linkCitations('Take a break [S1]. Fake [S4].', new Set(['S1']))
    expect(out).toBe('Take a break [S1](#cite-S1). Fake [S4].')
  })
})

describe('preferences', () => {
  it('sanitises tampered storage values back to safe defaults', () => {
    localStorage.setItem('couplecare.prefs', JSON.stringify({ theme: 'neon', fontScale: 9, responseLanguage: 'fr' }))
    const prefs = loadPreferences()
    expect(prefs.theme).toBe(DEFAULT_PREFERENCES.theme)
    expect(prefs.fontScale).toBe(1)
    expect(prefs.responseLanguage).toBe('auto')
  })

  it('reads from session storage in guest mode', () => {
    localStorage.setItem('couplecare.guest', '1')
    sessionStorage.setItem('couplecare.prefs', JSON.stringify({ theme: 'dark' }))
    expect(loadPreferences()).toMatchObject({ guestMode: true, theme: 'dark' })
    sessionStorage.clear()
  })

  it('survives corrupt JSON', () => {
    localStorage.setItem('couplecare.prefs', '{oops')
    expect(loadPreferences().theme).toBe('light') // corrupt storage falls back to the default (light)
  })
})

describe('client id', () => {
  it('is stable and matches the backend format', () => {
    const a = getClientId()
    expect(a).toMatch(/^[A-Za-z0-9-]{16,64}$/)
    expect(getClientId()).toBe(a)
  })

  it('is kept out of local storage in guest mode', () => {
    localStorage.setItem('couplecare.guest', '1')
    getClientId()
    expect(localStorage.getItem('couplecare.clientId')).toBeNull()
    expect(sessionStorage.getItem('couplecare.clientId')).not.toBeNull()
    sessionStorage.clear()
  })
})

describe('copy', () => {
  function shape(value: unknown): unknown {
    if (Array.isArray(value)) return value.length ? [shape(value[0])] : []
    if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((k) => [k, shape((value as Record<string, unknown>)[k])]))
    return typeof value
  }

  it('Bangla copy has the same structure as English', () => {
    expect(shape(bn)).toEqual(shape(en))
  })

  it('contains no hard-coded phone numbers', () => {
    const text = JSON.stringify([en, bn])
    expect(text).not.toMatch(/\b\d{3}[-\s]?\d{3,}\b/)
  })
})

describe('stripCitations', () => {
  it('removes markers and tidies the text left behind', async () => {
    const { stripCitations } = await import('@/lib/citations')
    expect(stripCitations('Talk calmly [S1]. Take a break ([S2]) today [S3], then talk.')).toBe(
      'Talk calmly. Take a break today, then talk.',
    )
    expect(stripCitations('দোষারোপ নেই [S1]।')).toBe('দোষারোপ নেই।')
  })
})
