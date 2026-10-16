import { useCallback, useEffect, useState } from 'react'

/** Plain text for speaking: markdown symbols, citation markers and list numbering removed. */
export function speakableText(markdown: string): string {
  return markdown
    .replace(/\[S\d{1,2}\]/g, '')
    .replace(/[*_`#>]+/g, '')
    .replace(/^\s*[-•]\s+/gm, '')
    .replace(/\s+/g, ' ')
    .trim()
}

export function speechSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

/** Prefer a voice that runs on this device; fall back to the browser's online voice only if there is none
 *  (e.g. Bangla in Microsoft Edge). Online voices send the text to the browser vendor's speech service. */
function voiceFor(lang: 'bn' | 'en'): SpeechSynthesisVoice | undefined {
  const matching = window.speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith(lang))
  return matching.find((v) => v.localService) ?? matching[0]
}

/**
 * Read replies aloud with the browser's voices (device voices first). One reply speaks at a time;
 * ``speak`` returns false when the device has no voice for the language (common for Bangla on Windows).
 */
export function useSpeech() {
  const [speakingId, setSpeakingId] = useState<string | null>(null)

  useEffect(() => {
    if (!speechSupported()) return
    window.speechSynthesis.getVoices() // voices load asynchronously in Chromium; ask early
    return () => window.speechSynthesis.cancel()
  }, [])

  const stop = useCallback(() => {
    if (speechSupported()) window.speechSynthesis.cancel()
    setSpeakingId(null)
  }, [])

  const speak = useCallback((id: string, text: string, lang: 'bn' | 'en'): boolean => {
    if (!speechSupported()) return false
    const voice = voiceFor(lang)
    if (!voice) return false
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(speakableText(text))
    utterance.voice = voice
    utterance.lang = voice.lang
    utterance.onend = () => setSpeakingId((current) => (current === id ? null : current))
    utterance.onerror = utterance.onend
    setSpeakingId(id)
    window.speechSynthesis.speak(utterance)
    return true
  }, [])

  return { speakingId, speak, stop }
}
