#!/usr/bin/env python3
"""Merge data/raw/*.csv into data/bitsians.csv.

One row per (company, founder) pair. Duplicates across source files are
collapsed: the highest-confidence row wins, blank fields are filled from the
other rows, and every source URL is kept. `source_count` is the number of
distinct raw files that agreed on the pair. `needs_review` is set when the
pair is low confidence, or medium confidence from a single file.

Run:  python3 -I scripts/merge.py
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "bitsians.csv"
ALIASES = ROOT / "data" / "aliases.csv"  # kind,variant,canonical (kind: company|person)

COLUMNS = [
    "company_name", "company_website", "founder_name", "founder_role",
    "bits_campus", "grad_year", "city_hq", "country", "sector", "stage",
    "founded_year", "one_line", "source_url", "source_note", "confidence",
]
OUT_COLUMNS = COLUMNS + ["source_count", "source_files", "needs_review"]
RANK = {"high": 3, "medium": 2, "low": 1, "": 0}
SUFFIXES = {"pvt", "ltd", "private", "limited", "inc", "llc", "corp", "corporation"}


def norm_company(name: str) -> str:
    words = re.findall(r"[a-z0-9]+", name.lower())
    words = [w for w in words if w not in SUFFIXES]
    return "".join(words)


def norm_person(name: str) -> str:
    return "".join(re.findall(r"[a-z0-9]+", name.lower()))


def load_aliases() -> dict[str, dict[str, str]]:
    """Map normalized variant -> canonical display name, per kind."""
    out = {"company": {}, "person": {}}
    if not ALIASES.exists():
        return out
    with ALIASES.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            kind = row["kind"].strip()
            norm = norm_company if kind == "company" else norm_person
            out[kind][norm(row["variant"])] = row["canonical"].strip()
    return out


def main() -> int:
    files = sorted(RAW.glob("*.csv"))
    if not files:
        print(f"no CSVs in {RAW}", file=sys.stderr)
        return 1
    aliases = load_aliases()

    groups: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    for f in files:
        with f.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames != COLUMNS:
                print(f"skip {f.name}: header mismatch {reader.fieldnames}", file=sys.stderr)
                continue
            for row in reader:
                company = (row["company_name"] or "").strip()
                if not company:
                    continue
                company = aliases["company"].get(norm_company(company), company)
                row["company_name"] = company
                founder = (row["founder_name"] or "").strip()
                founder = aliases["person"].get(norm_person(founder), founder)
                row["founder_name"] = founder
                key = (norm_company(company), norm_person(founder))
                groups.setdefault(key, []).append((f.stem, row))

    merged = []
    for (_, _), items in groups.items():
        items.sort(key=lambda it: RANK.get(it[1]["confidence"].strip().lower(), 0), reverse=True)
        best = dict(items[0][1])
        urls, notes, srcs = [], [], []
        for stem, row in items:
            for col in COLUMNS:
                if not (best[col] or "").strip() and (row[col] or "").strip():
                    best[col] = row[col]
            u = (row["source_url"] or "").strip()
            if u and u not in urls:
                urls.append(u)
            n = (row["source_note"] or "").strip()
            if n and n not in notes:
                notes.append(n)
            if stem not in srcs:
                srcs.append(stem)
        best["source_url"] = " | ".join(urls)
        best["source_note"] = " | ".join(notes)
        # "BITS Pilani" is also the institute's name, so a bare "Pilani" is weak evidence:
        # a specific Goa/Hyderabad/Dubai from any source wins; two different ones is a conflict.
        campuses = {(row["bits_campus"] or "").strip() for _, row in items} - {"", "unknown"}
        specific = campuses - {"Pilani"}
        campus_conflict = len(specific) > 1
        if len(specific) == 1:
            best["bits_campus"] = specific.pop()
        elif campuses and not campus_conflict:
            best["bits_campus"] = "Pilani"
        else:
            best["bits_campus"] = "unknown"
        conf = best["confidence"].strip().lower()
        best["confidence"] = conf
        best["source_count"] = len(srcs)
        best["source_files"] = ",".join(srcs)
        weak = conf == "low" or (conf == "medium" and len(srcs) == 1)
        best["needs_review"] = "yes" if weak or campus_conflict else ""
        merged.append(best)

    merged.sort(key=lambda r: (-RANK.get(r["confidence"], 0), r["company_name"].lower()))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_COLUMNS)
        w.writeheader()
        w.writerows(merged)

    total = len(merged)
    by_conf = {c: sum(1 for r in merged if r["confidence"] == c) for c in ("high", "medium", "low")}
    companies = len({norm_company(r["company_name"]) for r in merged})
    print(f"{total} rows, {companies} companies -> {OUT}")
    print("confidence:", by_conf, "| needs_review:", sum(1 for r in merged if r["needs_review"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
