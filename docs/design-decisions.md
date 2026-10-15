# Design & dependency decisions

This log records verified decisions so future contributors know *why* things are the way they are.

## UI references (verified 2026-10-14)

| Reference | Finding | Decision |
|---|---|---|
| **Skiper UI** — <https://skiper-ui.com> | Exists. "Un-common components for shadcn/ui"; distributed through the shadcn CLI registry (`npx shadcn add @skiper-ui/<name>`), built on Tailwind + Motion. Some components are paid (Premium / Exclusive tiers); licence terms are not stated on the landing page. | Used as **visual inspiration only**. We do not copy its paid components. Our components are original, built on the same primitives (Tailwind + Motion). |
| **Vengeance UI** — <https://www.vengenceui.com> (note the spelling of the domain) | Exists. Collection of animated React components installed via `npx shadcn@latest add @vengeanceui/<component>`. Repository <https://github.com/Ashutoshx7/VengeanceUI> is **MIT-licensed** (re-checked 2026-10-15). | **Used (2026-10-15):** Stagger Text, Flip Text and Kinetic Text Loader were adapted into `frontend/src/components/kinetic/` (motion/react instead of framer-motion, reduced-motion fallbacks, no Google Fonts request, Bangla-safe grapheme splitting). Attribution and licence text in `frontend/THIRD_PARTY_NOTICES.md`. |
| **AnimMaster Lib** | Could **not** be verified. Searches returned only unrelated projects (Terraria AnimLib, Blender add-on, Android animlib, Animation:Master 3D software). | Not used. Per the brief, we proceed with an original design rather than guessing a package name. |

## Visual direction (2026-10-15): neo-brutalism + kinetic type

Replaced the original soft "editorial" look, which read as a generic AI template, at the owner's request.
- Tokens only (`styles/index.css`): paper/ink palette with flat tomato, yellow, lilac, mint and sky; 2px ink
  borders everywhere; hard offset shadows (`3px 3px 0` / `6px 6px 0`) that collapse on press (`press` utility);
  small radii.
- Type: Archivo variable (weight 100–900 and width 62–125%) for display and body, JetBrains Mono for labels
  (`kicker`), Noto Sans Bengali for Bangla. All OFL-1.1 via Fontsource.
- Kinetic typography: masked word reveals on headings, a breathing width/weight wave on the hero's key phrase,
  a trilingual marquee band, a stretch-and-squash "Thinking" loader and a flipping 404. Every animation is off
  under reduced motion (OS setting or in-app setting) and the components then render plain text.
- Sources panel simplified for non-technical users: title, topic and a short excerpt; licence, relevance and
  document id moved into a collapsed "Technical details"; passages from the same guide merged into one card.

## Frontend stack (pinned exactly in `frontend/package.json`)

- React 19 + TypeScript + Vite 8
- Tailwind CSS 4 via `@tailwindcss/vite` (CSS-first config, design tokens as CSS variables)
- shadcn/ui-compatible structure (`components.json`, `cn()` helper, Radix primitives) — components are written into the repo, not imported from a runtime UI kit
- `motion` (the successor package of Framer Motion; import path `motion/react`)
- `lucide-react` for every control icon (no emoji controls)
- React Router (declarative mode), TanStack Query for server state
- `sonner` for toasts, `react-markdown` for assistant messages
- Vitest + Testing Library + jsdom

## Backend stack

- Python 3.12, FastAPI, Pydantic v2, pydantic-settings, Uvicorn
- sentence-transformers on **CPU-only PyTorch** (keeps the 8 GB GPU free for the generator)
- FAISS (CPU), rank-bm25, pypdf, BeautifulSoup
- SQLite via the standard library (`sqlite3`, parameterized queries)
