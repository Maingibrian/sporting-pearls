#!/usr/bin/env python3
"""P8 — image compression (T8), final pipeline.

- feminin-hero.jpg / sp-coach-address.jpg: ffmpeg nlmeans denoise
  (edge-preserving; these photos carry heavy baked-in grain that made a
  plain re-encode plateau at ~300 KB) + high-quality JPEG re-encode.
  Same dimensions, same filenames. Rollback copies: scripts/originals/.
- logo.png: Pillow re-encode (lossless optimise, then adaptive palette
  if needed) — flat RGBA artwork.

Run from the kit root:  python3 scripts/p8_images.py
"""
import subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
TARGET = 200_000  # "under 200 KB", strict decimal reading

# (file, ffmpeg -vf filter, -q:v) — chosen from a measured quality/size curve
JPEG_JOBS = [
    ("feminin-hero.jpg", "nlmeans=s=10:p=7:r=11", 5),
    ("sp-coach-address.jpg", "nlmeans=s=16:p=7:r=11", 4),
]


def human(n):
    return f"{n/1024:.0f} KiB ({n} B)"


results = []
for name, vf, q in JPEG_JOBS:
    src = ROOT / "scripts" / "originals" / name
    dst = SITE / name
    orig_size = dst.stat().st_size
    r = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-vf", vf, "-q:v", str(q), "-update", "1", str(dst)],
        capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"{name}: ffmpeg failed: {r.stderr[:300]}"
    new_size = dst.stat().st_size
    im = Image.open(dst)
    src_im = Image.open(src)
    assert im.size == src_im.size, f"{name}: dimensions changed!"
    assert new_size < TARGET, f"{name}: {new_size} not under {TARGET}"
    results.append((name, f"ffmpeg {vf} q:v{q}", orig_size, new_size))
    print(f"{name:22} {orig_size/1024:6.0f} KiB -> {new_size/1024:5.0f} KiB   ({vf}, q:v {q})")

# logo.png
p = SITE / "logo.png"
orig_size = p.stat().st_size
im = Image.open(p)
assert im.mode == "RGBA"
w, h = im.size
im.save(p, "PNG", optimize=True)
method = "lossless optimise"
if p.stat().st_size >= TARGET:
    q = im.quantize(colors=256, method=Image.FASTOCTREE)
    q.save(p, "PNG", optimize=True)
    method = "adaptive 256-colour palette (visually lossless for flat artwork)"
assert p.stat().st_size < TARGET, f"logo.png: {p.stat().st_size} not under target"
assert Image.open(p).size == (w, h)
print(f"{'logo.png':22} {orig_size/1024:6.0f} KiB -> {p.stat().st_size/1024:5.0f} KiB   ({method})")

# rollback copies verified present
for name, *_ in JPEG_JOBS:
    assert (ROOT / "scripts" / "originals" / name).exists()
assert (ROOT / "scripts" / "originals" / "logo.png").exists()
print("\nall three under 200 KB; dimensions preserved; originals in scripts/originals/")
