import { Loader2, Mic, Square } from 'lucide-react'
import { useCallback } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Tooltip } from '@/components/ui/primitives'
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder'
import { useCopy } from '@/i18n'
import { cn } from '@/lib/utils'
import { ApiError, api } from '@/services/api'

/** Record a voice message and put the transcription into the composer (the user reviews it before sending). */
export function MicButton({ language, onText }: { language: 'auto' | 'en' | 'bn'; onText: (text: string) => void }) {
  const t = useCopy()
  const handleAudio = useCallback(
    async (audio: Blob) => {
      try {
        const text = await api.transcribe(audio, language)
        if (text) onText(text)
      } catch (err) {
        toast.error(err instanceof ApiError && err.code === 'voice_unavailable' ? t.chat.voiceNeedsCloud : t.chat.voiceFailed)
      }
    },
    [language, onText, t.chat.voiceFailed, t.chat.voiceNeedsCloud],
  )
  const handleError = useCallback(
    (kind: 'denied' | 'failed') => toast.error(kind === 'denied' ? t.chat.voiceDenied : t.chat.voiceFailed),
    [t.chat.voiceDenied, t.chat.voiceFailed],
  )
  const { state, seconds, start, stop } = useVoiceRecorder(handleAudio, handleError)

  const recording = state === 'recording'
  const busy = state === 'transcribing'
  const label = recording ? t.chat.voiceStop : busy ? t.chat.voiceTranscribing : t.chat.voiceRecord
  return (
    <div className="flex items-center gap-1.5">
      {recording && (
        <span className="flex items-center gap-1.5 font-mono text-xs font-bold tabular-nums text-danger" aria-live="polite">
          <span className="size-2 animate-pulse rounded-full bg-danger" aria-hidden />
          0:{String(seconds).padStart(2, '0')}
        </span>
      )}
      {busy && <span className="text-xs text-muted-foreground">{t.chat.voiceTranscribing}</span>}
      <Tooltip content={label}>
        <Button
          type="button"
          size="icon"
          variant={recording ? 'danger' : 'secondary'}
          aria-label={label}
          aria-pressed={recording}
          disabled={busy}
          onClick={() => (recording ? stop() : void start())}
          className={cn(recording && 'animate-pulse')}
        >
          {busy ? <Loader2 className="animate-spin" /> : recording ? <Square className="fill-current" /> : <Mic />}
        </Button>
      </Tooltip>
    </div>
  )
}
