#!/usr/bin/env python3
"""Export the map-ready dataset to web/src/data/companies.json.

One object per company, founders nested. Publishing rules:
  - "low" confidence founder rows are left out;
  - rows whose ONLY source is the Coresignal import are left out by default,
    because Coresignal's licence limits republishing and those founders have not
    been verified or consented yet. Pass --include-coresignal to ship them.
  - no private data (profile links, raw lead files) is ever exported.

Run:  python3 -I scripts/export_web_data.py [--include-coresignal]
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOUNDERS = ROOT / "data" / "bitsians.csv"
COMPANIES = ROOT / "data" / "companies.csv"
OUT = ROOT / "web" / "src" / "data" / "companies.json"
SLIM = ROOT / "web" / "src" / "data" / "index-data.json"
LOGOS = ROOT / "data" / "logos" / "manifest.csv"
WEB_PUBLIC = ROOT / "web" / "public"

# keyword -> bucket, first match wins; buckets drive the sector filter
SECTOR_RULES = [
    ("AI", r"\bai\b|artificial intelligence|machine learning|llm|generative|agentic"),
    ("Fintech", r"fintech|financ|payment|bank|lending|credit|invest|insur|wealth|tax|capital"),
    ("Healthtech", r"health|medic|diagnos|pharma|hospital|bio|clinic|optomet|surgical|life science"),
    ("Edtech", r"educat|edtech|learning|school|e-learning|career"),
    ("Space & Deeptech", r"space|satellite|aero|drone|robot|defen[cs]e|semiconductor|optic|photon|electro|imaging|hardware|deeptech|nuclear"),
    ("Climate & Mobility", r"climate|energy|solar|ev\b|electric vehicle|charging|mobility|carbon|sustainab|environment|chemical"),
    ("Consumer", r"consumer|retail|grocery|food|d2c|fashion|apparel|beauty|cosmetic|restaurant|lingerie|nutrition|home|ayurved|realty|real estate"),
    ("Logistics & Commerce", r"logistic|delivery|procure|supply|commerce|marketplace|b2b|travel|bus|ticket|warehouse"),
    ("Media & Gaming", r"media|gaming|game|entertain|film|publish|content|music|social"),
    ("SaaS & Dev Tools", r"saas|software|developer|api|cloud|data|security|analytics|platform|it services|consult|internet|network|telecom|enterprise"),
]
CITY_ALIASES = {"bangalore": "Bengaluru", "bengaluru east": "Bengaluru", "gurgaon": "Gurugram", "new delhi": "Delhi",
                "bombay": "Mumbai", "navi mumbai": "Mumbai", "noida": "Noida", "greater noida": "Noida"}


COUNTRY_ALIASES = {"united arab emirates": "UAE", "united states": "USA", "united states of america": "USA",
                   "us": "USA", "u.s.": "USA", "united kingdom": "UK", "england": "UK", "great britain": "UK"}


def norm_country(country: str) -> str:
    c = country.strip()
    return COUNTRY_ALIASES.get(c.lower(), c)


def sector_bucket(text: str) -> str:
    t = text.lower()
    for bucket, pat in SECTOR_RULES:
        if re.search(pat, t):
            return bucket
    return "Other"


def norm_city(city: str) -> str:
    c = city.strip()
    return CITY_ALIASES.get(c.lower(), c)


def stage_bucket(stage: str, status: str) -> str:
    s = f"{stage} {status}".lower()
    for word in ("unicorn", "soonicorn", "minicorn"):
        if word in s:
            return word.capitalize()
    if "acquired" in s:
        return "Acquired"
    if "closed" in s:
        return "Closed"
    if re.search(r"ipo|public|listed", s):
        return "Public"
    if re.search(r"series [c-z]", s):
        return "Series C+"
    if re.search(r"series [ab]", s):
        return "Series A/B"
    if re.search(r"seed|angel|pre-series", s):
        return "Seed"
    return ""


def slugify(name: str, taken: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", re.sub(r"\(.*?\)", "", name.lower())).strip("-") or "company"
    slug, n = base, 2
    while slug in taken:
        slug, n = f"{base}-{n}", n + 1
    taken.add(slug)
    return slug


def num(v: str):
    try:
        return round(float(v), 5)
    except (TypeError, ValueError):
        return None


def load_logos() -> dict[str, dict]:
    """company_name -> {"logo": "/logos/x.png", "logoDark": bool} from scripts/fetch_logos.py's manifest."""
    if not LOGOS.exists():
        return {}
    out = {}
    for r in csv.DictReader(LOGOS.open(encoding="utf-8")):
        f = (r.get("file") or "").strip()
        if not f:
            continue
        # fetch_logos.py writes PNGs; they're converted to WebP (cwebp -q 90, about half the bytes)
        # and the PNG originals live in data/logos/png/. Ship whichever exists in web/public.
        for cand in (f[:-4] + ".webp" if f.endswith(".png") else f, f):
            if (WEB_PUBLIC / cand).exists():
                out[r["company_name"]] = {"logo": "/" + cand.lstrip("/"),
                                          "logoDark": "light_logo" in (r.get("status") or "")}
                break
    return out


def main() -> int:
    include_cs = "--include-coresignal" in sys.argv
    companies = {r["company_name"]: r for r in csv.DictReader(COMPANIES.open(encoding="utf-8"))}
    logos = load_logos()

    founders: dict[str, list] = {}
    for r in csv.DictReader(FOUNDERS.open(encoding="utf-8")):
        if r["confidence"] == "low":
            continue
        if r["source_files"] == "coresignal" and not include_cs:
            continue
        founders.setdefault(r["company_name"], []).append(r)

    out, taken = [], set()
    for name in sorted(founders, key=str.lower):
        rows = founders[name]
        c = companies.get(name, {})
        public_sources = sorted({u.strip() for r in rows for u in r["source_url"].split("|")
                                 if u.strip().startswith("http")})
        lat, lng = num(c.get("lat")), num(c.get("lng"))
        city_known = bool((c.get("city_hq") or next((r["city_hq"] for r in rows if r["city_hq"]), "")).strip())
        if c.get("geo_precision") == "city" and not city_known:
            lat = lng = None  # only the country is known: a country-centroid pin would be misleading
        ilat, ilng = num(c.get("india_lat")), num(c.get("india_lng"))
        sector_raw = c.get("sector") or next((r["sector"] for r in rows if r["sector"]), "")
        stage_raw = c.get("stage") or next((r["stage"] for r in rows if r["stage"]), "")
        out.append({
            "id": slugify(name, taken),
            "name": name,
            "website": c.get("company_website") or next((r["company_website"] for r in rows if r["company_website"]), ""),
            "careers": c.get("careers_url", ""),
            "status": (c.get("status") or "").split(" (")[0],
            "city": norm_city(c.get("city_hq") or next((r["city_hq"] for r in rows if r["city_hq"]), "")),
            "country": norm_country(c.get("country") or next((r["country"] for r in rows if r["country"]), "")),
            "lat": lat, "lng": lng, "precision": c.get("geo_precision") or None,
            "indiaOffice": {"address": c["india_office_address"], "lat": ilat, "lng": ilng}
                           if c.get("india_office_address") and ilat is not None else None,
            "founded": (c.get("founded_year") or "")[:4],
            "sector": sector_bucket(f"{sector_raw} {c.get('one_line', '')}"),
            "sectorRaw": sector_raw,
            "stage": stage_bucket(stage_raw, c.get("status", "")),
            "oneLine": next((t for t in [c.get("one_line", "")] + [r["one_line"] for r in rows]
                             if t and not re.search(r"listed on the BITSAA|notable-alumni page", t)), ""),
            "campuses": sorted({r["bits_campus"] for r in rows if r["bits_campus"] not in ("", "unknown")}),
            "founders": [{"name": r["founder_name"], "role": r["founder_role"],
                          "campus": r["bits_campus"] if r["bits_campus"] != "unknown" else "",
                          "gradYear": r["grad_year"]} for r in rows if r["founder_name"]],
            "logo": logos.get(name, {}).get("logo", ""),
            "logoDark": logos.get(name, {}).get("logoDark", False),
            "verified": any(r["confidence"] == "high" for r in rows),
            "sources": public_sources[:5],
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    # Slim copy for the index page's app bundle: only the fields the map/list UI reads.
    keep = ("id", "name", "website", "careers", "status", "city", "country", "lat", "lng", "precision",
            "founded", "sector", "stage", "oneLine", "campuses", "logo", "logoDark", "sources")
    slim = [{**{k: o[k] for k in keep},
             "founders": [{k: f[k] for k in ("name", "role", "campus", "gradYear")} for f in o["founders"]]}
            for o in out]
    SLIM.write_text(json.dumps(slim, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    pins = sum(1 for o in out if o["lat"] is not None)
    print(f"{len(out)} companies, {sum(len(o['founders']) for o in out)} founders, {pins} with map pins -> {OUT}"
          f" ({OUT.stat().st_size // 1024} KB){' [incl. Coresignal]' if include_cs else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
