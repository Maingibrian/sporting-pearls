#!/usr/bin/env python3
"""P8 audit — map every gap the polish round must fix.

Read-only. Reports per page: lang, viewport, favicon, description (+len),
canonical, OG tags, lazy images, eyebrow numbering, plus targeted greps.
"""
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"

PAGES = sorted(p.name for p in SITE.glob("*.html"))
FORM_PAGES = {f"form-{n:02d}-{t}.html" for n, t in [
    (1, "player-registration"), (2, "trial-application"), (3, "parent-association"),
    (4, "volunteer-application"), (5, "coach-technical-staff"),
    (6, "sponsorship-partnership"), (7, "donation-support"),
    (8, "contact-form"), (9, "media-photo-consent"), (10, "safeguarding-report"),
]}
ERR_PAGES = {"404.html", "50x.html"}


def get(tag_re, html):
    m = re.search(tag_re, html, re.I | re.S)
    return m.group(0) if m else None


rows = []
for name in PAGES:
    html = (SITE / name).read_text(encoding="utf-8")
    head = html[:html.find("</head>")] if "</head>" in html else html
    r = {"page": name}
    r["lang"] = bool(re.search(r"<html[^>]*\blang=", html, re.I))
    r["viewport"] = bool(re.search(r'<meta[^>]+name=["\']viewport', head, re.I))
    r["favicon"] = bool(re.search(r'<link[^>]+rel=["\'][^"\']*icon', head, re.I))
    d = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']', head, re.I)
    if not d:
        d = re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']description["\']', head, re.I)
    r["desc_len"] = len(d.group(1)) if d else 0
    r["canonical"] = bool(re.search(r'<link[^>]+rel=["\']canonical', head, re.I))
    r["og"] = len(re.findall(r'<meta[^>]+property=["\']og:', head, re.I))
    # images (skip inline svg/data URIs)
    imgs = re.findall(r"<img\b[^>]*>", html, re.I)
    lazy = [t for t in imgs if 'loading="lazy"' in t or "loading='lazy'" in t]
    eager = [t for t in imgs if "loading=" not in t]
    r["imgs"] = len(imgs); r["lazy"] = len(lazy); r["eager"] = len(eager)
    r["eager_srcs"] = [re.search(r'src="([^"]+)"', t).group(1) if re.search(r'src="([^"]+)"', t) else "?" for t in eager]
    # numbered eyebrows in document order
    eyes = re.findall(r'class="eyebrow"[^>]*>\s*(?:<[^>]+>\s*)?(\d{2})\b[^<]*', html)
    r["eyebrows"] = eyes
    rows.append(r)

print(f"{'page':44} {'lang':4} {'vw':3} {'fav':3} {'dlen':4} {'canon':5} {'og':2} {'img/lz/eg':9}  eyebrows")
for r in rows:
    print(f"{r['page']:44} {str(r['lang'])[0]:4} {str(r['viewport'])[0]:3} {str(r['favicon'])[0]:3} "
          f"{r['desc_len']:<4} {str(r['canonical'])[0]:5} {r['og']:<2} {r['imgs']}/{r['lazy']}/{r['eager']:<2}       {','.join(r['eyebrows'])}")

print("\n=== EAGER (no loading attr) image sources per page ===")
for r in rows:
    if r["eager_srcs"]:
        print(f"{r['page']}: {r['eager_srcs']}")

print("\n=== targeted greps ===")
pats = {
    "Seven commitments": r"[Ss]even\s+commitments",
    "commitments (any count)": r"\b(\w+)\s+commitments\b",
    "development areas": r"\b(\w+)\s+development\s+areas\b",
    "Five gateways": r"[Ff]ive\s+gateways",
    "Building The Future Together": r"Building\s+The\s+Future\s+Together",
    "2020 · Serving the community": r"2020\s*[·&]\s*Serving\s+the\s+community",
    "Since 2020 (hero labels)": r"[Ss]ince\s+2020",
}
for label, pat in pats.items():
    print(f"\n-- {label} --")
    for name in PAGES:
        html = (SITE / name).read_text(encoding="utf-8")
        for m in re.finditer(pat, html):
            ctx = html[max(0, m.start() - 90):m.end() + 90].replace("\n", " ")
            print(f"  {name}: …{ctx}…")

print("\n-- Mtwapa / Kilifi mentions (first 3 per page) --")
for name in PAGES:
    html = (SITE / name).read_text(encoding="utf-8")
    ms = list(re.finditer(r"[Mm]twapa|[Kk]ilifi", html))
    if ms:
        shown = []
        for m in ms[:4]:
            ctx = re.sub(r"\s+", " ", html[max(0, m.start() - 55):m.end() + 55])
            shown.append(f"[{m.start()}]…{ctx}…")
        print(f"  {name} ({len(ms)} total): " + " | ".join(shown))
