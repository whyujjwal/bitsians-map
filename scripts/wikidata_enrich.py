#!/usr/bin/env python3
"""Fill company details from Wikidata's public API into data/enrich/wikidata.csv.

For each company in data/bitsians.csv, search Wikidata by name and accept a
candidate only when it is clearly the same company:
  - one of its "founded by" (P112) people matches one of our founders, or
  - its official website (P856) has the same domain as the one we already have.
Name-only matches are rejected because many company names are generic.

From an accepted item it takes: official website, headquarters city + country
(P159 / P17), the HQ street address qualifier (P6375) when present, inception
year (P571) and dissolved (P576 -> status "closed").

Run:  python3 -I scripts/wikidata_enrich.py
"""
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOUNDERS = ROOT / "data" / "bitsians.csv"
OUT = ROOT / "data" / "enrich" / "wikidata.csv"
API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "bitsians-map-data-builder/0.1 (one-off lookup of company facts)"
COLUMNS = ["company_name", "company_website", "careers_url", "status", "city_hq", "country", "office_address",
           "india_office_address", "founded_year", "source_url", "notes"]


def api(**params):
    params.update(format="json")
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                time.sleep(0.3)
                return json.load(resp)
        except Exception as exc:
            print(f"  retry {attempt + 1}: {exc}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    return {}


def entities(ids, props="claims|labels|descriptions"):
    out = {}
    ids = [i for i in ids if i]
    for i in range(0, len(ids), 50):
        data = api(action="wbgetentities", ids="|".join(ids[i:i + 50]), props=props, languages="en")
        out.update(data.get("entities", {}))
    return out


def label(ent):
    return ent.get("labels", {}).get("en", {}).get("value", "")


def claim_values(ent, pid):
    vals = []
    for c in ent.get("claims", {}).get(pid, []):
        dv = c.get("mainsnak", {}).get("datavalue", {})
        if dv:
            vals.append((dv.get("value"), c))
    return vals


def domain(url):
    host = urllib.parse.urlparse(url if "//" in url else "https://" + url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def toks(name):
    return set(re.findall(r"[a-z]+", name.lower())) - {"dr", "mr", "ms"}


def founder_match(our, theirs):
    for a in our:
        ta = toks(a)
        for b in theirs:
            tb = toks(b)
            if len(ta) >= 2 and len(ta & tb) >= 2:
                return b
    return ""


def main() -> int:
    companies = {}
    with FOUNDERS.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            c = companies.setdefault(r["company_name"], {"founders": set(), "website": ""})
            if r["founder_name"].strip():
                c["founders"].add(r["founder_name"].strip())
            if not c["website"] and r["company_website"].strip():
                c["website"] = r["company_website"].strip()

    rows, accepted = [], 0
    for n, (name, c) in enumerate(sorted(companies.items()), 1):
        query = re.sub(r"\s*\(.*?\)", "", name).strip()  # "Clear (ClearTax)" -> "Clear"
        hits = api(action="wbsearchentities", search=query, language="en", type="item", limit=7).get("search", [])
        cands = entities([h["id"] for h in hits])
        # labels for every founder (P112) mentioned by any candidate
        fids = {v["id"] for e in cands.values() for v, _ in claim_values(e, "P112") if isinstance(v, dict)}
        flabels = {k: label(v) for k, v in entities(sorted(fids), props="labels").items()}

        best, basis = None, ""
        for qid, ent in cands.items():
            theirs = [flabels.get(v["id"], "") for v, _ in claim_values(ent, "P112") if isinstance(v, dict)]
            m = founder_match(c["founders"], theirs)
            if m:
                best, basis = (qid, ent), f"founder match ({m})"
                break
            sites = [v for v, _ in claim_values(ent, "P856") if isinstance(v, str)]
            if c["website"] and any(domain(s) == domain(c["website"]) for s in sites):
                best, basis = (qid, ent), "website match"
                break

        row = {k: "" for k in COLUMNS}
        row["company_name"] = name
        if best:
            accepted += 1
            qid, ent = best
            sites = [v for v, _ in claim_values(ent, "P856") if isinstance(v, str)]
            row["company_website"] = sites[0] if sites else ""
            hq = claim_values(ent, "P159")
            if hq:
                hq_val, hq_claim = hq[0]
                place = entities([hq_val.get("id")]).get(hq_val.get("id"), {})
                row["city_hq"] = label(place)
                ctry = claim_values(place, "P17")
                if ctry:
                    row["country"] = label(entities([ctry[0][0]["id"]], props="labels").get(ctry[0][0]["id"], {}))
                addr = hq_claim.get("qualifiers", {}).get("P6375", [])
                if addr:
                    row["office_address"] = addr[0].get("datavalue", {}).get("value", {}).get("text", "")
            inc = claim_values(ent, "P571")
            if inc and isinstance(inc[0][0], dict):
                row["founded_year"] = inc[0][0].get("time", "")[1:5]
            if claim_values(ent, "P576"):
                row["status"] = "closed"
            row["source_url"] = f"https://www.wikidata.org/wiki/{qid}"
            row["notes"] = f"Wikidata {qid}, {basis}"
        rows.append(row)
        if n % 25 == 0:
            print(f"  {n}/{len(companies)} looked up, {accepted} matched", file=sys.stderr)

    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"{accepted}/{len(rows)} companies matched on Wikidata -> {OUT}")
    for col in ["company_website", "city_hq", "office_address", "founded_year", "status"]:
        print(f"  {col}: {sum(1 for r in rows if r[col])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
