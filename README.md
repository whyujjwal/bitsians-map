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

Founders known only from Coresignal (a licensed source) are excluded from the site by default; `export_web_data.py --include-coresignal` ships them. Coresignal-derived files and `data/private/` are kept out of git.

## Site

```bash
cd web
cp .env.example .env   # SITE_URL for canonical links and the sitemap
pnpm install
pnpm dev               # http://localhost:4321
pnpm run deploy        # build and deploy to Cloudflare (needs `wrangler login`)
```

Not affiliated with BITS Pilani.

## Contributors

- whyujjwal
- [Devansh Goel](https://github.com/Devanshgoel-123)
