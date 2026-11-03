#!/usr/bin/env python3
"""P8 CSS edits — kit rev 20 polish round.

Covers:
  T4  stat strips: mobile 3-up grid + aligned labels (shared bl14m files,
      per-page CSS, and the 3 inline-style pages).
  T7  typography: every uppercase monospace label raised to >= 12px
      (0.75rem) — blanket, marker-based, with a manual-review log.
  T7  contrast: grey-on-dark alphas raised to pass WCAG AA 4.5:1
      (measured in scripts/p8_contrast.py).
  T7  policy-data-privacy: paragraph spacing + subheading size.
  T5  join-us: strip grid for four cards + group-label style.

Idempotent. Run from the kit root:  python3 scripts/p8_css_edits.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
changes = []


def log(f, what):
    changes.append((f, what))
    print(f"  [{f}] {what}")


def rw(p):
    return Path(p).read_text(encoding="utf-8")


def wr(p, t):
    Path(p).write_text(t, encoding="utf-8")


# ════════════════════════════════════════════════════════════════════
# T7a — blanket tiny-label raise (>= 0.75rem) where the rule is a
#       monospace / uppercase label (marker-based)
# ════════════════════════════════════════════════════════════════════
print("== T7a tiny labels -> >= 12px ==")
MARKERS = ("var(--fm)", "var(--sp-mono)", "'Space Mono'", "text-transform:uppercase", "text-transform: uppercase")
FS_RE = re.compile(r"font-size:\s*\.?(\d*\.?\d+)rem")

def raise_labels(text, name):
    """Raise every <0.75rem font-size whose rule carries a mono/uppercase marker."""
    n, review = 0, []

    def walk(css):
        nonlocal n
        out, i = [], 0
        for rm in re.finditer(r"\{[^{}]*\}", css):
            rule = rm.group(0)
            def sub(fm):
                nonlocal n
                val = float(fm.group(1))
                if val >= 0.75:
                    return fm.group(0)
                if any(mk in rule for mk in MARKERS):
                    n += 1
                    return "font-size:0.75rem"
                review.append(f"{fm.group(0)} in rule ...{rule[:70]}")
                return fm.group(0)
            new_rule = FS_RE.sub(sub, rule)
            out.append(css[i:rm.start()]); out.append(new_rule)
            i = rm.end()
        out.append(css[i:])
        return "".join(out)

    return walk(text), n, review

CSS_FILES = [
    "assets/css/pages/about-us.css", "assets/css/pages/academy.css",
    "assets/css/pages/index.css", "assets/css/pages/institutional-blueprint.css",
    "assets/css/pages/leadership-governance.css", "assets/css/pages/player.css",
    "assets/css/pages/policy.css", "assets/css/pages/portal-guide.css",
    "assets/css/pages/results.css", "assets/css/pages/the-squad.css",
    "assets/css/pages/leadership-governance.css", "assets/css/pages/join-us.css",
    "assets/css/pages/support-us.css", "assets/css/pages/player-development.css",
    "assets/css/pages/contact.css", "assets/css/pages/feminin.css",
    "assets/css/pages/boys-programme.css", "assets/css/pages/education-life-skills.css",
    "assets/css/shared/bl14m-hero-600.css",
]
for rel in CSS_FILES:
    p = SITE / rel
    if not p.exists():
        continue
    old = rw(p)
    new, n, review = raise_labels(old, rel)
    if n:
        wr(p, new)
        log(rel, f"{n} label size(s) raised to 0.75rem (12px)")
    for r in review:
        print(f"    REVIEW (no marker, left as-is): {r[:110]}")

# inline-style pages (core-values / our-story / vision-mission)
for page in ["core-values.html", "our-story.html", "vision-mission.html"]:
    p = SITE / page
    html = rw(p)
    total = 0
    def fix_style(sm):
        global total
        css = sm.group(1)
        new, n, review = raise_labels(css, page)
        total += n
        for r in review:
            print(f"    REVIEW {page}: {r[:110]}")
        return sm.group(0).replace(css, new)
    new_html = re.sub(r"<style[^>]*>(.*?)</style>", fix_style, html, flags=re.S)
    if total:
        wr(p, new_html)
        log(page, f"{total} inline label size(s) raised to 0.75rem (12px)")

# ════════════════════════════════════════════════════════════════════
# T4 — stat strips: aligned 3-up grid on mobile
# ════════════════════════════════════════════════════════════════════
print("== T4 stat strips ==")

# shared bl14m-hero-600.css (8 pages)
p = SITE / "assets/css/shared/bl14m-hero-600.css"
css = rw(p)
OLD = """.hero-stats{gap:0.9rem 1.3rem;padding-top:0.8rem}
.hero-stat b{font-size:1.55rem;margin-bottom:0.3rem}"""
NEW = """.hero-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:0.9rem 0.6rem;padding-top:0.8rem}
.hero-stat b{font-size:1.55rem;margin-bottom:0.3rem}"""
if OLD in css:
    wr(p, css.replace(OLD, NEW, 1))
    log("bl14m-hero-600.css", "mobile hero-stats -> 3-column grid (aligned row at 390px)")
elif NEW in css:
    log("bl14m-hero-600.css", "grid already applied")
else:
    raise SystemExit("bl14m-hero-600.css anchor missing")

# shared bl14m-hero-600-b.css (2 pages, loads after -600)
p = SITE / "assets/css/shared/bl14m-hero-600-b.css"
css = rw(p)
OLD = ".hero-stats{padding-top:0.8rem;gap:1rem 0}"
NEW = ".hero-stats{display:grid;grid-template-columns:repeat(3,1fr);padding-top:0.8rem;gap:1rem 0.6rem}"
if OLD in css:
    wr(p, css.replace(OLD, NEW, 1))
    log("bl14m-hero-600-b.css", "mobile hero-stats -> 3-column grid")
elif NEW in css:
    log("bl14m-hero-600-b.css", "grid already applied")
else:
    raise SystemExit("bl14m-hero-600-b.css anchor missing")

# per-page CSS heroes (leadership-governance, player-development)
MOBILE_BLOCK = """
/* ═══ P8: mobile stat-strip alignment (3-up grid, 12px labels) ═══ */
@media(max-width:600px){
.hero-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem 0.6rem;}
.hero-stat span{font-size:0.75rem;letter-spacing:.06em;}
.hero-stat b{font-size:1.55rem;}
}
"""
for rel in ["assets/css/pages/leadership-governance.css", "assets/css/pages/player-development.css"]:
    p = SITE / rel
    css = rw(p)
    if "P8: mobile stat-strip alignment" not in css:
        wr(p, css.rstrip() + "\n" + MOBILE_BLOCK)
        log(rel, "mobile stat-strip grid block appended")

# inline-style pages: base label size + mobile grid block
for page in ["core-values.html", "our-story.html", "vision-mission.html"]:
    p = SITE / page
    html = rw(p)
    did = []
    def fix_style(sm):
        css = sm.group(1)
        if ".hero-stat span" not in css:
            return sm.group(0)
        new = css
        if "P8: mobile stat alignment" not in new:
            new = new.rstrip() + """

/* P8: mobile stat alignment + 12px minimum label size */
@media(max-width:600px){
.hero-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem 0.6rem;padding-top:1.4rem}
.hero-stat b{font-size:1.5rem;margin-bottom:.3rem}
.hero-stat span{font-size:.75rem;letter-spacing:.06em}
}
"""
            did.append("mobile grid block")
        return sm.group(0).replace(css, new)
    html = re.sub(r"<style[^>]*>(.*?)</style>", fix_style, html, flags=re.S)
    if did:
        wr(p, html)
        log(page, "; ".join(did))

# ════════════════════════════════════════════════════════════════════
# T7b — contrast: raise grey-on-dark alphas (WCAG AA 4.5:1)
# ════════════════════════════════════════════════════════════════════
print("== T7b contrast ==")
# (selector regex, old colour literal, new colour, note)
CONTRAST_FIXES = [
    (r"\.card-meta[^{]*\{[^}]*?color:\s*", "rgba(251,250,247,.45)", "rgba(251,250,247,.68)",
     "card-meta .45 -> .68 (was 4.29:1)"),
    (r"\.cb-meta[^{]*\{[^}]*?color:\s*", "rgba(251,250,247,.5)", "rgba(251,250,247,.68)",
     "cb-meta .50 -> .68 (charter band sits on the hero gradient)"),
    (r"\.hs-txt[^{]*\{[^}]*?color:\s*", "rgba(251,250,247,.5)", "rgba(251,250,247,.68)",
     "hs-txt .50 -> .68"),
    (r"\.cent-flow i[^{]*\{[^}]*?color:\s*", "rgba(251,250,247,.4)", "rgba(251,250,247,.62)",
     "cent-flow arrows .40 -> .62 (was 3.66:1)"),
    (r"\.path-flow i[^{]*\{[^}]*?color:\s*", "rgba(251,250,247,.4)", "rgba(251,250,247,.62)",
     "path-flow arrows .40 -> .62"),
    (r"\.hero-side[^{]*\{[^}]*?color:\s*", "rgba(251,250,247,.45)", "rgba(251,250,247,.62)",
     "hero-side .45 -> .62"),
    (r"\.pitch-side[^{]*\{[^}]*?color:\s*", "rgba(251,250,247,.45)", "rgba(251,250,247,.62)",
     "pitch-side .45 -> .62"),
    (r"\.vis \.v-n[^{]*\{[^}]*?color:\s*", "rgba(251,250,247,.4)", "rgba(251,250,247,.62)",
     "vis .v-n .40 -> .62"),
    (r"\.sp-enq-row[^{]*::placeholder[^{]*\{[^}]*?color:\s*", "rgba(251,250,247,.4)", "rgba(251,250,247,.55)",
     "enquiry placeholders .40 -> .55"),
]
ALL_CSS = sorted((SITE / "assets/css/pages").glob("*.css")) + sorted((SITE / "assets/css/shared").glob("*.css"))
for p in ALL_CSS:
    css = rw(p)
    did = []
    for sel_re, old_c, new_c, note in CONTRAST_FIXES:
        pattern = re.compile("(" + sel_re + ")" + re.escape(old_c), re.S)
        new_css, n = pattern.subn(lambda m: m.group(1) + new_c, css)
        if n:
            css = new_css
            did.append(f"{note} x{n}")
    if did:
        wr(p, css)
        log(p.name, "; ".join(did))

for page in ["core-values.html", "our-story.html", "vision-mission.html"]:
    p = SITE / page
    html = rw(p)
    did = []
    def fix_style(sm):
        css = sm.group(1)
        for sel_re, old_c, new_c, note in CONTRAST_FIXES:
            pattern = re.compile("(" + sel_re + ")" + re.escape(old_c), re.S)
            css, n = pattern.subn(lambda m: m.group(1) + new_c, css)
            if n and note not in did:
                did.append(f"{note} x{n}")
        # raise remaining sub-12px sizes: buttons / nav chips / scroll cue that
        # inherit their mono family from a base rule (no in-rule marker)
        def sub(fm):
            if float(fm.group(1)) < 0.75:
                did.append("remaining inherited-mono label(s) raised")
                return "font-size:0.75rem"
            return fm.group(0)
        css = FS_RE.sub(sub, css)
        return sm.group(0).replace(sm.group(1), css)
    html = re.sub(r"<style[^>]*>(.*?)</style>", fix_style, html, flags=re.S)
    # de-dup the log notes
    if did:
        uniq = list(dict.fromkeys(did))
        wr(p, html)
        log(page, "; ".join(uniq))

# ════════════════════════════════════════════════════════════════════
# T7c — policy-data-privacy: paragraph spacing + subheading size
# ════════════════════════════════════════════════════════════════════
print("== T7c policy doc spacing ==")
p = SITE / "assets/css/pages/policy.css"
css = rw(p)
edits = [
    (".doc-sec{padding-block:clamp(1.75rem,3.2vw,2.5rem);border-top:1px solid var(--hair);}",
     ".doc-sec{padding-block:clamp(2.25rem,4vw,3.25rem);border-top:1px solid var(--hair);}",
     "section spacing 1.75-2.5rem -> 2.25-3.25rem"),
    (".doc-sec p{margin-bottom:1.1rem;max-width:70ch;}",
     ".doc-sec p{margin-bottom:1.5rem;max-width:70ch;}",
     "paragraph spacing 1.1rem -> 1.5rem"),
    (".doc-sec h2{font-size:clamp(1.6rem,3vw,2.25rem);margin-bottom:1.25rem;}",
     ".doc-sec h2{font-size:clamp(1.8rem,3.4vw,2.5rem);margin-bottom:1.5rem;}",
     "section heading 1.6-2.25rem -> 1.8-2.5rem"),
    (".doc-sec h3{font-size:1.15rem;margin:1.6rem 0 .8rem;color:var(--ink);}",
     ".doc-sec h3{font-size:1.3rem;margin:1.8rem 0 .9rem;color:var(--ink);}",
     "subheading 1.15rem -> 1.3rem"),
]
did = []
for old, new, note in edits:
    if new in css:
        continue
    assert old in css, f"policy.css anchor missing: {old[:50]}"
    css = css.replace(old, new, 1)
    did.append(note)
wr(p, css)
log("policy.css", "; ".join(did) + "  (shared by all four policy pages — kept uniform by design)")

# ════════════════════════════════════════════════════════════════════
# T5 — join-us: four-card strip grid + group label style
# ════════════════════════════════════════════════════════════════════
print("== T5 join-us css ==")
p = SITE / "assets/css/pages/join-us.css"
css = rw(p)
OLD = """.strip-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1.5rem;}
@media(max-width:860px){.strip-grid{grid-template-columns:1fr;}}"""
NEW = """.strip-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1.25rem;}
@media(max-width:1020px){.strip-grid{grid-template-columns:repeat(2,1fr);}}
@media(max-width:640px){.strip-grid{grid-template-columns:1fr;}}"""
did = []
if NEW not in css and OLD in css:
    css = css.replace(OLD, NEW, 1)
    did.append("strip-grid 3 -> 4 columns (2x2 tablet, 1-col mobile)")
elif NEW in css:
    did.append("strip-grid already 4-col")
else:
    raise SystemExit("join-us.css strip-grid anchor missing")
if ".gw-group" not in css:
    css = css.rstrip() + """

/* ═══ P8: forms-hub group labels ═══ */
.gw-group{margin:0 0 1.5rem;}
"""
    did.append(".gw-group label style added")
css = css.replace("/* ============ 01 GATEWAYS (THE 5 CORE ONBOARDING PATHWAYS) ============ */",
                  "/* ============ 01 GATEWAYS (THE TEN ONBOARDING FORMS) ============ */", 1)
wr(p, css)
log("join-us.css", "; ".join(did))

print(f"\nTOTAL: {len(changes)} css-level changes")
