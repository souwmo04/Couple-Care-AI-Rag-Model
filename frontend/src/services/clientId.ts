/**
 * A random identifier for this browser profile. The backend binds conversations to it so
 * one browser cannot read another's conversations by guessing an id.
 *
 * Guest mode keeps the id in sessionStorage (forgotten when the tab closes); otherwise it
 * lives in localStorage. Storage can be unavailable (private windows, blocked site data),
 * so every access is guarded and falls back to an in-memory id.
 */

const KEY = 'couplecare.clientId'
let memoryId: string | null = null

function randomId(): string {
  const c: Crypto = globalThis.crypto
  if (typeof c.randomUUID === 'function') return c.randomUUID()
  const bytes = new Uint8Array(16)
  c.getRandomValues(bytes)
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

function isGuest(): boolean {
  try {
    return localStorage.getItem('couplecare.guest') === '1' || sessionStorage.getItem('couplecare.guest') === '1'
  } catch {
    return true
  }
}

export function getClientId(): string {
  const storage = (() => {
    try {
      return isGuest() ? sessionStorage : localStorage
    } catch {
      return null
    }
  })()
  try {
    const existing = storage?.getItem(KEY)
    if (existing && /^[A-Za-z0-9-]{16,64}$/.test(existing)) return existing
    const id = randomId()
    storage?.setItem(KEY, id)
    return id
  } catch {
    memoryId ??= randomId()
    return memoryId
  }
}

export function resetClientId(): void {
  memoryId = null
  try {
    localStorage.removeItem(KEY)
    sessionStorage.removeItem(KEY)
  } catch {
    /* storage unavailable */
  }
}
