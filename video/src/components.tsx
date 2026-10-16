import type { CSSProperties, ReactNode } from 'react'
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion'
import { BORDER, C, F, shadow } from './theme'

// ------------------------------------------------------------------------------------------- motion helpers
export function useIn(delay = 0, config: { damping?: number; stiffness?: number; mass?: number } = {}) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  return spring({ frame: frame - delay, fps, config: { damping: 14, stiffness: 140, mass: 0.8, ...config } })
}

export const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const

/** Deterministic pseudo-random numbers (same every render). */
export function seeded(seed: number) {
  let x = seed
  return () => {
    x = (x * 16807) % 2147483647
    return (x - 1) / 2147483646
  }
}

// ------------------------------------------------------------------------------------------- shapes
export const HEART_PATH =
  'M12 21s-6.7-4.35-9.33-8.04C.57 9.94 1.9 5.5 5.9 4.6c2.2-.5 4.3.5 6.1 2.6 1.8-2.1 3.9-3.1 6.1-2.6 4 .9 5.33 5.34 3.23 8.36C18.7 16.65 12 21 12 21z'

export function HeartShape({ size, fill = C.heartRed, stroke = C.ink, strokeWidth = 1.3, style }: {
  size: number
  fill?: string
  stroke?: string
  strokeWidth?: number
  style?: CSSProperties
}) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} style={style}>
      <path d={HEART_PATH} fill={fill} stroke={stroke} strokeWidth={strokeWidth} strokeLinejoin="round" />
    </svg>
  )
}

/** The app logo: a couple holding hands under a heart. */
export function Logo({ size, heartScale = 1 }: { size: number; heartScale?: number }) {
  return (
    <svg viewBox="0 0 32 32" width={size} height={size}>
      <rect x="1" y="1" width="30" height="30" rx="6" fill={C.paperLight} stroke={C.ink} strokeWidth="2" />
      <g transform="translate(3 3) scale(0.8125)">
        <g transform={`translate(16 6.2) scale(${heartScale}) translate(-16 -6.2)`}>
          <path
            d="M16 9.6s-3.5-2.2-3.5-4.6c0-1.25 1-2.15 2.05-2.15.7 0 1.15.3 1.45.85.3-.55.75-.85 1.45-.85 1.05 0 2.05.9 2.05 2.15 0 2.4-3.5 4.6-3.5 4.6z"
            fill={C.heartRed}
            stroke={C.ink}
            strokeWidth="1.1"
            strokeLinejoin="round"
          />
        </g>
        <circle cx="7.5" cy="10.8" r="3.1" fill={C.ink} />
        <circle cx="24.5" cy="10.8" r="3.1" fill={C.ink} />
        <path d="M3.9 29v-8.3a3.6 3.6 0 0 1 7.2 0V29z" fill={C.ink} />
        <path d="M20.9 29v-8.3a3.6 3.6 0 0 1 7.2 0V29z" fill={C.ink} />
        <path d="M10.4 17.6 L15.2 23.4 M21.6 17.6 L16.8 23.4" fill="none" stroke={C.ink} strokeWidth="2.2" strokeLinecap="round" />
        <circle cx="16" cy="23.6" r="2" fill={C.heartRed} stroke={C.ink} strokeWidth="1.1" />
      </g>
    </svg>
  )
}

// ------------------------------------------------------------------------------------------- background
export function Background({ dark = false, hearts = 16, seed = 3 }: { dark?: boolean; hearts?: number; seed?: number }) {
  const frame = useCurrentFrame()
  const { width, height } = useVideoConfig()
  const rand = seeded(seed)
  const list = Array.from({ length: hearts }, (_, i) => ({
    x: rand() * width,
    y: rand() * height,
    size: 26 + rand() * 54,
    speed: 0.25 + rand() * 0.5,
    sway: rand() * Math.PI * 2,
    rot: -25 + rand() * 50,
    kind: i % 3,
  }))
  const dot = dark ? 'rgba(255,255,255,0.07)' : 'rgba(30,30,40,0.09)'
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: dark ? C.ink : C.paper,
        backgroundImage: `radial-gradient(${dot} 2px, transparent 2.5px)`,
        backgroundSize: '34px 34px',
        backgroundPosition: `0 ${-frame * 0.4}px`,
        overflow: 'hidden',
      }}
    >
      {list.map((h, i) => {
        const y = ((h.y - frame * h.speed * 2) % (height + 120) + height + 120) % (height + 120) - 60
        const x = h.x + Math.sin(frame / 40 + h.sway) * 18
        const fill = h.kind === 0 ? C.heartPink : h.kind === 1 ? C.heartRed : 'none'
        const stroke = h.kind === 2 ? C.heartRed : dark ? C.paper : C.ink
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              opacity: dark ? 0.22 : 0.3,
              transform: `rotate(${h.rot + Math.sin(frame / 30 + i) * 6}deg)`,
            }}
          >
            <HeartShape size={h.size} fill={fill} stroke={stroke} strokeWidth={h.kind === 2 ? 1.8 : 1.2} />
          </div>
        )
      })}
    </div>
  )
}

// ------------------------------------------------------------------------------------------- blocks
export function Card({ children, style, bg = C.white, depth = 10 }: {
  children: ReactNode
  style?: CSSProperties
  bg?: string
  depth?: number
}) {
  return (
    <div style={{ background: bg, border: BORDER, borderRadius: 18, boxShadow: shadow(depth), ...style }}>{children}</div>
  )
}

export function Chip({ children, bg = C.yellow, style, size = 30 }: {
  children: ReactNode
  bg?: string
  style?: CSSProperties
  size?: number
}) {
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 12,
        background: bg,
        border: BORDER,
        borderRadius: 999,
        boxShadow: shadow(5),
        padding: `${size * 0.32}px ${size * 0.8}px`,
        fontFamily: F.body,
        fontWeight: 800,
        fontSize: size,
        color: C.ink,
        whiteSpace: 'nowrap',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

/** Small mono label, like the app's kicker. */
export function Kicker({ children, bg = C.yellow, style }: { children: ReactNode; bg?: string; style?: CSSProperties }) {
  return (
    <div
      style={{
        display: 'inline-block',
        background: bg,
        border: BORDER,
        boxShadow: shadow(5),
        padding: '10px 20px',
        fontFamily: F.mono,
        fontWeight: 700,
        fontSize: 26,
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
        color: C.ink,
        ...style,
      }}
    >
      {children}
    </div>
  )
}

export function Bubble({ children, side, style, lang }: {
  children: ReactNode
  side: 'user' | 'ai'
  style?: CSSProperties
  lang?: string
}) {
  const user = side === 'user'
  return (
    <div style={{ display: 'flex', justifyContent: user ? 'flex-end' : 'flex-start', ...style }}>
      <div
        style={{
          maxWidth: '84%',
          background: user ? C.ink : C.white,
          color: user ? C.paperLight : C.ink,
          border: BORDER,
          borderRadius: user ? '22px 22px 6px 22px' : '22px 22px 22px 6px',
          boxShadow: shadow(5),
          padding: '16px 22px',
          fontFamily: lang === 'bn' ? F.bangla : F.body,
          fontSize: 27,
          lineHeight: 1.35,
          fontWeight: user ? 600 : 500,
        }}
      >
        {children}
      </div>
    </div>
  )
}

/** Phone frame around app-like content. */
export function Phone({ children, width = 600, height = 960, style }: {
  children: ReactNode
  width?: number
  height?: number
  style?: CSSProperties
}) {
  return (
    <div
      style={{
        width,
        height,
        background: C.ink,
        borderRadius: 64,
        padding: 16,
        boxShadow: shadow(16),
        ...style,
      }}
    >
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          borderRadius: 50,
          overflow: 'hidden',
          background: C.paper,
          backgroundImage: 'radial-gradient(rgba(30,30,40,0.08) 1.6px, transparent 2px)',
          backgroundSize: '26px 26px',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 14,
            left: '50%',
            width: 130,
            height: 34,
            marginLeft: -65,
            borderRadius: 20,
            background: C.ink,
            zIndex: 5,
          }}
        />
        {children}
      </div>
    </div>
  )
}

/** App header bar shown inside the phone. */
export function AppBar({ title = 'New conversation', coach = false }: { title?: string; coach?: boolean }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        padding: '64px 24px 16px',
        borderBottom: BORDER,
        background: C.paperLight,
      }}
    >
      <Logo size={46} />
      <div style={{ fontFamily: F.display, fontWeight: 900, fontSize: 24, fontStretch: '115%', letterSpacing: '0.02em' }}>
        COUPLECARE
      </div>
      <div
        style={{
          background: C.tomato,
          border: `3px solid ${C.ink}`,
          borderRadius: 6,
          padding: '0 8px',
          fontFamily: F.display,
          fontWeight: 900,
          fontSize: 22,
          color: C.ink,
        }}
      >
        AI
      </div>
      <div style={{ flex: 1 }} />
      <div style={{ fontFamily: F.mono, fontSize: 17, fontWeight: 700, color: C.muted }}>{coach ? 'COACH' : title}</div>
    </div>
  )
}

/** Words that pop in one after another. */
export function StaggerWords({ text, delay = 0, every = 4, style, wordStyle }: {
  text: string
  delay?: number
  every?: number
  style?: CSSProperties
  wordStyle?: (i: number) => CSSProperties
}) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '0 0.28em', ...style }}>
      {text.split(' ').map((w, i) => {
        const s = spring({ frame: frame - delay - i * every, fps, config: { damping: 12, stiffness: 160, mass: 0.7 } })
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              opacity: Math.min(1, s * 1.4),
              transform: `translateY(${(1 - s) * 60}px) scale(${0.7 + 0.3 * s}) rotate(${(1 - s) * (i % 2 ? 6 : -6)}deg)`,
              ...wordStyle?.(i),
            }}
          >
            {w}
          </span>
        )
      })}
    </div>
  )
}

/** Big display title whose letters stretch open (Archivo's width axis), like the app's hero. */
export function StretchTitle({ text, delay = 0, size = 120, color = C.ink, style }: {
  text: string
  delay?: number
  size?: number
  color?: string
  style?: CSSProperties
}) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  return (
    <div style={{ display: 'flex', justifyContent: 'center', ...style }}>
      {text.split('').map((ch, i) => {
        const s = spring({ frame: frame - delay - i * 1.6, fps, config: { damping: 11, stiffness: 120, mass: 0.6 } })
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              fontFamily: F.display,
              fontWeight: 900,
              fontSize: size,
              lineHeight: 1,
              color,
              fontStretch: `${interpolate(s, [0, 1], [62, 125])}%`,
              transform: `translateY(${(1 - s) * 80}px)`,
              opacity: Math.min(1, s * 2),
              whiteSpace: 'pre',
            }}
          >
            {ch}
          </span>
        )
      })}
    </div>
  )
}

/** A rubber-stamp style mark that slams onto a card. */
export function Stamp({ children, delay, color = C.red, rotate = -12, style }: {
  children: ReactNode
  delay: number
  color?: string
  rotate?: number
  style?: CSSProperties
}) {
  const s = useIn(delay, { damping: 9, stiffness: 220, mass: 0.6 })
  if (s <= 0.001) return null
  return (
    <div
      style={{
        position: 'absolute',
        border: `6px solid ${color}`,
        color,
        borderRadius: 12,
        padding: '6px 18px',
        fontFamily: F.display,
        fontWeight: 900,
        fontSize: 34,
        fontStretch: '110%',
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        background: 'rgba(255,255,255,0.85)',
        transform: `rotate(${rotate}deg) scale(${interpolate(s, [0, 1], [2.4, 1])})`,
        opacity: Math.min(1, s * 1.5),
        ...style,
      }}
    >
      {children}
    </div>
  )
}

/** Typewriter text. */
export function Typed({ text, start, cps = 30, style }: { text: string; start: number; cps?: number; style?: CSSProperties }) {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()
  const n = Math.max(0, Math.floor(((frame - start) / fps) * cps))
  const shown = Array.from(text).slice(0, n).join('')
  const caret = n < Array.from(text).length && frame >= start && Math.floor(frame / 8) % 2 === 0
  return (
    <span style={style}>
      {shown}
      <span style={{ opacity: caret ? 1 : 0 }}>▍</span>
    </span>
  )
}
