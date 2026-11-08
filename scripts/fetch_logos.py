#!/usr/bin/env python3
"""Collect a clean 128x128 square PNG logo per company for the BITSians Startup Map.

Run:  python3 -I scripts/fetch_logos.py

Reads  data/companies.csv (+ data/bitsians.csv for missing websites)
Writes web/public/logos/<slug>.png and data/logos/manifest.csv
Raw downloads (untrusted, never executed) go to RAW_DIR outside the repo.

Order per site: apple-touch-icon, <link rel=icon>, web manifest icons,
/favicon.ico; then DuckDuckGo / Google favicon services as a fallback.
If a homepage answers 403/406/429/captcha we do NOT work around it: we only
use the public icon services for that site.
SVGs are never published; they are rasterised locally with macOS qlmanage.
"""
import csv
import hashlib
import io
import ipaddress
import json
import re
import socket
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from PIL import Image, ImageStat

ROOT = Path("/Users/ujjwalraj/Developer/bitsiansmap")
RAW_DIR = Path("/private/tmp/claude-501/-Users-ujjwalraj--claude-spares-spare-AA3iog/"
               "ede3d031-6503-4c8d-b563-cd8bdb9c5b00/scratchpad/logos-raw")
OUT_DIR = ROOT / "web/public/logos"
MANIFEST = ROOT / "data/logos/manifest.csv"
WORKERS = 8
TIMEOUT = 10
MAX_BYTES = 5_000_000
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
           "Accept-Language": "en-US,en;q=0.9"}
IMG_HEADERS = {"User-Agent": UA, "Accept": "image/*,*/*;q=0.8"}

NOT_OWN = ("harmonic.ai", "forms.gle", "webflow.io", "linkedin.com", "google.com",
           "docs.google.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
           "wixsite.com", "github.io", "notion.site", "carrd.co", "wordpress.com",
           "blogspot.com", "medium.com", "crunchbase.com", "youtube.com")
# sites whose own favicons are the generic icons that other sites inherit by default
BUILDER_DOMAINS = ("wix.com", "squarespace.com", "godaddy.com", "wordpress.org",
                   "wordpress.com", "cloudflare.com", "vercel.com", "weebly.com",
                   "webflow.com", "hostinger.com", "namecheap.com", "netlify.com",
                   "framer.com", "sedo.com", "bluehost.com", "hostgator.com",
                   "dreamhost.com", "ionos.com", "strikingly.com", "jimdo.com",
                   "carrd.co", "nginx.org", "apache.org")
PLACEHOLDER_PROBES = ("zzq-no-such-site-81723.com", "qqxv-unknown-4410.net")

# Manual visual-QA rejections (checked on contact sheets): icon returned is not the company's logo.
REJECT_OVERRIDES = {
    "Mumbai Angels": "wrong-company",  # site is Cloudflare-blocked; Google's cached icon is an unrelated "SCB" sign
}

lock = threading.Lock()


# ---------- helpers ----------
def slugify(name):
    name = re.sub(r"\([^)]*\)", " ", name).lower()
    return re.sub(r"[^a-z0-9]+", "-", name).strip("-")


def public_host(host):
    try:
        for fam, _, _, _, sa in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(sa[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        return True
    except Exception:
        return False


def get(url, headers, session=None, max_bytes=MAX_BYTES):
    """GET with size cap; returns (status, final_url, content_type, bytes) or raises."""
    host = urlparse(url).hostname or ""
    if not public_host(host):
        raise ValueError("non-public host")
    s = session or requests
    r = s.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True, stream=True)
    try:
        if not public_host(urlparse(r.url).hostname or ""):
            raise ValueError("redirect to non-public host")
        buf = bytearray()
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > max_bytes:
                break
        return r.status_code, r.url, r.headers.get("Content-Type", ""), bytes(buf)
    finally:
        r.close()


def parse_sizes(s):
    best = 0
    for m in re.finditer(r"(\d+)\s*[xX]\s*(\d+)", s or ""):
        best = max(best, int(m.group(1)))
    return best


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.base = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "base" and a.get("href") and not self.base:
            self.base = a["href"]
        if tag == "link" and a.get("href"):
            self.links.append(a)


def is_svg(data, ctype="", url=""):
    head = data[:600].lstrip().lower()
    return ("svg" in ctype.lower() or url.lower().split("?")[0].endswith(".svg")
            or head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in data[:2000].lower()))


# ---------- image processing ----------
def rasterize_svg(path, outdir):
    """Render an SVG with qlmanage into outdir; return PNG path or None."""
    outdir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["/usr/bin/qlmanage", "-t", "-s", "256", "-o", str(outdir), str(path)],
                       cwd="/", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    except Exception:
        return None
    out = outdir / (Path(path).name + ".png")
    return out if out.exists() and out.stat().st_size > 0 else None


def load_raster(data):
    Image.MAX_IMAGE_PIXELS = 40_000_000
    im = Image.open(io.BytesIO(data))
    im.load()
    return im.convert("RGBA")


def tidy_svg_raster(im):
    """qlmanage output is on an opaque white page; make near-white background transparent
    only when the border is uniformly white."""
    px = im.load()
    w, h = im.size
    edge = [px[x, 0] for x in range(0, w, 8)] + [px[x, h - 1] for x in range(0, w, 8)] + \
           [px[0, y] for y in range(0, h, 8)] + [px[w - 1, y] for y in range(0, h, 8)]
    if all(p[3] == 255 and min(p[:3]) >= 250 for p in edge):
        out = Image.new("RGBA", im.size)
        out.putdata([(r, g, b, 0) if min(r, g, b) >= 250 else (r, g, b, 255)
                     for r, g, b, a in im.getdata()])
        return out
    return im


def process(im):
    """Square-pad (10% margin, transparent) and resize to 128x128. Returns clean RGBA."""
    w, h = im.size
    inner = 102  # 128 * 0.8 -> 10% margin per side
    scale = inner / max(w, h)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    small = im.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    canvas.paste(small, ((128 - nw) // 2, (128 - nh) // 2), small)
    clean = Image.new("RGBA", canvas.size)  # fresh image => no metadata
    clean.putdata(list(canvas.getdata()))
    return clean


def dhash(img):
    g = Image.new("RGB", img.size, "white")
    g.paste(img, mask=img.split()[3])
    g = g.convert("L").resize((9, 8), Image.LANCZOS)
    p = list(g.getdata())
    bits = 0
    for r in range(8):
        for c in range(8):
            bits = (bits << 1) | (p[r * 9 + c] > p[r * 9 + c + 1])
    return bits


def ham(a, b):
    return bin(a ^ b).count("1")


def analyse(img, orig):
    """Return (blank, light) for a processed 128 image. `light` = genuinely transparent
    original whose visible pixels are near-white (would vanish on a white page)."""
    rgba = img
    a = rgba.split()[3]
    opaque = [i for i, v in enumerate(a.getdata()) if v > 40]
    if len(opaque) < 120:
        return True, False
    px = list(rgba.getdata())
    cols = [px[i][:3] for i in opaque]
    # on-white view for blankness
    flat = Image.new("RGB", rgba.size, "white")
    flat.paste(rgba, mask=a)
    st = ImageStat.Stat(flat)
    if max(st.stddev) < 6:
        return True, False
    lum = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in cols) / len(cols)
    oa = list(orig.split()[3].getdata())
    transparent_frac = sum(1 for v in oa if v < 20) / len(oa)
    light = lum > 215 and transparent_frac > 0.15
    return False, light


# ---------- candidate discovery ----------
def site_candidates(session, home_url, html, final_url):
    cands = []
    p = LinkParser()
    try:
        p.feed(html)
    except Exception:
        pass
    base = urljoin(final_url, p.base) if p.base else final_url
    manifest_url = None
    for a in p.links:
        rel = (a.get("rel") or "").lower().split()
        href = a["href"].strip()
        if href.startswith("data:"):
            continue
        url = urljoin(base, href)
        if urlparse(url).scheme not in ("http", "https"):
            continue
        sz = parse_sizes(a.get("sizes"))
        typ = (a.get("type") or "").lower()
        if "apple-touch-icon" in rel or "apple-touch-icon-precomposed" in rel:
            cands.append(("apple-touch", url, sz or 180))
        elif "icon" in rel or "shortcut" in rel:
            svg = "svg" in typ or url.lower().split("?")[0].endswith(".svg")
            cands.append(("icon", url, 64 if svg else (sz or 32)))
        elif "manifest" in rel and not manifest_url:
            manifest_url = url
    if manifest_url:
        try:
            st, murl, _, data = get(manifest_url, HEADERS, session, 500_000)
            if st == 200:
                for ic in json.loads(data.decode("utf-8", "replace")).get("icons", []):
                    if not isinstance(ic, dict) or not ic.get("src"):
                        continue
                    u = urljoin(murl, ic["src"])
                    sz = parse_sizes(ic.get("sizes"))
                    if "svg" in (ic.get("type") or "") or u.lower().split("?")[0].endswith(".svg"):
                        sz = 64
                    if "maskable" in (ic.get("purpose") or "") and "any" not in (ic.get("purpose") or ""):
                        sz = max(0, sz - 40)  # maskable icons carry extra safe-zone padding
                    cands.append(("manifest", u, sz or 48))
        except Exception:
            pass
    root = f"{urlparse(final_url).scheme}://{urlparse(final_url).netloc}"
    cands.append(("favicon", root + "/favicon.ico", 32))
    prio = {"apple-touch": 3, "manifest": 2, "icon": 1, "favicon": 0}
    seen, out = set(), []
    for c in sorted(cands, key=lambda c: (-c[2], -prio[c[0]])):
        if c[1] not in seen:
            seen.add(c[1])
            out.append(c)
    return out[:6]


# ---------- per-company pipeline ----------
class Result:
    def __init__(self, name, website):
        self.name, self.website = name, website
        self.file = self.source_url = self.source_kind = ""
        self.source_px = self.bytes = ""
        self.status = "none"


def fetch_image(url, rawdir, idx, session=None, headers=IMG_HEADERS):
    """Download and decode one candidate. Returns (RGBA image, px) or raises ValueError(reason)."""
    st, final, ctype, data = get(url, headers, session)
    if st != 200 or not data:
        raise ValueError(f"http-{st}")
    if "text/html" in ctype.lower() and not is_svg(data, ctype, url):
        raise ValueError("html-not-image")
    rawdir.mkdir(parents=True, exist_ok=True)
    if is_svg(data, ctype, url):
        raw = rawdir / f"cand{idx}.svg"
        raw.write_bytes(data)
        png = rasterize_svg(raw, rawdir / f"ql{idx}")
        if not png:
            raise ValueError("svg-raster-failed")
        im = tidy_svg_raster(load_raster(png.read_bytes()))
        return im, 0, True
    raw = rawdir / f"cand{idx}.bin"
    raw.write_bytes(data)
    try:
        im = load_raster(data)
    except Exception:
        raise ValueError("undecodable")
    return im, max(im.size), False


def judge(im, bad_hashes):
    """Process + quality gates. Returns (processed, light) or raises ValueError(reason)."""
    proc = process(im)
    blank, light = analyse(proc, im)
    if blank:
        raise ValueError("blank")
    h = dhash(proc)
    for tag, bh in bad_hashes:
        if ham(h, bh) <= 4:
            raise ValueError(tag)
    return proc, light


def work(row, bad_hashes, rawroot):
    name, website = row
    res = Result(name, website)
    slug = slugify(name)
    rawdir = rawroot / slug
    host = (urlparse(website if "//" in website else "//" + website).hostname or "").lower()
    if not host or any(host == d or host.endswith("." + d) for d in NOT_OWN):
        res.status = "rejected:non-company-site"
        return res
    url = website if "//" in website else "https://" + website
    blocked = False
    reasons = []
    chosen = None  # (proc, light, kind, src, px)

    # --- 1. the site itself ---
    session = requests.Session()
    html = final = None
    pu = urlparse(url)
    alt_host = pu.netloc[4:] if pu.netloc.startswith("www.") else "www." + pu.netloc
    tries = [url, url.replace("https://", "http://", 1), pu._replace(netloc=alt_host).geturl()]
    for u in tries:
        if html is not None or blocked:
            break
        try:
            st, final, ctype, data = get(u, HEADERS, session, 1_500_000)
            body = data.decode("utf-8", "replace")
            if st in (403, 406, 429) or (st in (503,) and re.search(r"captcha|cf-chl|just a moment", body, re.I)):
                blocked = True
                break
            if st >= 400:
                reasons.append(f"home-http-{st}")
                continue
            if re.search(r"captcha|cf-chl-bypass|attention required", body[:5000], re.I) and "<link" not in body.lower():
                blocked = True
                break
            html = body
            break
        except Exception as e:
            reasons.append("home-" + type(e).__name__)
    if html is not None:
        for i, (kind, cu, declared) in enumerate(site_candidates(session, url, html, final)):
            try:
                im, px, svg = fetch_image(cu, rawdir, i, session)
                if not svg and px < 64:
                    raise ValueError(f"small-{px}px")
                proc, light = judge(im, bad_hashes)
                chosen = (proc, light, kind, cu, px or 256)
                break
            except Exception as e:
                reasons.append(str(e) if isinstance(e, ValueError) else type(e).__name__)

    # --- 2. public icon services (also used when the site blocks us) ---
    if not chosen:
        dom = host[4:] if host.startswith("www.") else host
        for kind, su in (("duckduckgo", f"https://icons.duckduckgo.com/ip3/{dom}.ico"),
                         ("google", f"https://www.google.com/s2/favicons?domain={dom}&sz=128")):
            try:
                im, px, svg = fetch_image(su, rawdir, "_" + kind)
                if px < 48:
                    raise ValueError(f"small-{px}px")
                proc, light = judge(im, bad_hashes)
                chosen = (proc, light, kind, su, px)
                break
            except Exception as e:
                reasons.append(f"{kind}:" + (str(e) if isinstance(e, ValueError) else type(e).__name__))

    if not chosen:
        if blocked:
            res.status = "blocked"
        elif html is None:
            res.status = "none"
            res.source_url = ""
        else:
            sig = [r for r in reasons if r in ("blank",) or r.startswith(("generic", "small", "placeholder"))]
            res.status = f"rejected:{sig[0]}" if sig else "none"
        return res

    proc, light, kind, src, px = chosen
    if name in REJECT_OVERRIDES:
        res.status = "rejected:" + REJECT_OVERRIDES[name]
        return res
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{slug}.png"
    proc.save(out, "PNG", optimize=True)
    res.file = f"logos/{slug}.png"
    res.source_url, res.source_kind, res.source_px = src, kind, px
    res.bytes = out.stat().st_size
    res.status = "ok:light_logo" if light else "ok"
    return res


def build_blocklist():
    """Hashes of generic icons: service placeholders and website-builder/host favicons."""
    bad = []
    tmp = RAW_DIR / "_blocklist"
    for i, d in enumerate(PLACEHOLDER_PROBES):
        for tag, u in (("placeholder-ddg", f"https://icons.duckduckgo.com/ip3/{d}.ico"),
                       ("placeholder-google", f"https://www.google.com/s2/favicons?domain={d}&sz=128")):
            try:
                st, _, ct, data = get(u, IMG_HEADERS)
                if data:
                    bad.append((tag, dhash(process(load_raster(data)))))
            except Exception:
                pass
    for i, d in enumerate(BUILDER_DOMAINS):
        for u in (f"https://icons.duckduckgo.com/ip3/{d}.ico",
                  f"https://www.google.com/s2/favicons?domain={d}&sz=128"):
            try:
                st, _, ct, data = get(u, IMG_HEADERS)
                if st == 200 and data:
                    bad.append(("generic-builder", dhash(process(load_raster(data)))))
            except Exception:
                pass
    return bad


def main():
    companies = list(csv.DictReader(open(ROOT / "data/companies.csv", newline="")))
    bit = {}
    for r in csv.DictReader(open(ROOT / "data/bitsians.csv", newline="")):
        if r["company_website"].strip():
            bit.setdefault(r["company_name"], r["company_website"].strip())
    rows = []
    for c in companies:
        w = c["company_website"].strip() or bit.get(c["company_name"], "")
        if w:
            rows.append((c["company_name"], w))
    slugs = {}
    for n, _ in rows:
        slugs.setdefault(slugify(n), []).append(n)
    dup = {k: v for k, v in slugs.items() if len(v) > 1}
    if dup:
        print("WARNING slug collisions:", dup, file=sys.stderr)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.png"):
        old.unlink()
    bad = build_blocklist()
    print(f"{len(rows)} companies with websites; {len(bad)} blocklist hashes", flush=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        results = list(ex.map(lambda r: work(r, bad, RAW_DIR), rows))

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["company_name", "website", "file", "source_url", "source_kind",
                    "source_px", "bytes", "status"])
        for r in sorted(results, key=lambda r: r.name.lower()):
            w.writerow([r.name, r.website, r.file, r.source_url, r.source_kind,
                        r.source_px, r.bytes, r.status])
    ok = sum(r.status.startswith("ok") for r in results)
    print(f"done: {ok}/{len(results)} logos")


if __name__ == "__main__":
    main()
