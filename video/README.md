# CoupleCare AI — promo video

A 74-second promo for Facebook, made with [Remotion](https://www.remotion.dev/) using the app's own look:
paper, ink, hard shadows, Archivo and the CoupleCare colours. There are two versions:
- `Promo`: 1080×1350, 4:5, for the Facebook feed.
- `PromoVertical`: 1080×1920, 9:16, for Reels and Stories.

Everything is generated here, with no stock footage or third-party music:

1. **Narration**: `scripts/narration.py` uses Microsoft Edge's neural voice *Ava* (`edge-tts`) and writes one
   clip per scene, plus word timings, to `src/narration.json`.
2. **Soundtrack**: `scripts/soundtrack.py` builds the scene timeline (`src/timeline.json`) and composes original
   music in code: a soft piano intro, a lift when CoupleCare appears, a warm groove under the features, and a
   bell melody at the end. It adds whooshes and pops, ducks the music under the voice, and writes
   `public/soundtrack.wav`.
3. **Picture**: `src/` holds ten scenes (`scenes.tsx`), karaoke captions and wipes (`Promo.tsx`). Every
   animation is keyed to the frame where the narrator says the matching word.

## Rebuild

From the repository root:

```powershell
.venv\Scripts\python.exe -m pip install edge-tts
.venv\Scripts\python.exe video\scripts\narration.py
.venv\Scripts\python.exe video\scripts\soundtrack.py
cd video
npm install
npx remotion studio                                       # preview and edit in the browser
npx remotion render src/index.ts Promo out/couplecare-promo.mp4 --crf=17
npx remotion render src/index.ts PromoVertical out/couplecare-promo-vertical.mp4 --crf=17
```

Changing a line of narration? Edit `LINES` in `scripts/narration.py`, then run both scripts again. The scenes
re-time themselves from the new word timings.

Remotion is free for individuals and small teams (see its license). The narration voice comes from Microsoft's
online text-to-speech service.
