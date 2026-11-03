#!/usr/bin/env python3
"""P8 contrast audit — measure WCAG contrast ratios for grey text on dark backgrounds.

Colours are taken verbatim from the page CSS (rgba pearl alphas over the
declared dark section backgrounds). Also probes the tiny-label colour pairs.
"""
# ── WCAG relative luminance / contrast ─────────────────────────────────
def srgb(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def lum(rgb):
    r, g, b = (srgb(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(fg, bg):
    l1, l2 = sorted((lum(fg), lum(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)

def blend(alpha, fg=(251, 250, 247), bg=(12, 26, 51)):
    """rgba(251,250,247,alpha) composited over bg."""
    return tuple(alpha * f + (1 - alpha) * b for f, b in zip(fg, bg))

PEARL = (251, 250, 247)
NAVY = (20, 40, 75)      # #14284b
NAVY2 = (12, 26, 51)     # #0c1a33  (heroes, faq-sec, values dark)
NAVY3 = (16, 33, 65)     # #102141
NAVY4 = (26, 50, 96)     # #1a3260  (leadership hero gradient start)
INK = (11, 26, 54)       # #0b1a36

print("Alpha sweep — rgba(251,250,247,a) over the four dark navies")
print(f"{'a':>5} {'on 0c1a33':>10} {'on 14284b':>10} {'on 1a3260':>10} {'on 102141':>10}")
for a in (0.40, 0.45, 0.50, 0.55, 0.60, 0.62, 0.65, 0.66, 0.68, 0.70, 0.72, 0.75, 0.78, 0.80, 0.85):
    row = [contrast(blend(a), bg) for bg in (NAVY2, NAVY, NAVY4, NAVY3)]
    print(f"{a:>5} " + " ".join(f"{r:>10.2f}" for r in row))

print("\nMinimum alpha for 4.5:1 on the lightest dark navy (#1a3260):")
lo, hi = 0.5, 1.0
for _ in range(30):
    mid = (lo + hi) / 2
    if contrast(blend(mid), NAVY4) >= 4.5:
        hi = mid
    else:
        lo = mid
print(f"  alpha >= {hi:.3f}")

print("\nMeasured pairs actually used in the CSS (worst-case solid bg):")
pairs = [
    # (label, fg, bg)
    ("partners/contact/safeguarding… hero-stat span  .55 pearl", blend(0.55), NAVY2),
    ("leadership/support-us/player-dev hero-stat span  .55 pearl", blend(0.55), NAVY2),
    ("join-us hstat span  .68 pearl", blend(0.68), NAVY),
    ("leadership charter-band p  .68 pearl (14px body)", blend(0.68), NAVY2),
    ("leadership cb-meta span  .50 pearl", blend(0.50), NAVY2),
    ("leadership/support/pd card-meta  .45 pearl", blend(0.45), NAVY2),
    ("leadership/support/pd hs-txt  .50 pearl", blend(0.50), NAVY2),
    ("leadership/support/pd cent-flow i  .40 pearl", blend(0.40), NAVY2),
    ("education hero-side  .45 pearl (decorative, aria-hidden)", blend(0.45), NAVY2),
    ("--muted-d  .66 pearl", blend(0.66), NAVY2),
    ("hero-sub chalkline  .70 pearl", blend(0.70), NAVY2),
    ("NEW proposal  .78 pearl", blend(0.78), NAVY4),
    ("NEW proposal  .80 pearl", blend(0.80), NAVY4),
    ("amber #f59d1e on navy-2 (hero-stat b)", (245, 157, 30), NAVY2),
    ("amber-2 #d97f06 on pearl (light kickers)", (217, 127, 6), PEARL),
    ("muted #3e4a5a on pearl (light body)", (62, 74, 90), PEARL),
    ("body #2f3b4d on pearl", (47, 59, 77), PEARL),
    ("ink #0b1a36 on sand #f3efe7", (11, 26, 54), (243, 239, 231)),
]
print(f"{'pair':<62} {'ratio':>7}  4.5:1?")
for label, fg, bg in pairs:
    r = contrast(fg, bg)
    print(f"{label:<62} {r:>7.2f}  {'PASS' if r >= 4.5 else 'FAIL'}")
