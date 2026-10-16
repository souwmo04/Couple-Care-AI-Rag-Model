import { useCallback, useEffect, useRef, useState } from 'react'

export type RecorderState = 'idle' | 'recording' | 'transcribing'
export const MAX_RECORDING_SECONDS = 60

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === 'undefined') return undefined
  return ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'].find((t) =>
    MediaRecorder.isTypeSupported(t),
  )
}

export function voiceRecordingSupported(): boolean {
  return typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined'
}

/**
 * Record from the microphone (MediaRecorder), stop automatically after MAX_RECORDING_SECONDS, and hand the
 * audio to ``onAudio``. The microphone is released as soon as recording stops.
 */
export function useVoiceRecorder(onAudio: (audio: Blob) => Promise<void>, onError: (kind: 'denied' | 'failed') => void) {
  const [state, setState] = useState<RecorderState>('idle')
  const [seconds, setSeconds] = useState(0)
  const recorder = useRef<MediaRecorder | null>(null)
  const timer = useRef<number | null>(null)

  const clearTimer = () => {
    if (timer.current !== null) window.clearInterval(timer.current)
    timer.current = null
  }

  const stop = useCallback(() => {
    clearTimer()
    if (recorder.current && recorder.current.state !== 'inactive') recorder.current.stop()
  }, [])

  const start = useCallback(async () => {
    if (state !== 'idle') return
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      onError('denied')
      return
    }
    const chunks: Blob[] = []
    const mimeType = pickMimeType()
    const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    recorder.current = rec
    rec.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data)
    }
    rec.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop())
      recorder.current = null
      const audio = new Blob(chunks, { type: rec.mimeType || mimeType || 'audio/webm' })
      if (audio.size === 0) {
        setState('idle')
        return
      }
      setState('transcribing')
      try {
        await onAudio(audio)
      } catch {
        onError('failed')
      } finally {
        setState('idle')
      }
    }
    rec.start()
    setSeconds(0)
    setState('recording')
    timer.current = window.setInterval(() => {
      setSeconds((s) => {
        if (s + 1 >= MAX_RECORDING_SECONDS) stop()
        return s + 1
      })
    }, 1000)
  }, [state, onAudio, onError, stop])

  // Release the microphone if the component unmounts mid-recording.
  useEffect(() => () => stop(), [stop])

  return { state, seconds, start, stop }
}
