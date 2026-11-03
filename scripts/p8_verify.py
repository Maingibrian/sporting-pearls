#!/usr/bin/env python3
"""P8 verify — static checks after the polish round.

 1. tag balance on every page (HTMLParser)
 2. every local href/src resolves (no 404 assets / broken links)
 3. CSP hygiene: no inline event handlers in HTML
 4. canonical + OG present on public pages, absent on 404/50x
 5. descriptions: unique, < 160 chars
 6. lazy-loading coverage; hero/nav/preloader still eager
 7. CSS brace balance on every stylesheet (files + inline)
 8. robots.txt + sitemap.xml exist and agree
 9. enquiry policy: no emails / phones / social links in visible text
10. join-us forms hub structure (6 main cards + 4 other cards)

Run from the kit root:  python3 scripts/p8_verify.py
"""
import re
import sys
import xml.dom.minidom
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DOMAIN = "https://www.sportingpearlsacademy.org"
ERR_PAGES = {"404.html", "50x.html"}
PAGES = sorted(p.name for p in SITE.glob("*.html"))
fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(label)


class Balance(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
            "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack:
            self.errors.append(f"stray </{tag}>")
            return
        if self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            self.errors.append(f"mismatched </{tag}> (top is {self.stack[-1]})")
            while self.stack and self.stack[-1] != tag:
                self.stack.pop()
            if self.stack:
                self.stack.pop()
        else:
            self.errors.append(f"unopened </{tag}>")


print("== 1. tag balance ==")
for name in PAGES:
    b = Balance()
    b.feed((SITE / name).read_text(encoding="utf-8"))
    leftovers = [t for t in b.stack if t not in ("html", "body")]
    ok = not b.errors and not leftovers
    if not ok:
        check(f"tag balance {name}", False, f"{b.errors[:3]} open={leftovers[:5]}")
if not fails:
    print(f"  PASS  tag balance on {len(PAGES)} pages")

print("\n== 2. local links resolve ==")
bad = []
for name in PAGES:
    html = (SITE / name).read_text(encoding="utf-8")
    for m in re.finditer(r'(?:href|src)="([^"]+)"', html):
        u = m.group(1)
        if u.startswith(("http", "#", "data:", "mailto:", "tel:", "javascript:")):
            continue
        path = unquote(urlparse(u).path.split("#")[0].split("?")[0])
        if not path:
            continue
        if not (SITE / path).exists():
            bad.append(f"{name}: {u}")
check("all local href/src resolve", not bad, "; ".join(bad[:6]))

print("\n== 3. CSP hygiene (no inline handlers) ==")
hits = []
for name in PAGES:
    html = (SITE / name).read_text(encoding="utf-8")
    for m in re.finditer(r"\son(click|error|load|change|input|submit|mouseover)=", html, re.I):
        hits.append(f"{name}: {m.group(0)}")
check("no inline event handlers", not hits, "; ".join(hits[:4]))

print("\n== 4. canonical + OG on public pages ==")
bad = []
for name in PAGES:
    if name in ERR_PAGES:
        continue
    html = (SITE / name).read_text(encoding="utf-8")
    head = html[:html.find("</head>")]
    for needle in ('rel="canonical"', 'property="og:title"', 'property="og:description"',
                   'property="og:image"', 'property="og:type"', 'property="og:url"'):
        if needle not in head:
            bad.append(f"{name}: missing {needle}")
    url = f"{DOMAIN}/{'' if name == 'index.html' else name}"
    if f'href="{url}"' not in head:
        bad.append(f"{name}: canonical href wrong")
check("canonical + 5 OG tags on all 39 public pages", not bad, "; ".join(bad[:5]))
err_ok = all('rel="canonical"' not in (SITE / n).read_text(encoding="utf-8") for n in ERR_PAGES)
check("404/50x carry no canonical (error documents)", err_ok)

print("\n== 5. descriptions unique and < 160 ==")
descs = {}
for name in PAGES:
    if name in ERR_PAGES:
        continue
    html = (SITE / name).read_text(encoding="utf-8")
    m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
    assert m, name
    descs[name] = m.group(1)
over = [f"{k}({len(v)})" for k, v in descs.items() if len(v) >= 160]
dupes = {v for v in descs.values() if list(descs.values()).count(v) > 1}
check("all descriptions < 160 chars", not over, ", ".join(over))
check("all descriptions unique", not dupes, str(list(dupes)[:2]))

print("\n== 6. lazy loading ==")
n_lazy = n_eager = 0
for name in PAGES:
    html = (SITE / name).read_text(encoding="utf-8")
    n_lazy += html.count('loading="lazy"')
    hero = re.search(r'<(section|header)\s+class="hero[^"]*"[^>]*>.*?</\1>', html, re.S)
    himg = re.findall(r"<img\b[^>]*>", hero.group(0)) if hero else []
    if any("loading=" in t for t in himg):
        check(f"hero image not lazy-loaded {name}", False)
    n_eager += len(himg)
check(f"lazy coverage ({n_lazy} lazy attrs; {n_eager} hero images eager)", n_lazy >= 140)

print("\n== 7. CSS brace balance ==")
bad = []
for p in sorted((SITE / "assets/css").rglob("*.css")):
    css = p.read_text(encoding="utf-8")
    if css.count("{") != css.count("}"):
        bad.append(f"{p.name}: {css.count('{')}{{ vs {css.count('}')}}}")
for name in PAGES:
    html = (SITE / name).read_text(encoding="utf-8")
    for sm in re.finditer(r"<style[^>]*>(.*?)</style>", html, re.S):
        css = sm.group(1)
        if css.count("{") != css.count("}"):
            bad.append(f"{name} inline: {css.count('{')}{{ vs {css.count('}')}}}")
check("brace balance in all stylesheets + inline styles", not bad, "; ".join(bad[:4]))

print("\n== 8. robots + sitemap ==")
robots = (SITE / "robots.txt").read_text(encoding="utf-8")
for line in ["Disallow: /portal/", "Disallow: /admin/", "Disallow: /api/", "Disallow: /media/",
             f"Sitemap: {DOMAIN}/sitemap.xml"]:
    check(f"robots.txt: {line}", line in robots)
xml.dom.minidom.parse(str(SITE / "sitemap.xml"))
locs = re.findall(r"<loc>([^<]+)</loc>", (SITE / "sitemap.xml").read_text(encoding="utf-8"))
check("sitemap parses; 23 URLs; all on placeholder domain",
      len(locs) == 23 and all(l.startswith(DOMAIN) for l in locs))
excluded = [f for f in PAGES if f not in {l.replace(DOMAIN + "/", "") or "index.html" for l in locs}
            and f not in ERR_PAGES]
must_be_excluded = {p.name for p in SITE.glob("form-*.html")} | {
    "policy-data-privacy.html", "policy-player-parent-code.html",
    "policy-coach-volunteer-code.html", "policy-safeguarding-child-protection.html",
    "portal-guide.html", "player.html"}
unexpected = [f for f in excluded if f not in must_be_excluded]
check("sitemap exclusions = forms + policies + portal-guide + player only", not unexpected, str(unexpected))

print("\n== 9. enquiry policy (no contact info in visible text) ==")
SOCIAL = ("facebook.com", "twitter.com", "x.com", "instagram.com", "tiktok.com",
          "youtube.com", "whatsapp.com", "wa.me", "linkedin.com", "t.me")
viol = []
for name in PAGES:
    html = (SITE / name).read_text(encoding="utf-8")
    body = html[html.find("<body"):] if "<body" in html else html
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    for m in re.finditer(r"[\w.+-]+@[\w-]+\.[\w.]+", text):
        viol.append(f"{name}: email {m.group(0)}")
    for m in re.finditer(r"(?:tel:|\+254|\b07\d{8}\b|\b2547\d{8}\b)", text):
        viol.append(f"{name}: phone {m.group(0)}")
    for s in SOCIAL:
        if s in text.lower():
            viol.append(f"{name}: social {s}")
    for m in re.finditer(r'(?:href|src)="(mailto:|tel:|https?://[^"]*(?:' + "|".join(SOCIAL) + r')[^"]*)"', body, re.I):
        viol.append(f"{name}: link {m.group(1)[:40]}")
check("no emails / phone numbers / social links on any page", not viol, "; ".join(viol[:6]))

print("\n== 10. join-us forms hub ==")
ju = (SITE / "join-us.html").read_text(encoding="utf-8")
gw_cards = len(re.findall(r'class="gw-card"', ju))
strip_cards = len(re.findall(r'class="s-card"', ju))
forms = {f"form-{n:02d}" in ju for n in range(1, 11)}
check("6 main pathway cards (01-06)", gw_cards == 6, str(gw_cards))
check("4 other-form cards (07-10)", strip_cards == 4, str(strip_cards))
check("all ten form links present", all(forms))
check("'Ten gateways' heading", "Ten gateways." in ju)
check("group labels present", "Main Pathways" in ju and "Other Forms" in ju)
check("hero stat 6 pathways", '<span data-count="6">0</span></b><span>Onboarding Pathways</span>' in ju)

print(f"\n{'ALL STATIC CHECKS PASS' if not fails else f'{len(fails)} FAILURES: ' + '; '.join(fails[:8])}")
sys.exit(1 if fails else 0)
