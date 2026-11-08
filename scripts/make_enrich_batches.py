#!/usr/bin/env python3
"""Split the companies in data/bitsians.csv into to-do batches for enrichment.

Writes data/enrich/todo_<n>.csv, one row per company, carrying what we already
know (website, city, sector, founders) so the enricher can disambiguate and
skip work that is already done.

Run:  python3 -I scripts/make_enrich_batches.py [n_batches]
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "bitsians.csv"
OUT_DIR = ROOT / "data" / "enrich"
COLUMNS = ["company_name", "known_website", "known_city_hq", "known_country", "sector", "one_line", "founders"]


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    companies: dict[str, dict] = {}
    with SRC.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            c = companies.setdefault(r["company_name"], {
                "company_name": r["company_name"], "known_website": "", "known_city_hq": "",
                "known_country": "", "sector": "", "one_line": "", "founders": [],
            })
            for src, dst in [("company_website", "known_website"), ("city_hq", "known_city_hq"),
                             ("country", "known_country"), ("sector", "sector"), ("one_line", "one_line")]:
                if not c[dst] and r[src].strip():
                    c[dst] = r[src].strip()
            if r["founder_name"].strip():
                c["founders"].append(r["founder_name"].strip())

    rows = sorted(companies.values(), key=lambda c: c["company_name"].lower())
    for c in rows:
        c["founders"] = "; ".join(c["founders"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        batch = rows[i::n]  # interleave so every batch gets a mix of easy and hard names
        with (OUT_DIR / f"todo_{i + 1}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(batch)
        print(f"todo_{i + 1}.csv: {len(batch)} companies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
