#!/usr/bin/env python3
"""Fetch open roles from public job-board APIs into web/src/data/jobs.json (+ jobs-summary.json).

Only public, documented job-board endpoints are used (Greenhouse, Lever, Ashby); these are
published by the companies themselves for exactly this purpose. Nothing about people is fetched.

Which board belongs to which company lives in data/ats_boards.json:
    { "<company id>": {"ats": "greenhouse", "slug": "acme", "source": "careers link"} }
Set a company to null to block it (for example a wrongly detected board). Edit by hand freely.

Run:
    python3 -I scripts/fetch_jobs.py --detect   # look for boards, then fetch roles
    python3 -I scripts/fetch_jobs.py            # fetch roles for known boards only

--detect only adds companies that are not in ats_boards.json yet. It reads each company's careers
link and, if needed, the careers page, homepage and /careers page, looking for links to a job
board. It never guesses slugs from company names, because a guessed slug can belong to another
company with the same name.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPANIES = ROOT / "web" / "src" / "data" / "companies.json"
BOARDS = ROOT / "data" / "ats_boards.json"
OUT = ROOT / "web" / "src" / "data" / "jobs.json"
# Role counts and board links only: small enough for the map app's main bundle. The full role
# lists in jobs.json are loaded on demand when a company is opened.
SUMMARY = ROOT / "web" / "src" / "data" / "jobs-summary.json"
UA = "bitsians-map-jobs/1.0 (+https://bitsians-map.whyujjwalraj.workers.dev)"
TIMEOUT = 20

# Links to a job board on a careers page or in a careers URL. Group "slug" is the board name.
BOARD_PATTERNS = [
    ("greenhouse", r"(?:job-)?boards(?:\.eu)?\.greenhouse\.io/(?:embed/job_board(?:/js)?\?for=)?(?P<slug>[A-Za-z0-9_-]+)"),
    ("greenhouse", r"boards-api\.greenhouse\.io/v1/boards/(?P<slug>[A-Za-z0-9_-]+)"),
    ("lever", r"jobs\.lever\.co/(?P<slug>[A-Za-z0-9._-]+)"),
    ("lever", r"api\.lever\.co/v0/postings/(?P<slug>[A-Za-z0-9._-]+)"),
    ("ashby", r"jobs\.ashbyhq\.com/(?P<slug>[A-Za-z0-9._%-]+)"),
    ("ashby", r"api\.ashbyhq\.com/posting-api/job-board/(?P<slug>[A-Za-z0-9._%-]+)"),
]
# Boards we can recognise but not read (no public API). Reported so they can be handled later.
OTHER_BOARDS = r"([a-z0-9-]+\.keka\.com|[a-z0-9-]+\.darwinbox\.in|apply\.workable\.com/[a-z0-9-]+|" \
               r"[a-z0-9-]+\.zohorecruit\.(?:com|in)|careers\.smartrecruiters\.com/[A-Za-z0-9-]+|" \
               r"[a-z0-9-]+\.recruitee\.com|[a-z0-9-]+\.freshteam\.com|[a-z0-9-]+\.myworkdayjobs\.com)"
SLUG_BLOCK = {"embed", "js", "v1", "api", "jobs", "search", "privacy", "static", "assets"}


def get(url: str, accept: str = "*/*") -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read(3_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def get_json(url: str):
    status, body = get(url, "application/json")
    if status != 200:
        return None
    try:
        return json.loads(body)
    except ValueError:
        return None


# ---- Reading boards -------------------------------------------------------------------------

def clean(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def read_greenhouse(slug: str):
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/departments")
    if data is None:
        return None
    jobs, seen = [], set()
    for d in data.get("departments", []):
        team = "" if d.get("name") in (None, "No Department") else clean(d["name"])
        for j in d.get("jobs", []):
            if j["id"] in seen:
                continue
            seen.add(j["id"])
            jobs.append({"title": clean(j.get("title")), "team": team,
                         "location": clean((j.get("location") or {}).get("name")), "url": j.get("absolute_url", "")})
    return {"board": f"https://job-boards.greenhouse.io/{slug}", "jobs": jobs}


def read_lever(slug: str):
    for host in ("api.lever.co", "api.eu.lever.co"):
        data = get_json(f"https://{host}/v0/postings/{slug}?mode=json")
        if isinstance(data, list):
            board = f"https://jobs.{'eu.' if 'eu' in host else ''}lever.co/{slug}"
            jobs = [{"title": clean(j.get("text")), "team": clean((j.get("categories") or {}).get("team")),
                     "location": clean((j.get("categories") or {}).get("location")), "url": j.get("hostedUrl", "")}
                    for j in data]
            return {"board": board, "jobs": jobs}
    return None


def read_ashby(slug: str):
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{urllib.parse.quote(slug)}")
    if data is None or "jobs" not in data:
        return None
    jobs = [{"title": clean(j.get("title")), "team": clean(j.get("team") or j.get("department")),
             "location": clean(j.get("location")), "url": j.get("jobUrl", "")}
            for j in data["jobs"] if j.get("isListed", True)]
    return {"board": f"https://jobs.ashbyhq.com/{slug}", "jobs": jobs}


READERS = {"greenhouse": read_greenhouse, "lever": read_lever, "ashby": read_ashby}


# ---- Detecting boards ------------------------------------------------------------------------

def find_boards(text: str) -> list[tuple[str, str]]:
    found = []
    for ats, pat in BOARD_PATTERNS:
        for m in re.finditer(pat, text):
            slug = urllib.parse.unquote(m.group("slug")).rstrip(".")
            if slug.lower() not in SLUG_BLOCK and (ats, slug) not in found:
                found.append((ats, slug))
    return found


def detect(c: dict) -> dict:
    """Returns {"board": {...} | None, "other": [hosts], "checked": [urls]}."""
    careers, website = c.get("careers") or "", c.get("website") or ""
    candidates = []  # (ats, slug, source)
    for ats, slug in find_boards(careers):
        candidates.append((ats, slug, "careers link"))
    other, checked = set(re.findall(OTHER_BOARDS, careers.lower())), []
    if not candidates:
        pages = [careers] if careers else []
        if website:
            base = website.rstrip("/")
            pages += [base, base + "/careers"]
        for url in dict.fromkeys(pages):
            status, html = get(url, "text/html")
            checked.append(f"{url} ({status or 'error'})")
            if status != 200:
                continue
            for ats, slug in find_boards(html):
                candidates.append((ats, slug, f"linked from {url}"))
            other |= set(re.findall(OTHER_BOARDS, html.lower()))
            if candidates:
                break
    for ats, slug, source in candidates:
        res = READERS[ats](slug)
        if res is not None:
            return {"board": {"ats": ats, "slug": slug, "source": source}, "other": sorted(other), "checked": checked}
    return {"board": None, "other": sorted(other), "checked": checked}


# ---- Main -------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--detect", action="store_true", help="look for job boards for companies not in ats_boards.json")
    args = ap.parse_args()

    companies = {c["id"]: c for c in json.loads(COMPANIES.read_text())}
    boards = json.loads(BOARDS.read_text()) if BOARDS.exists() else {}

    if args.detect:
        todo = [c for cid, c in companies.items() if cid not in boards and (c.get("careers") or c.get("website"))]
        print(f"Looking for job boards for {len(todo)} companies…", file=sys.stderr)
        others = {}
        with cf.ThreadPoolExecutor(8) as ex:
            for c, r in zip(todo, ex.map(detect, todo)):
                if r["board"]:
                    boards[c["id"]] = r["board"]
                    print(f"  + {c['name']}: {r['board']['ats']}/{r['board']['slug']} ({r['board']['source']})", file=sys.stderr)
                elif r["other"]:
                    others[c["name"]] = r["other"]
        if others:
            print("Boards without a public API (not read):", file=sys.stderr)
            for name, hosts in sorted(others.items()):
                print(f"  - {name}: {', '.join(hosts)}", file=sys.stderr)
        BOARDS.write_text(json.dumps(dict(sorted(boards.items())), indent=2) + "\n")

    known = {cid: b for cid, b in boards.items() if b and cid in companies}
    print(f"Fetching roles from {len(known)} boards…", file=sys.stderr)
    out, failed = {}, []

    def fetch(item):
        cid, b = item
        return cid, b, READERS[b["ats"]](b["slug"])

    with cf.ThreadPoolExecutor(8) as ex:
        for cid, b, res in ex.map(fetch, sorted(known.items())):
            if res is None:
                failed.append(f"{companies[cid]['name']} ({b['ats']}/{b['slug']})")
                continue
            jobs = sorted((j for j in res["jobs"] if j["title"] and j["url"].startswith("https://")),
                          key=lambda j: (j["team"] == "", j["team"].lower(), j["title"].lower()))
            out[cid] = {"ats": b["ats"], "board": res["board"], "jobs": jobs}
            print(f"  {companies[cid]['name']}: {len(jobs)} roles", file=sys.stderr)

    fetched = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.write_text(json.dumps({"fetchedAt": fetched, "companies": out}, ensure_ascii=False, separators=(",", ":")) + "\n")
    summary = {cid: {"ats": v["ats"], "board": v["board"], "n": len(v["jobs"])} for cid, v in out.items()}
    SUMMARY.write_text(json.dumps({"fetchedAt": fetched, "companies": summary}, indent=1) + "\n")
    total = sum(len(v["jobs"]) for v in out.values())
    print(f"Wrote {OUT.relative_to(ROOT)}: {total} roles at {len(out)} companies.", file=sys.stderr)
    if failed:
        print("Could not read (kept out of jobs.json): " + "; ".join(failed), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
