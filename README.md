# BITSians Startup Map

A map and directory of companies founded by BITS Pilani alumni (Pilani, Goa, Hyderabad and Dubai campuses): who founded them, where they are, and who's hiring.

Live: https://bitsians-map.whyujjwalraj.workers.dev

## Layout

- `data/` — the dataset. `raw/*.csv` are per-source founder rows (each with a source link and confidence); `aliases.csv` merges spelling variants; `enrich/` holds company details, geocoding cache and Wikidata matches; `logos/` holds the logo manifest and PNG originals.
- `scripts/` — the Python data pipeline.
- `web/` — the site: Astro (static) + Svelte + MapLibre, deployed to Cloudflare. Design spec in `web/DESIGN.md`.

## Data pipeline

Run from the repo root, in order (`python3 -I` each):

1. `scripts/merge.py` — merge `data/raw/*.csv` into `data/bitsians.csv` (one row per founder–company pair).
2. `scripts/build_companies.py` — join enrichment, geocode (OpenStreetMap Nominatim, cached) into `data/companies.csv`.
3. `scripts/fetch_logos.py` — optional: refresh logos into `web/public/logos/` (then convert to WebP with `cwebp`; originals go to `data/logos/png/`).
4. `scripts/export_web_data.py` — write `web/src/data/companies.json` (company pages) and `web/src/data/index-data.json` (map/list app).

Open roles are refreshed separately, any time: `python3 -I scripts/fetch_jobs.py` reads the public Greenhouse, Lever and Ashby job boards listed in `data/ats_boards.json` and writes `web/src/data/jobs.json` and `jobs-summary.json`. Add `--detect` to look for boards for companies not in that file yet (it follows careers links and careers pages; it never guesses). Edit `data/ats_boards.json` by hand to add a board or block a wrong one (`null`). The site hides role counts 14 days after the last fetch and falls back to the careers link, so refresh and release at least every two weeks.

Founders known only from Coresignal (a licensed source) are excluded from the site by default; `export_web_data.py --include-coresignal` ships them. Coresignal-derived files and `data/private/` are kept out of git.

## Site

Needs Node 24 (`web/.nvmrc`) and pnpm 10.14 (`corepack enable`).

```bash
cd web
cp .env.example .env   # SITE_URL for canonical links and the sitemap; builds stop without it
pnpm install
pnpm dev               # http://localhost:4321
pnpm run deploy:dry-run   # every release check and the build, nothing uploaded
pnpm run deploy        # guarded release from main to Cloudflare (needs `wrangler login`)
```

How releases are checked, verified and rolled back: [RELEASING.md](RELEASING.md).

Not affiliated with BITS Pilani.

## Contributors

- whyujjwal
- [Devansh Goel](https://github.com/Devanshgoel-123)
