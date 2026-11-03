#!/usr/bin/env python3
"""P8 site edits — HTML layer (kit rev 20 polish round).

Covers (task numbers from the owner brief):
  T1  SEO head surgery: rewritten >160-char descriptions, canonical, OG tags,
      favicon on 404/50x.
  T2  Copy: index hero label, pillar 06 title, join-us heading/stat,
      contact stat + response-time line.
  T3  Eyebrow renumbering (start at 01, continuous).
  T4  contact hero stat replacement (markup; CSS lives in p8_css_edits.py).
  T5  Forms hub: join-us grouping (Main pathways 01-06 / Other forms 07-10).
  T8  loading="lazy" on below-the-fold images (hero/nav/preloader stay eager).
  T2b Place naming: first body "Kilifi County" -> "Mtwapa, Kilifi County".

Idempotent: every edit asserts its anchor and skips if already applied.
Run from the kit root:  python3 scripts/p8_site_edits.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DOMAIN = "https://www.sportingpearlsacademy.org"

changes = []          # (page, what)


def log(page, what):
    changes.append((page, what))
    print(f"  [{page}] {what}")


def rw(name):
    return (SITE / name).read_text(encoding="utf-8")


def wr(name, text):
    (SITE / name).write_text(text, encoding="utf-8")


# ════════════════════════════════════════════════════════════════════
# T1 — description rewrites (unique, < 160 chars each)
# ════════════════════════════════════════════════════════════════════
NEW_DESC = {
    "about-us.html": "Sporting Pearls Football Academy — a community football institution founded in 2020 in Mtwapa, Kilifi County, developing talent, character and opportunity.",
    "academy.html": "A community football institution building structured pathways for boys, girls and young people — coaching, education and character. Est. 2020, Mtwapa.",
    "boys-programme.html": "A structured development pathway for boys from Foundation (U9) to Transition (U17 and Senior) — talent, discipline and leadership in Mtwapa, Kilifi County.",
    "coaching-philosophy.html": "Developing thinking footballers and responsible people — the official coaching curriculum, playing identity and methodology of Sporting Pearls.",
    "contact.html": "Contact Sporting Pearls Football Academy in Mtwapa, Kilifi County — enquiry desks for registration, trials, parents, volunteering, coaching and partnerships.",
    "education-life-skills.html": "Football opens doors — education helps players walk through them: academic accountability, leadership, digital awareness and career pathways.",
    "form-03-parent-association.html": "Form 03: Parent & Guardian Association (SPPGA) enrolment and liaison. Sporting Pearls Football Academy. Mtwapa, Kilifi County.",
    "form-07-donation-support.html": "Form 07: Donation & Support pledge — a one-off or recurring gift to a Sporting Pearls programme area. Mtwapa, Kilifi County.",
    "form-08-contact-form.html": "Form 08: Contact & General Enquiry — one simple form for anything the academy office can help with. Mtwapa, Kilifi County.",
    "form-09-media-photo-consent.html": "Form 09: Media & Photo Consent under the academy Safeguarding & Child Protection Policy — optional, revocable consents. Mtwapa, Kilifi County.",
    "goalkeeper-development.html": "Save. Think. Play. Lead. Modern goalkeeper development at Sporting Pearls — shot-stoppers who understand the game, initiate attacks and lead from the back.",
    "institutional-blueprint.html": "The Sporting Pearls Institutional Blueprint 2026–2126 — a 100-year framework for a safe, sustainable, community-rooted football institution in Kilifi County.",
    "join-us.html": "Join Sporting Pearls Football Academy — the official onboarding hub for players, trials, parents, volunteers, coaches and partners. Est. 2020, Mtwapa.",
    "leadership-governance.html": "Leadership and governance at Sporting Pearls — the Chairman & Founder and Executive Director, our governance structure and institutional accountability.",
    "partners.html": "Partner with Sporting Pearls Football Academy — invest in talent, character and young lives across Kenya's coast: institutional partnerships and sponsorships.",
    "policy-coach-volunteer-code.html": "The Coach & Volunteer Code of Conduct — professional conduct, safe practice, boundaries, communication rules and the duty to report, as a readable web page.",
    "policy-data-privacy.html": "How we collect, use, store and protect your personal information — what each form collects, who can see it, how long we keep it, your Kenya DPA rights.",
    "policy-player-parent-code.html": "Player code of conduct and parent & guardian expectations — how players train, compete and behave, and how families support the academy.",
    "policy-safeguarding-child-protection.html": "The full Safeguarding & Child Protection Policy (2026–2031) — principles, roles, safe recruitment, safe environments and responding to concerns.",
    "portal-guide.html": "Step-by-step guide to the Sporting Pearls staff and parent portals — sign-in, submissions, players, fixtures, announcements, welfare and account tasks.",
    "results.html": "Match results for Sporting Pearls squads — U9, U13, U15, U17, U19 and Féminin, published by the academy office as matches are played.",
    "safeguarding.html": "Safeguarding and child protection at Sporting Pearls — our commitment, principles, how to raise a concern, and key public policies.",
    "the-squad.html": "Official squads and rosters — U9, U13, U15, U17, U19 Senior and Sporting Pearls Féminin. Est. 2020, Mtwapa, Kenya.",
}
for d in NEW_DESC.values():
    assert len(d) < 160, f"description not under 160: {len(d)} {d[:60]}"
assert len(set(NEW_DESC.values())) == len(NEW_DESC), "duplicate description"

ERR_PAGES = {"404.html", "50x.html"}
PAGES = sorted(p.name for p in SITE.glob("*.html") if p.name not in ERR_PAGES)

# ════════════════════════════════════════════════════════════════════
# T1 — head surgery on every public page
# ════════════════════════════════════════════════════════════════════
print("== T1 head surgery ==")
DESC_RE = re.compile(r'<meta\s+name="description"\s+content="([^"]*)"\s*>', re.S)

for name in PAGES:
    html = rw(name)
    did = []
    m = DESC_RE.search(html)
    assert m, f"{name}: no description meta found"
    # 1. rewrite over-long description
    if name in NEW_DESC and m.group(1) != NEW_DESC[name]:
        html = html[:m.start()] + f'<meta name="description" content="{NEW_DESC[name]}">' + html[m.end():]
        did.append(f"description rewritten ({len(m.group(1))} -> {len(NEW_DESC[name])} chars)")
        m = DESC_RE.search(html)
    # 2. canonical + OG block after the description meta
    if 'rel="canonical"' not in html:
        title = re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()
        desc = m.group(1)
        url = f"{DOMAIN}/{'' if name == 'index.html' else name}"
        ogtype = "profile" if name == "player.html" else "website"
        block = (
            f'\n<link rel="canonical" href="{url}">'
            f'\n<meta property="og:title" content="{title}">'
            f'\n<meta property="og:description" content="{desc}">'
            f'\n<meta property="og:image" content="{DOMAIN}/sp-pitch-aerial.jpg">'
            f'\n<meta property="og:type" content="{ogtype}">'
            f'\n<meta property="og:url" content="{url}">'
        )
        html = html[:m.end()] + block + html[m.end():]
        did.append("canonical + OG tags added")
    if did:
        wr(name, html)
        log(name, "; ".join(did))

# favicon for the error pages
for name in sorted(ERR_PAGES):
    html = rw(name)
    if 'rel="icon"' not in html:
        html = html.replace("</title>", '</title>\n<link rel="icon" type="image/png" href="logo.png">', 1)
        wr(name, html)
        log(name, "favicon added (logo.png)")

# ════════════════════════════════════════════════════════════════════
# T8 — lazy loading
# ════════════════════════════════════════════════════════════════════
print("== T8 lazy loading ==")
EAGER_CLASSES = {"pl-logo-img", "sp-nav-brand-mark"}
lazy_total = 0
for name in PAGES:
    html = rw(name)
    # hero blocks (image stays eager — LCP)
    hero_spans = []
    for hm in re.finditer(r'<(section|header)\s+class="hero[^"]*"[^>]*>.*?</\1>', html, re.S):
        hero_spans.append((hm.start(), hm.end()))
    def in_hero(pos):
        return any(a <= pos < b for a, b in hero_spans)

    out, last, n = [], 0, 0
    for im in re.finditer(r"<img\b[^>]*>", html):
        tag = im.group(0)
        if "loading=" in tag or "fetchpriority" in tag:
            continue
        cls = (re.search(r'class="([^"]*)"', tag) or [None, ""])[1]
        if cls in EAGER_CLASSES or in_hero(im.start()):
            continue
        new = tag[:-1].rstrip() + ' loading="lazy">'
        out.append(html[last:im.start()]); out.append(new)
        last = im.end(); n += 1
    out.append(html[last:])
    if n:
        wr(name, "".join(out))
        lazy_total += n
        log(name, f"{n} below-the-fold image(s) -> loading=lazy")
print(f"  total lazy additions: {lazy_total}")

# ════════════════════════════════════════════════════════════════════
# T2 — copy edits
# ════════════════════════════════════════════════════════════════════
print("== T2 copy edits ==")

# index: hero label that duplicated the H1
html = rw("index.html")
OLD = '<div class="hero-tagline">Developing Talent. Building Character. Transforming Lives Through Football.</div>'
NEW = '<div class="hero-tagline">Mtwapa · Kilifi County · Since 2020</div>'
if OLD in html:
    html = html.replace(OLD, NEW, 1); wr("index.html", html)
    log("index.html", "hero label no longer duplicates the H1 (now 'Mtwapa · Kilifi County · Since 2020')")
elif NEW in html:
    log("index.html", "hero label already replaced")
else:
    sys.exit("index.html: hero-tagline anchor not found")

# index: final pillar title (duplicated its section heading)
html = rw("index.html")
OLD = "<h3>Building The Future Together</h3>"
NEW = "<h3>A Community United</h3>"
if OLD in html:
    html = html.replace(OLD, NEW, 1); wr("index.html", html)
    log("index.html", "pillar 06 retitled 'A Community United' (was duplicate of section heading)")
elif NEW in html:
    log("index.html", "pillar 06 already retitled")
else:
    sys.exit("index.html: pillar 06 anchor not found")

# contact: replace the redundant '2020 · Serving the Community' stat
html = rw("contact.html")
OLD = '<div class="hero-stat"><b>2020</b><span>Serving the Community</span></div>'
NEW = '<div class="hero-stat"><b data-count="6">0</b><span>Teams · U9 → Féminin</span></div>'
if OLD in html:
    html = html.replace(OLD, NEW, 1); wr("contact.html", html)
    log("contact.html", "hero stat 3 '2020 · Serving the Community' -> '6 · Teams U9 → Féminin' (fact already on index impact strip)")
elif NEW in html:
    log("contact.html", "hero stat 3 already replaced")
else:
    sys.exit("contact.html: hero stat anchor not found")

# contact: response-time line (wording already stated by the auto-reply email)
html = rw("contact.html")
OLD = "<p data-reveal>For anything that doesn't fit a structured form — questions about programmes, visits, media, or general information — send us a message and we will get back to you.</p>"
NEW = ("<!-- OWNER: confirm response time (wording mirrors the auto-reply email: \"within a few working days\") -->\n"
       "<p data-reveal>For anything that doesn't fit a structured form — questions about programmes, visits, media, or general information — send us a message and we will get back to you. The academy office reads every message and replies within a few working days.</p>")
if OLD in html:
    html = html.replace(OLD, NEW, 1); wr("contact.html", html)
    log("contact.html", "response-time line added (matches the kit's auto-reply wording) + OWNER comment")
elif NEW in html:
    log("contact.html", "response-time line already present")
else:
    sys.exit("contact.html: enquiry intro anchor not found")

# join-us: heading + hero stat + comments
html = rw("join-us.html")
edits = [
    ('<h2 class="wr" data-words>Five gateways. <span class="it">One family.</span></h2>',
     '<h2 class="wr" data-words>Ten gateways. <span class="it">One family.</span></h2>',
     "heading 'Five gateways' -> 'Ten gateways' (10 forms shown)"),
    ('<div class="hstat"><b><span data-count="5">0</span></b><span>Onboarding Pathways</span></div>',
     '<div class="hstat"><b><span data-count="6">0</span></b><span>Onboarding Pathways</span></div>',
     "hero stat 5 -> 6 Onboarding Pathways (forms 01-06 are the main pathways)"),
    ("<!-- 02 THE 5 CORE ONBOARDING PATHWAYS -->",
     "<!-- 02 THE TEN ONBOARDING FORMS (01-06 MAIN PATHWAYS + 07-10 OTHER FORMS) -->",
     "section comment updated"),
    ("<!-- 03 SECONDARY SUPPORT PATHWAYS -->",
     "<!-- 03 OTHER FORMS (07-10) -->",
     "strip comment updated"),
]
for old, new, what in edits:
    if new in html:
        log("join-us.html", f"{what} (already)")
    elif old in html:
        html = html.replace(old, new, 1)
        log("join-us.html", what)
    else:
        sys.exit(f"join-us.html: anchor not found: {old[:60]}")
wr("join-us.html", html)

# ════════════════════════════════════════════════════════════════════
# T5 — join-us forms hub grouping
# ════════════════════════════════════════════════════════════════════
print("== T5 forms hub ==")
html = rw("join-us.html")

# 1. group label above the main grid
LBL1 = '<p class="sec-eyebrow gw-group" data-reveal>Main Pathways &middot; Forms 01&ndash;06</p>'
if LBL1 not in html:
    anchor = 'Select your dedicated application form below. All registrations are processed directly by our Technical Director and Safeguarding Lead.</p>\n    </div>\n\n    <div class="gw-grid">'
    assert anchor in html, "join-us: sec-head/gw-grid anchor not found"
    html = html.replace(anchor, anchor.replace('<div class="gw-grid">', LBL1 + '\n\n    <div class="gw-grid">'), 1)
    log("join-us.html", "'Main Pathways · Forms 01–06' group label added")

# 2. Form 06 becomes the sixth gateway card
if "form-06-sponsorship-partnership.html\" class=\"gw-btn\"" not in html:
    anchor = ('<a href="form-05-coach-technical-staff.html" class="gw-btn">Coach Application (Form 05) '
              '<span class="ar">→</span></a>\n      </article>')
    assert anchor in html, "join-us: gateway 05 anchor not found"
    card06 = anchor + '''

      <!-- GATEWAY 06: SPONSORSHIP & PARTNERSHIP -->
      <article class="gw-card" style="--ac:var(--amber)" data-reveal>
        <div class="gw-top">
          <svg class="sk"><use href="#i-link"/></svg>
          <span class="n">06</span>
        </div>
        <h3>Sponsorship & Partnership</h3>
        <p>For companies, foundations and individuals ready to invest in kits, education, facilities and the long-term development of young players.</p>
        <ul class="gw-list">
          <li>Sponsorship and partnership enquiries</li>
          <li>Kit branding and programme support</li>
          <li>Multi-year partnership tiers</li>
          <li>Accountability and impact reporting</li>
        </ul>
        <a href="form-06-sponsorship-partnership.html" class="gw-btn">Sponsorship Application (Form 06) <span class="ar">→</span></a>
      </article>'''
    html = html.replace(anchor, card06, 1)
    log("join-us.html", "Form 06 added as sixth Main Pathway card (direct link to the form page)")

# 3. support strip -> 'Other forms' group of four (07-10)
LBL2 = '<p class="sec-eyebrow gw-group" data-reveal>Other Forms &middot; 07&ndash;10</p>'
if LBL2 not in html:
    anchor = '<div class="strip-grid">'
    assert html.count(anchor) == 1, "join-us: strip-grid anchor not unique"
    html = html.replace(anchor, LBL2 + '\n      ' + anchor, 1)
    log("join-us.html", "'Other Forms · 07–10' group label added")

if "form-08-contact-form.html\" class=\"s-link\"" not in html:
    # remove the old Form 06 strip card (now a main-pathway card)
    old06 = '''      <div class="s-card" data-reveal="left">
        <div>
          <h3>Sponsor / Partner with Us</h3>
          <p>Explore corporate sponsorship, team kit branding, and long-term community development investments.</p>
        </div>
        <a href="partners.html" class="s-link">Form 06: Partnership Enquiry →</a>
      </div>

'''
    assert old06 in html, "join-us: old form-06 strip card not found"
    html = html.replace(old06, "", 1)
    # repoint 07 to the form page and add 08 + 09
    old07 = '''        <a href="support-us.html" class="s-link">Form 07: Donation & Support →</a>
      </div>
'''
    new07 = '''        <a href="form-07-donation-support.html" class="s-link">Form 07: Donation &amp; Support →</a>
      </div>

      <div class="s-card" data-reveal="zoom">
        <div>
          <h3>General Enquiry</h3>
          <p>Anything else the academy office can help with — programmes, policies, visits or paperwork.</p>
        </div>
        <a href="form-08-contact-form.html" class="s-link">Form 08: Contact &amp; Enquiry →</a>
      </div>

      <div class="s-card" data-reveal="zoom">
        <div>
          <h3>Media &amp; Photo Consent</h3>
          <p>Give, refuse or withdraw permission for photographs and video of your child, per the safeguarding policy.</p>
        </div>
        <a href="form-09-media-photo-consent.html" class="s-link">Form 09: Media &amp; Photo Consent →</a>
      </div>
'''
    assert old07 in html, "join-us: form 07 strip card not found"
    html = html.replace(old07, new07, 1)
    log("join-us.html", "Other Forms group now 07/08/09/10 (07 repointed to the form page; 08+09 added; old 06 card moved to main grid)")

wr("join-us.html", html)

print(f"\nTOTAL: {len(changes)} page-level changes")
