#!/usr/bin/env python3
"""Build data/companies.csv: one row per company, ready for map pins.

Joins the enrichment results (data/enrich/out_*.csv) with the founder dataset
(data/bitsians.csv), then geocodes the HQ address and, when present, the
India office address with OpenStreetMap Nominatim. Nominatim's usage policy
allows at most 1 request/second and asks clients to identify themselves, so
every lookup is throttled and cached in data/enrich/geocode_cache.json;
re-runs only query what is new. If the street address does not resolve, the
pin falls back to the city (geo_precision says which one was used).

Run:  python3 -I scripts/build_companies.py [--no-geocode]
"""
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOUNDERS = ROOT / "data" / "bitsians.csv"
ENRICH = ROOT / "data" / "enrich"
CACHE = ENRICH / "geocode_cache.json"
OUT = ROOT / "data" / "companies.csv"

NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "bitsians-map-data-builder/0.1 (one-off geocoding of company office addresses)"
MIN_INTERVAL = 1.1  # seconds between uncached requests

OUT_COLUMNS = [
    "company_name", "company_website", "careers_url", "status", "city_hq", "country",
    "office_address", "lat", "lng", "geo_precision",
    "india_office_address", "india_lat", "india_lng", "india_geo_precision",
    "founded_year", "sector", "stage", "one_line", "founders", "founder_count",
    "bits_campuses", "source_url", "notes",
]


class Geocoder:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
        self.last = 0.0
        self.queries = 0

    def lookup(self, query: str):
        query = " ".join(query.split())
        if not query:
            return None
        if query in self.cache:
            return self.cache[query]
        if not self.enabled:
            return None
        wait = MIN_INTERVAL - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        url = NOMINATIM + "?" + urllib.parse.urlencode({"q": query, "format": "jsonv2", "limit": 1})
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
        except Exception as exc:  # network hiccup: don't cache, try again next run
            print(f"  geocode failed for {query!r}: {exc}", file=sys.stderr)
            self.last = time.monotonic()
            return None
        self.last = time.monotonic()
        self.queries += 1
        hit = [float(data[0]["lat"]), float(data[0]["lon"])] if data else []
        self.cache[query] = hit
        if self.queries % 20 == 0:
            self.save()
        return hit

    def save(self):
        CACHE.write_text(json.dumps(self.cache, indent=1, sort_keys=True))

    def place(self, address: str, city: str, country: str):
        """Return (lat, lng, precision) trying the street address, then the city."""
        for query, precision in [(address, "address"), (", ".join(p for p in (city, country) if p), "city")]:
            if not query.strip(", "):
                continue
            hit = self.lookup(query)
            if hit:
                return f"{hit[0]:.6f}", f"{hit[1]:.6f}", precision
        return "", "", ""


def main() -> int:
    geocoder = Geocoder(enabled="--no-geocode" not in sys.argv)

    agg: dict[str, dict] = {}
    with FOUNDERS.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            a = agg.setdefault(r["company_name"], {"founders": [], "campuses": set(), "sector": "", "stage": "",
                                                   "one_line": "", "website": "", "city": "", "country": "",
                                                   "founded": ""})
            if r["founder_name"].strip():
                a["founders"].append(r["founder_name"].strip())
            if r["bits_campus"] and r["bits_campus"] != "unknown":
                a["campuses"].add(r["bits_campus"])
            for src, dst in [("sector", "sector"), ("stage", "stage"), ("one_line", "one_line"),
                             ("company_website", "website"), ("city_hq", "city"), ("country", "country"),
                             ("founded_year", "founded")]:
                if not a[dst] and r[src].strip():
                    a[dst] = r[src].strip()

    enriched: dict[str, dict] = {}
    for f in sorted(ENRICH.glob("out_*.csv")):
        with f.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                enriched[r["company_name"]] = r
    # Wikidata (scripts/wikidata_enrich.py) only fills fields the research agents left blank.
    wikidata: dict[str, dict] = {}
    wd_file = ENRICH / "wikidata.csv"
    if wd_file.exists():
        with wd_file.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("city_hq") and not r.get("country"):
                    r["city_hq"] = ""  # a bare city is ambiguous to geocode (e.g. Brisbane, CA vs Australia)
                wikidata[r["company_name"]] = r
    missing = sorted(set(agg) - set(enriched))
    if missing:
        print(f"{len(missing)} companies have no enrichment row yet", file=sys.stderr)

    rows = []
    for i, (name, a) in enumerate(sorted(agg.items(), key=lambda kv: kv[0].lower()), 1):
        e = {k: v for k, v in wikidata.get(name, {}).items() if (v or "").strip()}
        e.update({k: v for k, v in enriched.get(name, {}).items() if (v or "").strip()})
        city = e.get("city_hq", "").strip() or a["city"]
        country = e.get("country", "").strip() or a["country"]
        address = e.get("office_address", "").strip()
        lat, lng, prec = geocoder.place(address, city, country)
        india_addr = e.get("india_office_address", "").strip()
        ilat, ilng, iprec = geocoder.place(india_addr, "", "") if india_addr else ("", "", "")
        rows.append({
            "company_name": name,
            "company_website": e.get("company_website", "").strip() or a["website"],
            "careers_url": e.get("careers_url", "").strip(),
            "status": e.get("status", "").strip(),
            "city_hq": city, "country": country, "office_address": address,
            "lat": lat, "lng": lng, "geo_precision": prec,
            "india_office_address": india_addr, "india_lat": ilat, "india_lng": ilng, "india_geo_precision": iprec,
            "founded_year": e.get("founded_year", "").strip() or a["founded"],
            "sector": a["sector"], "stage": a["stage"], "one_line": a["one_line"],
            "founders": "; ".join(a["founders"]), "founder_count": len(a["founders"]),
            "bits_campuses": ", ".join(sorted(a["campuses"])),
            "source_url": e.get("source_url", "").strip(), "notes": e.get("notes", "").strip(),
        })
        if geocoder.enabled and i % 25 == 0:
            print(f"  {i}/{len(agg)} companies placed", file=sys.stderr)

    geocoder.save()
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_COLUMNS)
        w.writeheader()
        w.writerows(rows)

    def filled(col):
        return sum(1 for r in rows if str(r[col]).strip())
    print(f"{len(rows)} companies -> {OUT}  ({geocoder.queries} new geocoder queries)")
    for col in ["company_website", "careers_url", "status", "city_hq", "office_address", "lat", "india_office_address"]:
        print(f"  {col}: {filled(col)}/{len(rows)}")
    print("  pins by precision:", {p: sum(1 for r in rows if r["geo_precision"] == p) for p in ("address", "city")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
