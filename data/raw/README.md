# data/raw — knowledge-base source files

Only files listed in [`../metadata/sources.json`](../metadata/sources.json) are ingested.
Nothing in this folder is crawled or picked up automatically.

## Synthetic examples (`synthetic/`)

Every file in `synthetic/` was written for development and testing of CoupleCare AI.
They are **synthetic examples, not authoritative relationship guidance**, and are labelled
as such inside each file and in the manifest (`"synthetic": true`). The UI shows a
"Synthetic example" badge on any citation that comes from them.

## Adding real sources

1. Confirm you have the right to index the material (open licence, public domain,
   written permission, or your own writing). Record that basis in `permission` and `license`.
2. Save a local copy (`.txt`, `.md`, `.html`, or a `.pdf` with a text layer) under this folder.
3. Add an entry to `data/metadata/sources.json` with accurate metadata — never invent an
   author, URL or publication date; leave unknown fields as `null`.
4. Rebuild: `python scripts/build_index.py` or the **Rebuild index** button on `/knowledge`.

Ingestion failures (unsupported type, oversize, no text layer, path outside this folder)
are listed on the Knowledge page and in the index's `ingestion_report.json`.
