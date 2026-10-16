import {
  ArrowRight,
  BookOpen,
  Building2,
  Check,
  Download,
  Languages,
  MessageCircleHeart,
  Mic,
  ShieldCheck,
  Smartphone,
  Sparkles,
  UserX,
  Users,
  Volume2,
  Zap,
} from 'lucide-react'
import type { CSSProperties, ReactNode } from 'react'
import { AbsoluteFill, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion'
import { useAudioData, visualizeAudio } from '@remotion/media-utils'
import {
  AppBar,
  Bubble,
  Card,
  Chip,
  clamp,
  HeartShape,
  Kicker,
  Logo,
  Phone,
  seeded,
  Stamp,
  StaggerWords,
  StretchTitle,
  Typed,
  useIn,
} from './components'
import { BORDER, C, F, shadow } from './theme'

export interface Word {
  text: string
  from: number
  to: number
}
export interface Scene {
  id: string
  text: string
  from: number
  durationInFrames: number
  voFrom: number
  words: Word[]
  chips?: number[]
}

/** Frame (within the scene) at which the narrator starts saying `word`. */
function at(s: Scene, word: string, fallback = 0, nth = 0): number {
  const hits = s.words.filter((w) => w.text.toLowerCase().replace(/[^a-z-']/g, '') === word.toLowerCase())
  return hits[nth]?.from ?? fallback
}

const abs = (style: CSSProperties): CSSProperties => ({ position: 'absolute', ...style })

function IconTile({ children, bg, size = 120 }: { children: ReactNode; bg: string; size?: number }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        flexShrink: 0,
        display: 'grid',
        placeItems: 'center',
        background: bg,
        border: BORDER,
        borderRadius: 18,
        boxShadow: shadow(5),
      }}
    >
      {children}
    </div>
  )
}

// =========================================================================================== 1. hook
export function HookScene({ s }: { s: Scene }) {
  const frame = useCurrentFrame()
  const messages = [
    { text: 'We fought again.', meta: 'Seen 11:42 PM', x: 360, y: 90, r: 3, d: 4 },
    { text: 'Should I text first?', meta: 'Typing… deleted', x: 70, y: 260, r: -4, d: 16 },
    { text: 'আমি কি ভুল করেছি?', meta: 'Not sent', x: 330, y: 430, r: 2, d: 28, bn: true },
  ]
  const heartIn = useIn(at(s, 'love', 70) - 4, { damping: 10, stiffness: 160 })
  const crack = interpolate(frame, [at(s, 'and', 87), at(s, 'and', 87) + 14], [0, 1], clamp)
  const titleAt = at(s, 'no', 100) - 3
  const dim = interpolate(frame, [titleAt - 6, titleAt + 8], [1, 0.28], clamp)
  return (
    <AbsoluteFill>
      {messages.map((m, i) => {
        const p = useIn(m.d, { damping: 13, stiffness: 150 })
        return (
          <div
            key={i}
            style={abs({
              left: m.x,
              top: m.y + (1 - p) * 120,
              opacity: Math.min(1, p * 1.5) * dim,
              transform: `rotate(${m.r}deg) scale(${0.8 + 0.2 * p})`,
            })}
          >
            <div
              style={{
                background: C.paperLight,
                color: C.ink,
                border: `4px solid ${C.paperLight}`,
                borderRadius: '30px 30px 8px 30px',
                padding: '22px 34px',
                fontFamily: m.bn ? F.bangla : F.body,
                fontWeight: 700,
                fontSize: 50,
                boxShadow: `10px 10px 0 0 ${C.tomato}`,
              }}
            >
              {m.text}
            </div>
            <div style={{ marginTop: 14, fontFamily: F.mono, fontSize: 24, color: 'rgba(255,255,255,0.55)', textAlign: 'right' }}>
              {m.meta}
            </div>
          </div>
        )
      })}
      {/* A heart that cracks in two. */}
      <div
        style={abs({
          left: 540 - 130,
          top: 600,
          width: 260,
          height: 260,
          transform: `scale(${heartIn})`,
          opacity: dim < 1 ? 0.55 + 0.45 * dim : 1,
        })}
      >
        {[0, 1].map((half) => (
          <div
            key={half}
            style={abs({
              inset: 0,
              clipPath: half === 0 ? 'polygon(0 0, 52% 0, 44% 35%, 56% 55%, 46% 100%, 0 100%)' : 'polygon(52% 0, 100% 0, 100% 100%, 46% 100%, 56% 55%, 44% 35%)',
              transform: `translateX(${(half ? 1 : -1) * crack * 34}px) rotate(${(half ? 1 : -1) * crack * 12}deg)`,
            })}
          >
            <HeartShape size={260} fill={C.heartRed} stroke={C.paperLight} strokeWidth={1} />
          </div>
        ))}
      </div>
      <div style={abs({ left: 0, right: 0, top: 800 })}>
        <StretchTitle text="NO ONE" delay={titleAt} size={150} color={C.paperLight} />
        <StretchTitle text="TO TALK TO?" delay={titleAt + 8} size={118} color={C.yellow} style={{ marginTop: 10 }} />
      </div>
    </AbsoluteFill>
  )
}

// =========================================================================================== 2. why
export function WhyScene({ s }: { s: Scene }) {
  const cards = [
    {
      icon: <Building2 size={68} strokeWidth={2.4} />,
      bg: C.sky,
      title: 'Counselling',
      sub: 'Far away, costly, awkward to ask.',
      stamp: 'Out of reach',
      d: at(s, 'counselling', 16) - 6,
      st: at(s, 'away', 58) + 4,
    },
    {
      icon: <Users size={68} strokeWidth={2.4} />,
      bg: C.mint,
      title: 'Friends',
      sub: 'They mean well, but take sides.',
      stamp: 'Biased',
      d: at(s, 'friends', 87) - 6,
      st: at(s, 'sides', 104) + 4,
    },
    {
      icon: <MessageCircleHeart size={68} strokeWidth={2.4} />,
      bg: C.lilac,
      title: 'Your own words',
      sub: 'Everything you type sounds wrong.',
      stamp: 'Stuck',
      d: at(s, 'right', 142) - 8,
      st: at(s, 'come', 176) + 2,
    },
  ]
  return (
    <AbsoluteFill>
      <div style={abs({ left: 0, right: 0, top: 60, display: 'flex', justifyContent: 'center' })}>
        <Kicker style={{ transform: `scale(${useIn(0)})` }}>Why it's so hard</Kicker>
      </div>
      {cards.map((c, i) => {
        const p = useIn(c.d, { damping: 13 })
        return (
          <div
            key={i}
            style={abs({
              left: 90,
              top: 190 + i * 300,
              width: 900,
              transform: `translateX(${(1 - p) * (i % 2 ? 1200 : -1200)}px) rotate(${(i % 2 ? 1 : -1) * 1.5}deg)`,
            })}
          >
            <Card style={{ display: 'flex', alignItems: 'center', gap: 34, padding: 34 }}>
              <IconTile bg={c.bg}>{c.icon}</IconTile>
              <div>
                <div style={{ fontFamily: F.display, fontWeight: 900, fontSize: 56, fontStretch: '105%', lineHeight: 1.05 }}>{c.title}</div>
                <div style={{ fontFamily: F.body, fontSize: 32, color: C.muted, marginTop: 8 }}>{c.sub}</div>
              </div>
              <Stamp delay={c.st} style={{ right: -24, top: -30 }} rotate={i % 2 ? 9 : -9}>
                {c.stamp}
              </Stamp>
            </Card>
          </div>
        )
      })}
    </AbsoluteFill>
  )
}

// =========================================================================================== 3. meet
export function MeetScene({ s }: { s: Scene }) {
  const frame = useCurrentFrame()
  const flash = interpolate(frame, [0, 8], [0.9, 0], clamp)
  const logo = useIn(2, { damping: 9, stiffness: 120, mass: 0.9 })
  const beat = 1 + 0.12 * Math.max(0, Math.sin((frame / 30) * Math.PI * 2 * 1.2)) * interpolate(frame, [10, 40], [0, 1], clamp)
  const rand = seeded(19)
  const burst = Array.from({ length: 14 }, (_, i) => ({
    angle: (i / 14) * Math.PI * 2 + rand() * 0.3,
    dist: 260 + rand() * 260,
    size: 30 + rand() * 40,
    fill: i % 2 ? C.heartPink : C.heartRed,
  }))
  const bp = interpolate(frame, [4, 50], [0, 1], { ...clamp, easing: (t) => 1 - (1 - t) ** 3 })
  const ai = useIn(at(s, 'ai', 49) - 2, { damping: 8, stiffness: 220 })
  const lines = at(s, 'understand', 104) - 6
  return (
    <AbsoluteFill>
      {burst.map((b, i) => (
        <div
          key={i}
          style={abs({
            left: 540 + Math.cos(b.angle) * b.dist * bp - b.size / 2,
            top: 250 + Math.sin(b.angle) * b.dist * bp - b.size / 2,
            opacity: 1 - bp * 0.75,
            transform: `rotate(${b.angle * 40}deg) scale(${0.4 + bp})`,
          })}
        >
          <HeartShape size={b.size} fill={b.fill} />
        </div>
      ))}
      <div style={abs({ left: 540 - 140, top: 100, transform: `scale(${logo}) rotate(${(1 - logo) * -30}deg)` })}>
        <div style={{ borderRadius: 40, boxShadow: shadow(12) }}>
          <Logo size={280} heartScale={beat} />
        </div>
      </div>
      <div style={abs({ left: 0, right: 0, top: 440, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 22 })}>
        <StretchTitle text="COUPLECARE" delay={at(s, 'couplecare', 31) - 4} size={88} />
        <div
          style={{
            background: C.tomato,
            border: BORDER,
            borderRadius: 14,
            boxShadow: shadow(6),
            padding: '2px 16px',
            fontFamily: F.display,
            fontWeight: 900,
            fontSize: 74,
            transform: `scale(${ai}) rotate(${(1 - ai) * 40 - 4}deg)`,
          }}
        >
          AI
        </div>
      </div>
      <div style={abs({ left: 0, right: 0, top: 600, display: 'flex', justifyContent: 'center' })}>
        <Kicker style={{ transform: `scale(${useIn(at(s, 'calm', 80) - 4)})` }}>A calm place to talk</Kicker>
      </div>
      <div style={abs({ left: 0, right: 0, top: 720, textAlign: 'center' })}>
        <StaggerWords text="UNDERSTAND" delay={lines} style={{ fontFamily: F.display, fontWeight: 900, fontSize: 104, fontStretch: '112%' }} />
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 10 }}>
          <div
            style={{
              background: C.tomato,
              border: BORDER,
              boxShadow: shadow(8),
              padding: '0 26px',
              transform: `rotate(-2deg) scaleX(${useIn(lines + 14, { damping: 12 })})`,
            }}
          >
            <StaggerWords
              text="EACH OTHER"
              delay={lines + 16}
              style={{ fontFamily: F.display, fontWeight: 900, fontSize: 104, fontStretch: '125%', letterSpacing: '0.08em' }}
            />
          </div>
        </div>
        <StaggerWords
          text="BETTER."
          delay={at(s, 'better', 132) - 4}
          style={{ fontFamily: F.display, fontWeight: 900, fontSize: 104, fontStretch: '112%', marginTop: 10 }}
        />
      </div>
      <AbsoluteFill style={{ background: C.white, opacity: flash }} />
    </AbsoluteFill>
  )
}

// =========================================================================================== 4. languages
export function LanguagesScene({ s }: { s: Scene }) {
  const frame = useCurrentFrame()
  const en = at(s, 'english', 75)
  const bn = at(s, 'bangla', 94)
  const bl = at(s, 'banglish', 119)
  const langs = [
    { label: 'ENGLISH', t: en, bg: C.sky },
    { label: 'বাংলা', t: bn, bg: C.mint, bn: true },
    { label: 'BANGLISH', t: bl, bg: C.yellow },
  ]
  const msgs = [
    { side: 'user' as const, text: 'We keep fighting over small things.', t: en - 4 },
    { side: 'ai' as const, text: 'That sounds tiring. Small fights often carry bigger feelings.', t: en + 12 },
    { side: 'user' as const, text: 'ও আমাকে একদম সময় দেয় না।', t: bn - 2, lang: 'bn' },
    { side: 'ai' as const, text: 'অবহেলিত লাগাটা খুব কষ্টের। চলুন বুঝি কী হচ্ছে।', t: bn + 14, lang: 'bn' },
    { side: 'user' as const, text: 'Ami ki age text korbo?', t: bl - 2 },
    { side: 'ai' as const, text: 'Korte paro! Chhoto, shohoj ekta message diye shuru koro.', t: bl + 16 },
  ]
  const scroll = interpolate(frame, [bl + 10, bl + 34], [0, 150], clamp)
  const phone = useIn(0, { damping: 15, stiffness: 110 })
  const sticker = useIn(at(s, 'replies', 154) - 4, { damping: 8, stiffness: 200 })
  return (
    <AbsoluteFill>
      <div style={abs({ left: 0, right: 0, top: 26 })}>
        <StaggerWords
          text="TALK THE WAY YOU TALK"
          delay={at(s, 'talk', 17) - 4}
          every={3}
          style={{ fontFamily: F.display, fontWeight: 900, fontSize: 70, fontStretch: '110%' }}
        />
      </div>
      <div style={abs({ left: 0, right: 0, top: 140, display: 'flex', justifyContent: 'center', gap: 22 })}>
        {langs.map((l, i) => {
          const on = useIn(l.t - 2, { damping: 9, stiffness: 220 })
          return (
            <Chip
              key={i}
              bg={on > 0.5 ? l.bg : C.paperLight}
              size={40}
              style={{
                transform: `scale(${1 + 0.18 * Math.sin(Math.min(1, on) * Math.PI)}) rotate(${(i - 1) * 3}deg)`,
                fontFamily: l.bn ? F.bangla : F.display,
                fontStretch: '110%',
                opacity: 0.45 + 0.55 * Math.min(1, on),
              }}
            >
              {on > 0.5 ? <Check size={34} strokeWidth={3.5} /> : <Languages size={34} strokeWidth={2.5} />}
              {l.label}
            </Chip>
          )
        })}
      </div>
      <div style={abs({ left: 540 - 320, top: 270, transform: `translateY(${(1 - phone) * 900}px)` })}>
        <Phone width={640} height={840}>
          <AppBar />
          <div style={{ position: 'absolute', top: 130, left: 0, right: 0, bottom: 0, overflow: 'hidden' }}>
          <div style={{ padding: '24px 22px', display: 'flex', flexDirection: 'column', gap: 18, transform: `translateY(${-scroll}px)` }}>
            {msgs.map((m, i) => {
              const p = useIn(m.t, { damping: 14, stiffness: 170 })
              return (
                <div key={i} style={{ opacity: Math.min(1, p * 1.5), transform: `translateY(${(1 - p) * 40}px) scale(${0.9 + 0.1 * p})` }}>
                  <Bubble side={m.side} lang={m.lang}>
                    {m.text}
                  </Bubble>
                </div>
              )
            })}
          </div>
          </div>
        </Phone>
      </div>
      <div
        style={abs({
          right: 30,
          top: 960,
          transform: `scale(${sticker}) rotate(${-6 + (1 - sticker) * 30}deg)`,
        })}
      >
        <div
          style={{
            background: C.tomato,
            border: BORDER,
            borderRadius: 20,
            boxShadow: shadow(7),
            padding: '16px 22px',
            fontFamily: F.display,
            fontWeight: 900,
            fontSize: 34,
            lineHeight: 1.05,
            textAlign: 'center',
          }}
        >
          REPLIES IN
          <br />
          YOUR LANGUAGE
        </div>
      </div>
    </AbsoluteFill>
  )
}

// =========================================================================================== 5. stages
export function StagesScene({ s }: { s: Scene }) {
  const frame = useCurrentFrame()
  const times = s.chips ?? [17, 39, 70, 84, 102, 117, 132]
  const chips = [
    { label: 'Single', bg: C.sky },
    { label: 'One-sided love', bg: C.heartPink },
    { label: 'Situationship', bg: C.lilac },
    { label: 'Dating', bg: C.yellow },
    { label: 'Long-distance', bg: C.mint },
    { label: 'Engaged', bg: C.tomatoLight },
    { label: 'Married', bg: C.paperLight },
  ]
  // Positions of a loose, hand-placed cloud.
  const pos = [
    { x: 100, y: 240, r: -6 },
    { x: 470, y: 225, r: 4 },
    { x: 50, y: 420, r: 3 },
    { x: 620, y: 410, r: -5 },
    { x: 70, y: 600, r: -3 },
    { x: 610, y: 590, r: 6 },
    { x: 340, y: 770, r: -2 },
  ]
  const adapt = at(s, 'adapts', 164)
  const pick = Math.min(6, Math.max(0, Math.floor(interpolate(frame, [adapt - 10, adapt + 20], [0, 6.99], clamp))))
  return (
    <AbsoluteFill>
      <div style={abs({ left: 0, right: 0, top: 70, display: 'flex', justifyContent: 'center' })}>
        <Kicker bg={C.lilac} style={{ transform: `scale(${useIn(0)})` }}>
          Where are you right now?
        </Kicker>
      </div>
      {chips.map((c, i) => {
        const p = useIn(times[i] - 3, { damping: 9, stiffness: 180, mass: 0.7 })
        const picked = frame >= adapt - 10 && pick === i
        return (
          <div
            key={i}
            style={abs({
              left: pos[i].x,
              top: pos[i].y - (1 - p) * 700,
              opacity: p > 0.02 ? 1 : 0,
              transform: `rotate(${pos[i].r + (1 - p) * 40}deg) scale(${picked ? 1.12 : 1})`,
            })}
          >
            <Chip bg={c.bg} size={50} style={{ boxShadow: picked ? `10px 10px 0 0 ${C.tomato}` : shadow(6) }}>
              {picked ? <Check size={44} strokeWidth={3.5} /> : <HeartShape size={40} fill={C.heartRed} />}
              {c.label}
            </Chip>
          </div>
        )
      })}
      <div style={abs({ left: 40, right: 40, top: 930 })}>
        <StaggerWords
          text="IT MEETS YOU WHERE YOU ARE"
          delay={adapt - 4}
          every={3}
          style={{ fontFamily: F.display, fontWeight: 900, fontSize: 78, fontStretch: '108%', lineHeight: 1.05 }}
          wordStyle={(i) => (i >= 3 ? { color: C.tomato } : {})}
        />
      </div>
    </AbsoluteFill>
  )
}

// =========================================================================================== 6. coach
export function CoachScene({ s }: { s: Scene }) {
  const frame = useCurrentFrame()
  const flip = useIn(at(s, 'coach', 60) - 2, { damping: 12, stiffness: 200 })
  const card = useIn(at(s, 'and', 86) - 6, { damping: 14 })
  const say = at(s, 'exactly', 98)
  const doNext = at(s, 'what', 150, 1)
  const sparkles = interpolate(frame, [at(s, 'coach', 60), at(s, 'coach', 60) + 24], [0, 1], clamp)
  return (
    <AbsoluteFill>
      <div style={abs({ left: 0, right: 0, top: 40 })}>
        <StretchTitle text="NEED IT" delay={at(s, 'need', 15) - 4} size={96} />
        <StretchTitle text="STRAIGHT?" delay={at(s, 'straight', 22) - 2} size={96} color={C.tomato} style={{ marginTop: 6 }} />
      </div>
      <div style={abs({ left: 140, top: 290, width: 800, transform: `scale(${useIn(at(s, 'turn', 49) - 8)})` })}>
        <Card style={{ display: 'flex', alignItems: 'center', gap: 30, padding: '26px 34px' }}>
          <Zap size={60} strokeWidth={2.6} fill={flip > 0.5 ? C.yellow : 'none'} />
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: F.display, fontWeight: 900, fontSize: 52, fontStretch: '110%' }}>COACH MODE</div>
            <div style={{ fontFamily: F.body, fontSize: 28, color: C.muted }}>Straight answers: what to say or do next</div>
          </div>
          {/* Switch */}
          <div
            style={{
              position: 'relative',
              width: 150,
              height: 82,
              borderRadius: 999,
              border: BORDER,
              background: interpolate(flip, [0, 1], [0, 1]) > 0.5 ? C.tomato : C.paperDark,
              boxShadow: shadow(4),
            }}
          >
            <div
              style={{
                position: 'absolute',
                top: 7,
                left: 8 + flip * 66,
                width: 60,
                height: 60,
                borderRadius: 999,
                background: C.white,
                border: BORDER,
              }}
            />
          </div>
          {[0, 1, 2, 3, 4].map((k) => (
            <div
              key={k}
              style={abs({
                right: 100 - Math.cos(k * 1.25) * 120 * sparkles,
                top: 40 - Math.sin(k * 1.25) * 110 * sparkles,
                opacity: 1 - sparkles,
              })}
            >
              <Sparkles size={34} color={C.tomato} strokeWidth={2.6} />
            </div>
          ))}
        </Card>
      </div>
      <div style={abs({ left: 90, top: 520, width: 900, transform: `translateY(${(1 - card) * 800}px)` })}>
        <Card style={{ padding: 40 }}>
          <Kicker bg={C.yellow} style={{ fontSize: 24 }}>
            Say this
          </Kicker>
          <div style={{ fontFamily: F.body, fontWeight: 700, fontSize: 44, lineHeight: 1.3, marginTop: 22, minHeight: 120 }}>
            <Typed text="“I miss how we used to talk. Coffee on Friday?”" start={say - 4} cps={34} />
          </div>
          <div style={{ height: 4, background: C.ink, margin: '30px 0', opacity: 0.12 }} />
          <Kicker bg={C.mint} style={{ fontSize: 24 }}>
            Do this next
          </Kicker>
          <div style={{ fontFamily: F.body, fontWeight: 600, fontSize: 40, lineHeight: 1.3, marginTop: 22, minHeight: 104 }}>
            <Typed text="Send it once, then give them space to reply." start={doNext - 6} cps={36} />
          </div>
        </Card>
      </div>
    </AbsoluteFill>
  )
}

// =========================================================================================== 7. voice
function Waveform({ startSec, active }: { startSec: number; active: number }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const audio = useAudioData(staticFile('soundtrack.wav'))
  const bars = 32
  let values = Array.from({ length: bars }, () => 0)
  if (audio) {
    const raw = visualizeAudio({ fps, frame: Math.round(startSec * fps) + frame, audioData: audio, numberOfSamples: 64 })
    values = raw.slice(1, bars + 1).map((v) => Math.min(1, Math.sqrt(v) * 4.5))
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, height: 190 }}>
      {values.map((v, i) => {
        const mirror = values[Math.abs(bars / 2 - i) % bars]
        const h = 16 + (0.5 * v + 0.5 * mirror) * 170 * active
        return (
          <div
            key={i}
            style={{
              width: 18,
              height: h,
              borderRadius: 9,
              background: i % 3 === 0 ? C.tomato : C.ink,
              border: `3px solid ${C.ink}`,
            }}
          />
        )
      })}
    </div>
  )
}

export function VoiceScene({ s, startSec }: { s: Scene; startSec: number }) {
  const frame = useCurrentFrame()
  const speak = at(s, 'just', 61)
  const read = at(s, 'read', 121)
  const mic = useIn(2, { damping: 11 })
  const split = interpolate(frame, [read - 14, read + 6], [0, 1], { ...clamp, easing: (t) => t * t * (3 - 2 * t) })
  const speaker = useIn(read - 8, { damping: 11 })
  const pulse = (frame % 30) / 30
  const headline = frame < speak - 4 ? 'TIRED OF TYPING?' : frame < read - 6 ? 'JUST SPEAK.' : 'OR JUST LISTEN.'
  const headlineAt = frame < speak - 4 ? at(s, "don't", 15) - 4 : frame < read - 6 ? speak - 4 : read - 6
  return (
    <AbsoluteFill>
      <div style={abs({ left: 0, right: 0, top: 50 })} key={headline}>
        <StretchTitle text={headline} delay={headlineAt} size={92} color={headline === 'JUST SPEAK.' ? C.tomato : C.ink} />
      </div>
      {/* Mic */}
      <div style={abs({ left: 540 - 130 - split * 240, top: 230, transform: `scale(${mic * (1 - 0.15 * split)})` })}>
        {[0, 1].map((k) => (
          <div
            key={k}
            style={abs({
              left: 130 - 130,
              top: 0,
              width: 260,
              height: 260,
              borderRadius: 999,
              border: `4px solid ${C.tomato}`,
              transform: `scale(${1 + ((pulse + k / 2) % 1) * 0.7})`,
              opacity: (1 - ((pulse + k / 2) % 1)) * (frame > speak - 6 && frame < read ? 1 : 0.25),
            })}
          />
        ))}
        <div
          style={{
            width: 260,
            height: 260,
            borderRadius: 999,
            background: C.tomato,
            border: BORDER,
            boxShadow: shadow(10),
            display: 'grid',
            placeItems: 'center',
          }}
        >
          <Mic size={130} strokeWidth={2.4} color={C.ink} />
        </div>
      </div>
      {/* Speaker */}
      <div style={abs({ left: 540 + 110, top: 230, transform: `scale(${speaker * 0.85})`, opacity: split })}>
        <div
          style={{
            width: 260,
            height: 260,
            borderRadius: 999,
            background: C.yellow,
            border: BORDER,
            boxShadow: shadow(10),
            display: 'grid',
            placeItems: 'center',
          }}
        >
          <Volume2 size={130} strokeWidth={2.4} color={C.ink} />
        </div>
      </div>
      <div style={abs({ left: 0, right: 0, top: 560 })}>
        <Waveform startSec={startSec} active={interpolate(frame, [s.voFrom - 4, s.voFrom + 6], [0.15, 1], clamp)} />
      </div>
      <div style={abs({ left: 70, right: 70, top: 800, opacity: useIn(speak + 4) })}>
        <Bubble side="user" style={{ transform: 'scale(1.35)', transformOrigin: 'right top' }}>
          <Typed text="Should I call him tonight, or wait till tomorrow?" start={speak + 6} cps={26} />
        </Bubble>
      </div>
    </AbsoluteFill>
  )
}

// =========================================================================================== 8. trust
export function TrustScene({ s }: { s: Scene }) {
  const guides = [
    { title: 'Feeling unheard', topic: 'Communication', bg: C.sky },
    { title: 'Repair after a fight', topic: 'Conflict', bg: C.yellow },
    { title: 'First dates & texting', topic: 'Dating', bg: C.heartPink },
  ]
  const lib = at(s, 'library', 63)
  const check = at(s, 'check', 88)
  const unsafe = at(s, 'unsafe', 154)
  const help = at(s, 'help', 230)
  const cardA = useIn(at(s, 'advice', 21) - 6, { damping: 14 })
  const cardB = useIn(unsafe - 8, { damping: 13 })
  return (
    <AbsoluteFill>
      <div style={abs({ left: 70, top: 50, width: 940, transform: `translateX(${(1 - cardA) * -1200}px)` })}>
        <Card style={{ padding: 36 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <IconTile bg={C.lilac} size={96}>
              <BookOpen size={56} strokeWidth={2.4} />
            </IconTile>
            <div>
              <div style={{ fontFamily: F.display, fontWeight: 900, fontSize: 48, fontStretch: '108%' }}>GUIDE LIBRARY</div>
              <div style={{ fontFamily: F.body, fontSize: 28, color: C.muted }}>“See where this comes from”</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 28 }}>
            {guides.map((g, i) => {
              const p = useIn(lib - 6 + i * 7, { damping: 14 })
              return (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 18,
                    border: BORDER,
                    borderRadius: 14,
                    padding: '20px 22px',
                    background: C.paperLight,
                    transform: `translateX(${(1 - p) * 300}px)`,
                    opacity: Math.min(1, p * 1.4),
                  }}
                >
                  <div style={{ width: 22, height: 22, borderRadius: 6, background: g.bg, border: `3px solid ${C.ink}` }} />
                  <div style={{ flex: 1, fontFamily: F.body, fontWeight: 700, fontSize: 36 }}>{g.title}</div>
                  <div style={{ fontFamily: F.mono, fontSize: 22, fontWeight: 700, color: C.muted }}>{g.topic.toUpperCase()}</div>
                  <Check size={34} strokeWidth={3.5} color={C.green} style={{ opacity: useIn(check + i * 3) }} />
                </div>
              )
            })}
          </div>
        </Card>
      </div>
      <div style={abs({ left: 70, top: 660, width: 940, transform: `translateY(${(1 - cardB) * 900}px)` })}>
        <Card bg={C.mint} style={{ padding: 36 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 26 }}>
            <IconTile bg={C.white} size={110}>
              <ShieldCheck size={66} strokeWidth={2.4} />
            </IconTile>
            <div style={{ fontFamily: F.body, fontWeight: 800, fontSize: 46, lineHeight: 1.2 }}>
              If you are not safe, you deserve help right now.
            </div>
          </div>
          <div style={{ display: 'flex', gap: 18, marginTop: 28, flexWrap: 'wrap' }}>
            <Chip bg={C.white} size={34} style={{ transform: `scale(${useIn(at(s, 'gently', 192) - 4, { damping: 9 })})` }}>
              Emergency · 999
            </Chip>
            <Chip bg={C.yellow} size={34} style={{ transform: `scale(${useIn(help - 14, { damping: 9 })})` }}>
              Talk to someone you trust
            </Chip>
          </div>
        </Card>
      </div>
    </AbsoluteFill>
  )
}

// =========================================================================================== 9. phone
export function PhoneScene({ s }: { s: Scene }) {
  const frame = useCurrentFrame()
  const phone = useIn(0, { damping: 15, stiffness: 100 })
  const tilt = interpolate(frame, [0, s.durationInFrames], [-22, 10])
  const badges = [
    { icon: <UserX size={52} strokeWidth={2.5} />, label: 'No sign-up', bg: C.yellow, t: at(s, 'no', 17) },
    { icon: <Download size={52} strokeWidth={2.5} />, label: 'Nothing to install', bg: C.sky, t: at(s, 'nothing', 59) },
    { icon: <Smartphone size={52} strokeWidth={2.5} />, label: 'Works on your phone', bg: C.mint, t: at(s, 'works', 111) },
  ]
  return (
    <AbsoluteFill>
      <div
        style={abs({
          left: 600,
          top: 150,
          perspective: 1400,
          transform: `translateX(${(1 - phone) * 700}px)`,
        })}
      >
        <div style={{ transform: `rotateY(${tilt}deg) rotateZ(3deg)` }}>
          <Phone width={420} height={850}>
            <AppBar title="" />
            <div style={{ padding: '40px 26px' }}>
              <Kicker style={{ fontSize: 15, padding: '6px 12px' }}>A more thoughtful way</Kicker>
              <div style={{ fontFamily: F.display, fontWeight: 900, fontSize: 40, lineHeight: 1.02, marginTop: 24 }}>
                UNDERSTAND
              </div>
              <div
                style={{
                  display: 'inline-block',
                  background: C.tomato,
                  border: `3px solid ${C.ink}`,
                  padding: '0 10px',
                  margin: '6px 0',
                  transform: 'rotate(-2deg)',
                  fontFamily: F.display,
                  fontWeight: 900,
                  fontSize: 34,
                  fontStretch: '112%',
                  whiteSpace: 'nowrap',
                }}
              >
                EACH OTHER
              </div>
              <div style={{ fontFamily: F.display, fontWeight: 900, fontSize: 40, lineHeight: 1.02 }}>BETTER.</div>
              <div
                style={{
                  marginTop: 40,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 10,
                  background: C.tomato,
                  border: `3px solid ${C.ink}`,
                  boxShadow: shadow(4),
                  padding: '14px 20px',
                  fontFamily: F.body,
                  fontWeight: 800,
                  fontSize: 24,
                }}
              >
                Start a conversation <ArrowRight size={24} strokeWidth={3} />
              </div>
            </div>
          </Phone>
        </div>
      </div>
      {badges.map((b, i) => {
        const p = useIn(b.t - 4, { damping: 9, stiffness: 200 })
        return (
          <div
            key={i}
            style={abs({
              left: 50,
              top: 220 + i * 250,
              transform: `scale(${p}) rotate(${(i % 2 ? 2 : -3) + (1 - p) * -20}deg)`,
              transformOrigin: 'left center',
            })}
          >
            <Card bg={b.bg} style={{ display: 'flex', alignItems: 'center', gap: 22, padding: '24px 30px', width: 540 }} depth={8}>
              {b.icon}
              <div style={{ fontFamily: F.display, fontWeight: 900, fontSize: 44, fontStretch: '104%', lineHeight: 1.05 }}>
                {b.label.toUpperCase()}
              </div>
            </Card>
          </div>
        )
      })}
    </AbsoluteFill>
  )
}

// =========================================================================================== 10. call to action
export function CtaScene({ s, link }: { s: Scene; link: string }) {
  const frame = useCurrentFrame()
  const logo = useIn(2, { damping: 10 })
  const listen = at(s, 'listen', 60)
  const understand = at(s, 'understand', 101)
  const tryAt = at(s, 'try', 145)
  const linkAt = at(s, 'link', 189)
  const btn = useIn(tryAt - 4, { damping: 9, stiffness: 200 })
  const linkIn = useIn(linkAt - 8, { damping: 13 })
  const beat = 1 + 0.12 * Math.max(0, Math.sin((frame / 30) * Math.PI * 2 * 1.1))
  const rand = seeded(41)
  const rise = Array.from({ length: 18 }, () => ({ x: rand() * 1080, delay: rand() * 90, size: 26 + rand() * 46, speed: 6 + rand() * 6 }))
  return (
    <AbsoluteFill>
      {rise.map((h, i) => {
        const t = frame - (linkAt + h.delay)
        if (t < 0) return null
        return (
          <div key={i} style={abs({ left: h.x + Math.sin(t / 12 + i) * 20, top: 1150 - t * h.speed, opacity: 0.85 })}>
            <HeartShape size={h.size} fill={i % 2 ? C.heartPink : C.heartRed} />
          </div>
        )
      })}
      <div style={abs({ left: 0, right: 0, top: 50, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 26 })}>
        <div style={{ transform: `scale(${logo})`, borderRadius: 30, boxShadow: shadow(8) }}>
          <Logo size={150} heartScale={beat} />
        </div>
        <div>
          <StretchTitle text="COUPLECARE" delay={at(s, 'couplecare', 16) - 6} size={86} style={{ justifyContent: 'flex-start' }} />
          <div
            style={{
              display: 'inline-block',
              marginTop: 8,
              background: C.tomato,
              border: BORDER,
              boxShadow: shadow(5),
              padding: '0 14px',
              fontFamily: F.display,
              fontWeight: 900,
              fontSize: 54,
              transform: `scale(${useIn(at(s, 'ai', 37) - 3, { damping: 8, stiffness: 220 })})`,
            }}
          >
            AI
          </div>
        </div>
      </div>
      <div style={abs({ left: 0, right: 0, top: 310 })}>
        <StaggerWords text="LISTEN FIRST." delay={listen - 4} style={{ fontFamily: F.display, fontWeight: 900, fontSize: 100, fontStretch: '115%' }} />
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 16 }}>
          <div
            style={{
              background: C.yellow,
              border: BORDER,
              boxShadow: shadow(8),
              padding: '0 24px',
              transform: `rotate(-2deg) scaleX(${useIn(understand - 6, { damping: 12 })})`,
            }}
          >
            <StaggerWords
              text="UNDERSTAND BETTER."
              delay={understand - 2}
              style={{ fontFamily: F.display, fontWeight: 900, fontSize: 72, fontStretch: '104%', flexWrap: 'nowrap' }}
            />
          </div>
        </div>
      </div>
      <div style={abs({ left: 0, right: 0, top: 640, display: 'flex', justifyContent: 'center' })}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 20,
            background: C.tomato,
            border: BORDER,
            borderRadius: 18,
            boxShadow: shadow(btn > 0.95 ? 10 - 4 * Math.abs(Math.sin(frame / 9)) : 10),
            padding: '26px 48px',
            fontFamily: F.display,
            fontWeight: 900,
            fontSize: 64,
            fontStretch: '110%',
            transform: `scale(${btn})`,
          }}
        >
          TRY IT TODAY <ArrowRight size={64} strokeWidth={3.4} />
        </div>
      </div>
      <div style={abs({ left: 60, right: 60, top: 860, transform: `translateY(${(1 - linkIn) * 500}px)`, opacity: Math.min(1, linkIn * 1.5) })}>
        <Card style={{ padding: '26px 30px', textAlign: 'center' }}>
          <div style={{ fontFamily: F.mono, fontWeight: 800, fontSize: 31, wordBreak: 'break-all', lineHeight: 1.3 }}>{link}</div>
          <div style={{ marginTop: 14, fontFamily: F.display, fontWeight: 900, fontSize: 34, color: C.tomato }}>LINK IN THE POST ↓</div>
        </Card>
      </div>
    </AbsoluteFill>
  )
}
