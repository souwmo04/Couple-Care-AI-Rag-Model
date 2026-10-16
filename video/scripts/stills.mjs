// Render selected frames as PNGs for review:  node scripts/stills.mjs Promo 100 400 900
import { bundle } from '@remotion/bundler'
import { renderStill, selectComposition } from '@remotion/renderer'
import path from 'node:path'

const [id = 'Promo', ...frames] = process.argv.slice(2)
const root = path.resolve(import.meta.dirname, '..')
const serveUrl = await bundle({ entryPoint: path.join(root, 'src', 'index.ts') })
const composition = await selectComposition({ serveUrl, id })
for (const f of frames.map(Number)) {
  const output = path.join(root, 'out', 'stills', `${id}-${String(f).padStart(4, '0')}.png`)
  await renderStill({ composition, serveUrl, output, frame: f, scale: 0.5 })
  console.log(output)
}
