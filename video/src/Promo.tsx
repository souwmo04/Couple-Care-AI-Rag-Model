import { useEffect, useState } from 'react'
import { AbsoluteFill, Audio, cancelRender, continueRender, delayRender, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from 'remotion'
import { Background, clamp, useIn } from './components'
import {
  CoachScene,
  CtaScene,
  HookScene,
  LanguagesScene,
  MeetScene,
  PhoneScene,
  type Scene,
  StagesScene,
  TrustScene,
  VoiceScene,
  WhyScene,
} from './scenes'
import { C, CAPTION_TOP, F, STAGE } from './theme'
import timeline from './timeline.json'

export const LINK = 'souwmo04.github.io/Couple-Care-AI-Rag-Model'
const scenes = timeline.scenes as Scene[]
const WIPE_COLORS = [C.tomato, C.yellow, C.lilac, C.mint, C.sky, C.heartPink, C.yellow, C.tomato, C.lilac]

function useFonts() {
  const [handle] = useState(() => delayRender('Loading fonts'))
  useEffect(() => {
    Promise.all([
      document.fonts.load('900 100px "Archivo Variable"'),
      document.fonts.load('500 40px "Archivo Variable"'),
      document.fonts.load('700 40px "Noto Sans Bengali Variable"', 'আমি'),
      document.fonts.load('700 30px "JetBrains Mono Variable"'),
    ])
      .then(() => document.fonts.ready)
      .then(() => continueRender(handle))
      .catch((err) => cancelRender(err))
  }, [handle])
}

/** Diagonal colour band that sweeps across each cut. */
function Wipe({ at, color }: { at: number; color: string }) {
  const frame = useCurrentFrame()
  const { width } = useVideoConfig()
  if (frame < at - 10 || frame > at + 10) return null
  const x = interpolate(frame, [at - 10, at + 10], [-1.6 * width, 1.2 * width], { ...clamp, easing: (t) => t * t * (3 - 2 * t) })
  return (
    <AbsoluteFill style={{ pointerEvents: 'none', overflow: 'hidden' }}>
      <div
        style={{
          position: 'absolute',
          top: '-20%',
          bottom: '-20%',
          left: x,
          width: 1.45 * width,
          background: color,
          borderLeft: `14px solid ${C.ink}`,
          borderRight: `14px solid ${C.ink}`,
          transform: 'skewX(-14deg)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: '-20%',
          bottom: '-20%',
          left: x - 120,
          width: 70,
          background: C.ink,
          transform: 'skewX(-14deg)',
        }}
      />
    </AbsoluteFill>
  )
}

/** Karaoke captions: a few words at a time, the spoken word highlighted. */
function Captions({ s, dark }: { s: Scene; dark: boolean }) {
  const frame = useCurrentFrame()
  const chunks: (typeof s.words)[] = []
  for (const w of s.words) {
    const last = chunks[chunks.length - 1]
    const prev = last?.[last.length - 1]
    if (!last || last.length >= 4 || w.from - prev!.to > 9) chunks.push([w])
    else last.push(w)
  }
  const idx = chunks.findIndex((c, i) => frame >= c[0].from - 2 && (i === chunks.length - 1 ? frame <= c[c.length - 1].to + 14 : frame < chunks[i + 1][0].from - 2))
  if (idx < 0) return null
  const chunk = chunks[idx]
  const enter = interpolate(frame, [chunk[0].from - 2, chunk[0].from + 4], [0, 1], clamp)
  return (
    <div style={{ position: 'absolute', left: 40, right: 40, top: CAPTION_TOP, display: 'flex', justifyContent: 'center' }}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: '6px 14px',
          padding: '16px 26px',
          background: dark ? C.paperLight : C.ink,
          border: `4px solid ${C.ink}`,
          borderRadius: 18,
          boxShadow: `6px 6px 0 0 ${dark ? C.tomato : C.tomato}`,
          transform: `translateY(${(1 - enter) * 30}px) scale(${0.94 + 0.06 * enter})`,
          opacity: enter,
        }}
      >
        {chunk.map((w, i) => {
          const on = frame >= w.from - 1 && frame <= w.to + 3
          const said = frame > w.to + 3
          return (
            <span
              key={i}
              style={{
                fontFamily: F.body,
                fontWeight: 900,
                fontSize: 50,
                fontStretch: '105%',
                lineHeight: 1.15,
                padding: '0 8px',
                borderRadius: 8,
                background: on ? C.yellow : 'transparent',
                color: on ? C.ink : dark ? C.ink : C.paperLight,
                opacity: on || said ? 1 : 0.6,
                transform: `scale(${on ? 1.08 : 1})`,
                display: 'inline-block',
              }}
            >
              {w.text.toUpperCase()}
            </span>
          )
        })}
      </div>
    </div>
  )
}

function Disclaimer({ from }: { from: number }) {
  const p = useIn(from, { damping: 16 })
  return (
    <div
      style={{
        position: 'absolute',
        left: 40,
        right: 40,
        top: CAPTION_TOP + 70,
        textAlign: 'center',
        fontFamily: F.body,
        fontSize: 27,
        fontWeight: 600,
        color: C.muted,
        opacity: p,
      }}
    >
      Educational support, not therapy or a crisis service.
    </div>
  )
}

function SceneBody({ s }: { s: Scene }) {
  switch (s.id) {
    case 'hook':
      return <HookScene s={s} />
    case 'why':
      return <WhyScene s={s} />
    case 'meet':
      return <MeetScene s={s} />
    case 'languages':
      return <LanguagesScene s={s} />
    case 'stages':
      return <StagesScene s={s} />
    case 'coach':
      return <CoachScene s={s} />
    case 'voice':
      return <VoiceScene s={s} startSec={s.from / timeline.fps} />
    case 'trust':
      return <TrustScene s={s} />
    case 'phone':
      return <PhoneScene s={s} />
    case 'cta':
      return <CtaScene s={s} link={LINK} />
    default:
      return null
  }
}

export function Promo() {
  useFonts()
  const { height } = useVideoConfig()
  const top = (height - STAGE.height) / 2
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      {scenes.map((s, i) => {
        const dark = s.id === 'hook'
        const last = s.words[s.words.length - 1]
        return (
          <Sequence key={s.id} from={s.from} durationInFrames={s.durationInFrames} name={s.id}>
            <Background dark={dark} seed={i * 7 + 3} hearts={dark ? 10 : 14} />
            <div style={{ position: 'absolute', left: 0, top, width: STAGE.width, height: STAGE.height }}>
              <SceneBody s={s} />
              <Captions s={s} dark={dark} />
              {s.id === 'cta' && last ? <Disclaimer from={last.to + 16} /> : null}
            </div>
          </Sequence>
        )
      })}
      {scenes.slice(1).map((s, i) => (
        <Wipe key={s.id} at={s.from} color={WIPE_COLORS[i % WIPE_COLORS.length]} />
      ))}
      <Audio src={staticFile('soundtrack.wav')} />
    </AbsoluteFill>
  )
}
