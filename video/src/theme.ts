// Same palette and type as the app (frontend/src/styles/index.css): paper, ink and a few loud flat colours.
export const C = {
  paper: 'oklch(0.965 0.028 88)',
  paperLight: 'oklch(0.985 0.012 90)',
  paperDark: 'oklch(0.93 0.04 86)',
  ink: 'oklch(0.17 0.01 270)',
  inkSoft: 'oklch(0.36 0.016 270)',
  muted: 'oklch(0.4 0.015 270)',
  white: '#ffffff',
  tomato: 'oklch(0.69 0.19 34)',
  tomatoLight: 'oklch(0.76 0.16 36)',
  yellow: 'oklch(0.91 0.17 100)',
  lilac: 'oklch(0.82 0.1 300)',
  lilacDeep: 'oklch(0.47 0.17 295)',
  mint: 'oklch(0.88 0.11 165)',
  sky: 'oklch(0.84 0.09 235)',
  green: 'oklch(0.55 0.13 155)',
  red: 'oklch(0.55 0.2 27)',
  heartPink: 'oklch(0.8 0.14 2)',
  heartRed: 'oklch(0.63 0.22 22)',
}

export const F = {
  display: "'Archivo Variable', 'Noto Sans Bengali Variable', system-ui, sans-serif",
  body: "'Archivo Variable', 'Noto Sans Bengali Variable', system-ui, sans-serif",
  bangla: "'Noto Sans Bengali Variable', 'Archivo Variable', system-ui, sans-serif",
  mono: "'JetBrains Mono Variable', ui-monospace, monospace",
}

export const BORDER = `4px solid ${C.ink}`
export const shadow = (n = 10) => `${n}px ${n}px 0 0 ${C.ink}`

/** Content is laid out on a 1080×1350 stage (4:5); taller frames get extra background above and below. */
export const STAGE = { width: 1080, height: 1350 }
/** Bottom band of the stage reserved for captions. */
export const CAPTION_TOP = 1140
