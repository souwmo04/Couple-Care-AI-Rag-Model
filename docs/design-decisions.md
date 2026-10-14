# Design & dependency decisions

This log records verified decisions so future contributors know *why* things are the way they are.

## UI references (verified 2026-10-14)

| Reference | Finding | Decision |
|---|---|---|
| **Skiper UI** — <https://skiper-ui.com> | Exists. "Un-common components for shadcn/ui"; distributed through the shadcn CLI registry (`npx shadcn add @skiper-ui/<name>`), built on Tailwind + Motion. Some components are paid (Premium / Exclusive tiers); licence terms are not stated on the landing page. | Used as **visual inspiration only**. We do not copy its paid components. Our components are original, built on the same primitives (Tailwind + Motion). |
| **Vengeance UI** — <https://www.vengenceui.com> (note the spelling of the domain) | Exists. Collection of animated React components (hover effects, tooltips, scroll-driven layouts), installed via `npx shadcn@latest add @vengeanceui/<component>`. | Inspiration only. Its registry could be added later via `components.json` registries once each component's licence is checked individually. |
| **AnimMaster Lib** | Could **not** be verified. Searches returned only unrelated projects (Terraria AnimLib, Blender add-on, Android animlib, Animation:Master 3D software). | Not used. Per the brief, we proceed with an original design rather than guessing a package name. |

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
