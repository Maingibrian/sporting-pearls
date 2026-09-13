#!/usr/bin/env python3
"""
Sporting Pearls - Link Pearls/ photo library into the mega-nav previews.

Re-points every nav item preview (data-img), each dropdown preview-figure
src and the navbar JS fallbackImg inside the shared sp-nav-pro mega
navigation to relevant local images from the Pearls/ folder.

Every mapping below was chosen from images whose content is PROVEN by the
site's own captions/alt-text (boys-programme.html, education-life-skills.html,
goalkeeper-development.html, index.html, the-squad.html), e.g.:
  radoms/IMG_7088.jpg = classroom & mentorship life skills
  radoms/IMG_7078.jpg = holiday camps & educational workshops
  radoms/IMG_7075.jpg = technical coaching on pitch
  radoms/IMG_7080.jpg = whole squad on the training pitch
  kids/IMG_6780.jpg  = U9 grassroots boys training
  kids/IMG_6772.jpg  = U11 boys training session
  kids/IMG_6760.jpg  = junior (U9) goalkeeper
  kids/IMG_6858.jpg  = parents and community supporting players
  kid%2013/IMG_6886.jpg = U13 boys tactical drill
  kid%2013/IMG_6891.jpg = U15 boys competitive match
  u-19/18.jpg        = U17 boys squad trophy celebration
  u-19/1.jpg         = senior squad captain and team
  u-19/IMG_7014.jpg  = goalkeeper handling / match focus
  FEMALE/IMG_6700.jpg = girls team huddle / mentorship huddle
  FEMALE/IMG_6704.jpg = Féminin (girls) player

The replacement is idempotent: it re-points whatever image is currently on
the item, so you can tweak MAP below and re-run safely.

Usage:
  python pearls-nav-link.py <folder>            # re-point every .html in folder (in place)
  python pearls-nav-link.py <folder> --dry-run  # show what would change
"""
import sys, glob, os, io, re

# Nav item preview images keyed by their data-title attribute.
MAP = {
    # --- About dropdown ---
    "About Us":                    "Pearls/radoms/IMG_7080.jpg",
    "Our Story":                   "Pearls/kids/IMG_6780.jpg",
    "Vision & Mission":            "Pearls/radoms/IMG_7075.jpg",
    "Core Values":                 "Pearls/kids/IMG_6772.jpg",
    "Leadership & Governance":     "Pearls/radoms/IMG_7088.jpg",
    "Safeguarding":                "Pearls/kids/IMG_6760.jpg",
    "Chairman's Message":          "Pearls/radoms/IMG_7078.jpg",
    "Partner With Us":             "Pearls/kids/IMG_6858.jpg",
    # --- Academy dropdown ---
    "Player Development":          "Pearls/radoms/IMG_7075.jpg",
    "Boys' Programme":             "Pearls/kid%2013/IMG_6886.jpg",
    "Sporting Pearls F\u00e9minin": "Pearls/FEMALE/IMG_6700.jpg",
    "Goalkeeper Development":      "Pearls/u-19/IMG_7014.jpg",
    "Coaching Philosophy":         "Pearls/radoms/IMG_7088.jpg",
    "Education & Life Skills":     "Pearls/radoms/IMG_7078.jpg",
    "Trials & Registration":       "Pearls/kids/IMG_6780.jpg",
    "Academy Enquiries":           "Pearls/radoms/IMG_7080.jpg",
    # --- Teams dropdown ---
    "U9 & U13":                    "Pearls/kids/IMG_6780.jpg",
    "U15 & U17":                   "Pearls/u-19/18.jpg",
    "U19 Senior":                  "Pearls/u-19/1.jpg",
    "F\u00e9minin Squads":          "Pearls/FEMALE/IMG_6704.jpg",
    "Fixtures":                    "Pearls/kid%2013/IMG_6891.jpg",
    "Results":                     "Pearls/u-19/IMG_7014.jpg",
    "Player Pathway":              "Pearls/radoms/IMG_7075.jpg",
    "Training Centre":             "Pearls/radoms/IMG_7080.jpg",
}

# Default preview images for each dropdown figure, keyed by figcaption title.
FIGURE_MAP = {
    "About Us":           "Pearls/radoms/IMG_7080.jpg",
    "Player Development": "Pearls/radoms/IMG_7075.jpg",
    "U9 & U13":           "Pearls/kids/IMG_6780.jpg",
}

# Navbar JS fallback preview image (used when an item has no data-img).
FALLBACK_IMG = "Pearls/radoms/IMG_7080.jpg"

ITEM_RE = re.compile(r"<a class=\"sp-nav-item[^>]*?>", re.S)
FIG_RE  = re.compile(r"(<figure class=\"sp-nav-preview\">)(.*?)(</figure>)", re.S)
FIG_IMG = re.compile(r"(<img class=\"sp-nav-preview-img\" src=\")[^\"]+(\")")
FALL_RE = re.compile(r"const fallbackImg\s*=\s*\"[^\"]*\"")

UNMAPPED, FIGURED = [], []

def fix_item(tag):
    m = re.search(r"data-title=\"([^\"]*)\"", tag)
    title = m.group(1) if m else ""
    if title in MAP and "data-img=\"" in tag:
        return re.sub(r"data-img=\"[^\"]*\"", "data-img=\"%s\"" % MAP[title], tag, count=1)
    if "data-img=\"" in tag and title:
        UNMAPPED.append(title)
    return tag

def fix_figure(m):
    head, inner, tail = m.group(1), m.group(2), m.group(3)
    cm = re.search(r"<h4 class=\"sp-nav-preview-title\">([^<]*)</h4>", inner)
    key = cm.group(1).strip() if cm else ""
    if key in FIGURE_MAP and FIG_IMG.search(inner):
        inner = FIG_IMG.sub(lambda g: g.group(1) + FIGURE_MAP[key] + g.group(2), inner, count=1)
        FIGURED.append(key)
    return head + inner + tail

def read_text(path):
    with io.open(path, "rb") as f:
        raw = f.read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return (raw[3:] if bom else raw).decode("utf-8"), bom

def main():
    global UNMAPPED, FIGURED
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    folder = sys.argv[1]
    dry = "--dry-run" in sys.argv
    total = 0

    for path in sorted(glob.glob(os.path.join(folder, "*.html"))):
        UNMAPPED, FIGURED = [], []
        src, bom = read_text(path)
        out = src

        # 1) nav-item data-img previews
        out = ITEM_RE.sub(lambda m: fix_item(m.group(0)), out)

        # 2) dropdown figure default preview images
        out = FIG_RE.sub(fix_figure, out)

        # 3) navbar JS fallback image
        out = FALL_RE.sub(lambda g: "const fallbackImg = \"%s\"" % FALLBACK_IMG, out)

        n_items = out.count("data-img=\"Pearls/")
        n_figs  = len(FIGURED)
        n_fb    = len(FALL_RE.findall(src)) - len(FALL_RE.findall(out))
        changed = (n_items > 0) or (n_figs > 0) or (n_fb > 0)
        if changed:
            total += 1
            print("\n%s: nav items -> %d, figures -> %d, fallback -> %d" % (os.path.basename(path), n_items, n_figs, n_fb))
            if UNMAPPED:
                print("   UNMAPPED items: %s" % ", ".join(sorted(set(UNMAPPED))))
            if not dry:
                with io.open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(("\ufeff" if bom else "") + out)
    if dry:
        print("\n[DRY RUN] %d file(s) would change. No files were modified." % total)
    else:
        print("\nDone. %d file(s) re-pointed to Pearls/ images." % total)

if __name__ == "__main__":
    main()
