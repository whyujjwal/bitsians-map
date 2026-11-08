#!/usr/bin/env python3
"""Turn the Coresignal leads pulled on 2026-11-07 into dataset rows.

Input:  data/private/coresignal_leads_raw.txt   (" ~~ "-delimited, includes LinkedIn URLs)
Output: data/private/coresignal_leads.csv       (all fields, PRIVATE: profile links, do not publish)
        data/raw/coresignal.csv                 (founder schema, no profile links, feeds merge.py)

Coresignal is a licensed, LinkedIn-derived database, so every row is
confidence "medium" and needs verification (or the founder's consent) before it
is shown publicly. Rows are dropped from the map feed when the "company" is a
stealth placeholder, the title is "founder in residence", or the only BITS link
is a short bootcamp rather than a degree.

Run:  python3 -I scripts/import_coresignal.py
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "private" / "coresignal_leads_raw.txt"
PRIVATE = ROOT / "data" / "private" / "coresignal_leads.csv"
OUT = ROOT / "data" / "raw" / "coresignal.csv"
COLUMNS = ["company_name", "company_website", "founder_name", "founder_role", "bits_campus", "grad_year",
           "city_hq", "country", "sector", "stage", "founded_year", "one_line", "source_url", "source_note",
           "confidence"]
BAD_SITES = ("harmonic.ai", "forms.gle", "webflow.io")
THIS_YEAR = 2026


def campus_of(bits: str, grad: int | None, wilp: bool) -> str:
    for c in ("Goa", "Hyderabad", "Dubai"):
        if c.lower() in bits.lower():
            return c
    if grad and grad <= 2003 and not wilp:
        return "Pilani"  # only Pilani had graduates before 2004
    return "unknown"


def main() -> int:
    lines = RAW.read_text(encoding="utf-8").splitlines()
    header = [h.strip() for h in lines[0].split(" ~~ ")]
    leads = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("~~")]
        leads.append(dict(zip(header, parts + [""] * (len(header) - len(parts)))))

    with PRIVATE.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(leads)

    rows, dropped = [], []
    for l in leads:
        bits = l["bits"]
        years = [int(y) for y in re.findall(r"\b(19\d\d|20\d\d)\b", bits)]
        grad = max(years) if years else None
        wilp = bool(re.search(r"work integrated|software system", bits, re.I))
        reason = ""
        if re.search(r"stealth", l["company"], re.I):
            reason = "stealth company"
        elif re.search(r"in residence", l["title"], re.I):
            reason = "founder-in-residence role"
        elif re.search(r"bootcamp", bits, re.I) and not re.search(r"bachelor|master|b\.?e\b|m\.?sc|mtech|ms\b|mba|phd", bits, re.I):
            reason = "BITS link is a bootcamp only"
        if reason:
            dropped.append((l["company"], reason))
            continue
        site = l["company_website"]
        if any(b in site for b in BAD_SITES):
            site = ""
        hq = [p.strip() for p in l["company_hq"].split(",")] if l["company_hq"] else []
        notes = [f"Coresignal licensed record: {l['title']} at {l['company']}", f"BITS education: {bits}"]
        if wilp:
            notes.append("work-integrated (WILP) programme")
        if grad and grad > THIS_YEAR:
            notes.append(f"current student, expected {grad}")
        rows.append({
            "company_name": l["company"], "company_website": site, "founder_name": l["full_name"],
            "founder_role": l["title"], "bits_campus": campus_of(bits, grad, wilp),
            "grad_year": str(grad) if grad else "",
            "city_hq": hq[0] if hq else "", "country": hq[-1] if len(hq) > 1 else "",
            "sector": l["company_industry"], "stage": "", "founded_year": l["company_founded"], "one_line": "",
            "source_url": f"coresignal://employee_multi_source/{l['cs_id']}",
            "source_note": "; ".join(notes), "confidence": "medium",
        })

    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(leads)} leads -> {PRIVATE.name} (private); {len(rows)} rows -> {OUT}")
    print("dropped:", dropped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
