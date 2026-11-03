#!/usr/bin/env bash
# Build kit rev 22 and verify the artifact in-zip.
set -euo pipefail
KIT="/home/z/my-project/analysis/sporting-pearls"
OUT="/home/z/my-project/download/sporting-pearls-server-kit-v22.zip"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

cd "$KIT"
# ── stage the kit (source tree minus runtime artifacts) ──────────────
mkdir -p "$STAGE/sporting-pearls"
tar -cf - \
  --exclude='./backend/.venv' --exclude='./backend/db.sqlite3*' \
  --exclude='./backend/.env' --exclude='./backend/media' \
  --exclude='./backend/staticfiles' --exclude='./backend/logs' \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
  --exclude='./backend/.coverage*' --exclude='./scripts/p8_qa_out' \
  --exclude='./.git' \
  . | (cd "$STAGE/sporting-pearls" && tar -xf -)

cd "$STAGE/sporting-pearls"
zip -qr "$OUT" . -x '*.DS_Store'
cd /
echo "zip built: $(du -h "$OUT" | cut -f1), $(unzip -l "$OUT" | tail -1 | awk '{print $2}') files"

# ── in-zip verification ─────────────────────────────────────────────
T="$(mktemp -d)"
unzip -q "$OUT" -d "$T"
cd "$T"
P=0; F=0
ok(){ P=$((P+1)); echo "  PASS  $1"; }
no(){ F=$((F+1)); echo "  FAIL  $1"; }

# rev-22: real register import
[ "$(ls site/assets/img/squad/*.jpg 2>/dev/null | wc -l)" = "29" ] && ok "29 player photos shipped" || no "squad photos"
grep -q "real academy register, season 2026–27" site/assets/js/pages/the-squad.js && ok "TEAMS = real register (header note)" || no "teams header"
grep -q "'Suleimann','Alii'" site/assets/js/pages/the-squad.js && grep -q "'Alii','Thoya'" site/assets/js/pages/the-squad.js && ok "register players present (U12 + U19 spot checks)" || no "register players"
! grep -q "'Zainab','Kibwana'" site/assets/js/pages/the-squad.js && ! grep -q "'James','Karanja'" site/assets/js/pages/the-squad.js && ok "demo squads fully retired" || no "demo leftovers"
grep -q "var BANDS" site/assets/js/pages/the-squad.js && grep -q "renderBench" site/assets/js/pages/the-squad.js && ok "band placement + bench render" || no "bands/bench"
grep -q 'id="bench"' site/the-squad.html && grep -q '.bench-p' site/assets/css/pages/the-squad.css && ok "bench markup + css" || no "bench html/css"
grep -q 'the-squad.js?v26' site/the-squad.html && grep -q 'the-squad.css?v24' site/the-squad.html && ok "cache busts v26/v24" || no "cache busts"
[ "$(grep -o 'data-team="[a-z0-9]*"' site/the-squad.html | sort -u | wc -l)" = "5" ] && ok "5 squad tabs" || no "tab count"
grep -q 'data-count="50" id="statRoster"' site/the-squad.html && ok "stats 50 rostered" || no "stats"
! grep -rq 'data-title="U9 & U13"\|data-title="U15 & U17"' site/*.html && ok "sitewide nav relabelled" || no "old nav labels"
grep -q "'U12-01'" site/assets/js/shared/sp-player.js && grep -q "photo: dd.photo" site/assets/js/shared/sp-player.js && ok "player profiles: real refs + photo passthrough" || no "sp-player"
grep -q 'sp-player.js?v3' site/player.html && ok "player.html include bumped" || no "player include"
grep -q '"count": 50' backend/player_seed.json && grep -q '"U19-05"' backend/player_seed.json && ok "backend seed regenerated" || no "seed"
grep -q "'U12-01'" backend/submissions/tests/test_phase7.py && ok "QR wiring test on real refs" || no "test refs"
[ -f CHANGELOG-REV22.md ] && grep -q "REAL SQUAD ROSTER" templates/POST-INSTALL-README.txt && grep -q "KIT REVISION 22" FIX-NOTES-FORM-SYNC.txt && grep -q "kit rev 22" PRODUCTION-READINESS.md && grep -q "T84" PRODUCTION-READINESS.md && ok "rev-22 docs complete" || no "docs"

# rev-21 regression markers (carried forward)
[ -f site/assets/js/vendor/qr.min.js ] && ok "self-hosted QR lib shipped (no CDN)" || no "qr lib"
grep -q 'id="mQr"' site/the-squad.html && grep -q 'id="mQrLink"' site/the-squad.html && ok "squad modal QR markup" || no "qr markup"
grep -q "encodeURIComponent(pref)" site/assets/js/pages/the-squad.js && grep -q "SQUAD_CODE" site/assets/js/pages/the-squad.js && ok "QR ref plumbing" || no "qr refs"
grep -q 'qrcode-generator' site/assets/js/vendor/qr.min.js && ! grep -q 'eval(' site/assets/js/vendor/qr.min.js && ok "QR lib MIT + eval-free" || no "qr hygiene"
grep -q '.m-qr' site/assets/css/pages/the-squad.css && ok "QR card styling" || no "qr css"

# prior-phase regression markers (rev 20)
[ -f site/robots.txt ] && grep -q "Disallow: /portal/" site/robots.txt && ok "robots.txt" || no "robots.txt"
[ -f site/sitemap.xml ] && ok "sitemap.xml" || no "sitemap"
[ -f site/assets/js/shared/hero-parallax.js ] && ok "hero-parallax.js shipped" || no "hero-parallax.js"
[ "$(grep -l 'id="heroBg"' site/*.html | wc -l)" = "16" ] && ok "16 parallax photo heroes" || no "herobg count"
[ -f backend/requirements.txt ] && grep -q "Django==6.1.2" backend/requirements.txt && ok "pinned requirements" || no "requirements"
[ -f backend/Procfile ] && ok "Procfile" || no "procfile"
[ -f DEPLOY-RENDER.md ] && ok "DEPLOY-RENDER.md runbook" || no "deploy doc"
grep -q "parents\[3\] / 'site'" backend/submissions/tests/test_phase7.py && ! grep -rq "/home/z/" backend/submissions/tests/test_phase7.py && ok "test suite path-portable" || no "test path"

echo "── $P passed, $F failed ──"
[ "$F" = "0" ] || exit 1
