#!/usr/bin/env python3
"""P8b — eyebrow renumbering (T3) + place-naming standardisation (T2).

T3: pages whose first numbered eyebrow starts at 02 (or 03) are renumbered
    to start at 01 and stay continuous. The HTML <!-- NN --> section
    comments are an internal all-sections index (they also number the hero
    and sections without eyebrows) and are deliberately left untouched.
T2: first visible body mention of "Kilifi County" per page becomes
    "Mtwapa, Kilifi County"; later mentions stay "Kilifi County".
    Head metadata, the shared nav, and footers are not body copy; the
    physical address content is never touched (only bare county mentions
    are extended).

Run from the kit root:  python3 scripts/p8_renumber.py
"""
import re
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"

# old eyebrow number -> new number, per page
RENUMBER = {
    "about-us.html": {2: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 7, 10: 8, 11: 9},
    "partners.html": {n: n - 1 for n in range(2, 17)},
    "safeguarding.html": {n: n - 1 for n in range(2, 9)},
    "leadership-governance.html": {n: n - 1 for n in range(2, 7)},
    "chairman-message.html": {3: 1, 4: 2},
    "boys-programme.html": {6: 5, 7: 6, 8: 7},
    "education-life-skills.html": {5: 4, 6: 5},
    "coaching-philosophy.html": {9: 8},
}

EYE_RE = re.compile(r'((?:p|span)\s+class="sec-eyebrow"[^>]*>\s*)(\d{2})(\s*·)')

print("== T3 eyebrow renumbering ==")
for page, mapping in RENUMBER.items():
    p = SITE / page
    html = p.read_text(encoding="utf-8")
    # show current sequence for the record
    seq = [int(m.group(2)) for m in EYE_RE.finditer(html)]
    if not seq:
        print(f"  [{page}] NO numbered eyebrows found — skipping")
        continue
    def sub(m):
        n = int(m.group(2))
        return f"{m.group(1)}{mapping.get(n, n):02d}{m.group(3)}"
    new_html, n = EYE_RE.subn(sub, html)
    new_seq = [int(m.group(2)) for m in EYE_RE.finditer(new_html)]
    changed = new_html != html
    if changed:
        p.write_text(new_html, encoding="utf-8")
    print(f"  [{page}] {seq} -> {new_seq} ({n} eyebrows{' CHANGED' if changed else ' — already correct'})")

# ════════════════════════════════════════════════════════════════════
# T2 — place naming
# ════════════════════════════════════════════════════════════════════
print("\n== T2 place naming (first body mention) ==")
BODY_RE = re.compile(r"<main\b.*?</main>|<header class=\"hero[^>]*>.*?</header>", re.S)
for p in sorted(SITE.glob("*.html")):
    html = p.read_text(encoding="utf-8")
    body = "".join(m.group(0) for m in BODY_RE.finditer(html))
    if not body or "Kilifi County" not in body:
        continue
    # find mentions in visible text: strip tags so attributes (data-copy etc.) never match
    text_only = re.sub(r"<[^>]+>", "\x00", body)  # keep offsets via placeholder
    first = None
    for m in re.finditer(r"Kilifi County", text_only):
        first = m.start()
        break
    if first is None:
        continue
    # already "Mtwapa, Kilifi County"? (check the 30 chars before, on the same text run)
    ctx = text_only[max(0, first - 30):first]
    if "Mtwapa" in ctx:
        print(f"  [{p.name}] first body mention already includes Mtwapa")
        continue
    # map back to the raw html: count visible-text occurrences up to `first`
    # by walking the body with the same tag-stripping offsets.
    pos, count = 0, 0
    target = None
    for piece in re.finditer(r"([^<]+)", body):
        txt = piece.group(1)
        idx = 0
        while True:
            k = txt.find("Kilifi County", idx)
            if k < 0:
                break
            if count == 0:  # first visible-text occurrence
                target = piece.start() + k
            count += 1
            idx = k + 1
    if target is None:
        print(f"  [{p.name}] no visible-text mention (attribute only) — skipped")
        continue
    snippet = body[target - 60:target + 40].replace("\n", " ")
    new_body = body[:target] + "Mtwapa, " + body[target:]
    new_html = html.replace(body, new_body, 1)
    p.write_text(new_html, encoding="utf-8")
    print(f"  [{p.name}] first body mention -> 'Mtwapa, Kilifi County'  | …{snippet}…")
