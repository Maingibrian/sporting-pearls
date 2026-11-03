#!/usr/bin/env bash
# Build kit rev 21 and verify the artifact in-zip.
set -euo pipefail
KIT="/home/z/my-project/analysis/sporting-pearls"
OUT="/home/z/my-project/download/sporting-pearls-server-kit-v21.zip"
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

# rev-21 artefacts
[ -f site/assets/js/shared/hero-parallax.js ] && ok "hero-parallax.js shipped" || no "hero-parallax.js"
[ "$(grep -l 'marquee' site/*.html 2>/dev/null | wc -l)" = "0" ] && ok "carousel removed from all pages" || no "marquee html"
[ "$(grep -rl '\.mq-' site/assets/css/ 2>/dev/null | wc -l)" = "0" ] && ok "marquee CSS swept" || no "mq css"
[ "$(grep -rl 'mqTrack' site/assets/js/ 2>/dev/null | wc -l)" = "0" ] && ok "marquee JS swept" || no "mqtrack js"
[ "$(grep -l 'id="heroBg"' site/*.html | wc -l)" = "16" ] && ok "16 parallax photo heroes" || no "herobg count"
[ "$(grep -l 'hero-parallax.js' site/*.html | wc -l)" = "11" ] && ok "11 hero-parallax includes" || no "parallax includes"
[ "$(grep -rn 'footer[^}]*navy-3' site/assets/css/ | wc -l)" = "0" ] && ok "no navy-3 footer rules" || no "footer navy-3"
grep -q 'path\.w1' site/assets/css/pages/support-us.css && ok "black-wave selector fix present" || no "wave selector"

# squad QR cards (owner request, folded into rev 21)
[ -f site/assets/js/vendor/qr.min.js ] && ok "self-hosted QR lib shipped (no CDN)" || no "qr lib"
grep -q 'assets/js/vendor/qr.min.js?v1' site/the-squad.html && grep -q 'id="mQr"' site/the-squad.html && grep -q 'id="mQrLink"' site/the-squad.html && ok "squad modal QR markup + lib include" || no "qr markup"
grep -q "encodeURIComponent(pref)" site/assets/js/pages/the-squad.js && grep -q "p.ref || ''" site/assets/js/pages/the-squad.js && grep -q "SQUAD_CODE" site/assets/js/pages/the-squad.js && ok "QR ref plumbing (live API refs + demo squad-code refs)" || no "qr refs"
grep -q 'qrcode-generator' site/assets/js/vendor/qr.min.js && ! grep -q 'eval(' site/assets/js/vendor/qr.min.js && ! grep -q 'new Function' site/assets/js/vendor/qr.min.js && ok "QR lib MIT-attributed + eval-free (CSP-safe)" || no "qr lib hygiene"
grep -q 'DEMO_PROFILES' site/assets/js/shared/sp-player.js && grep -q "'U19-10'" site/assets/js/shared/sp-player.js && ok "player page demo-profile fallback (captain seeded)" || no "demo profiles"
grep -q '.m-qr' site/assets/css/pages/the-squad.css && ok "QR card styling present" || no "qr css"
grep -q 'test_squad_player_cards_carry_unique_qr' backend/submissions/tests/test_phase7.py && ok "QR wiring test shipped (suite = 163)" || no "qr test"
grep -q 'unique QR' CHANGELOG-REV21.md && grep -q 'squad QR' FIX-NOTES-FORM-SYNC.txt && grep -q 'PLAYER QR CARDS' templates/POST-INSTALL-README.txt && ok "QR folded into all rev-21 docs" || no "qr docs"
[ -f CHANGELOG-REV21.md ] && ok "CHANGELOG-REV21.md present" || no "changelog"
grep -q "KIT REVISION 21" FIX-NOTES-FORM-SYNC.txt && ok "FIX-NOTES rev 21" || no "fixnotes"
grep -q "kit rev 21" PRODUCTION-READINESS.md && grep -q "T83" PRODUCTION-READINESS.md && ok "readiness rev 21 + evidence T79-T83" || no "readiness"
grep -q "WHAT REVISION 21 CHANGED" templates/POST-INSTALL-README.txt && ok "POST-INSTALL rev 21" || no "postinstall"
grep -q "parents\[3\] / 'site'" backend/submissions/tests/test_phase7.py && ! grep -rq "/home/z/" backend/submissions/tests/test_phase7.py && ok "test suite path-portable" || no "test path"

# prior-phase regression markers (rev 20)
[ -f site/robots.txt ] && grep -q "Disallow: /portal/" site/robots.txt && ok "robots.txt with portal/admin/api/media disallow" || no "robots.txt"
[ -f site/sitemap.xml ] && [ "$(grep -c '<loc>' site/sitemap.xml)" = "23" ] && ok "sitemap.xml 23 public URLs" || no "sitemap.xml"
[ "$(grep -l 'rel="canonical"' site/*.html | wc -l)" = "39" ] && ok "canonical on 39 public pages" || no "canonical count"
[ "$(grep -l 'property="og:image"' site/*.html | wc -l)" = "39" ] && ok "og:image on 39 public pages" || no "og count"
[ "$(grep -l 'rel="icon"' site/404.html site/50x.html | wc -l)" = "2" ] && ok "favicon on error pages" || no "error favicons"
grep -q "Ten gateways" site/join-us.html && grep -q "Main Pathways" site/join-us.html && grep -q "Other Forms" site/join-us.html && ok "forms hub groups + heading" || no "forms hub"
grep -q "Sponsorship Application (Form 06)" site/join-us.html && grep -q "Form 08: Contact" site/join-us.html && grep -q "Form 09: Media" site/join-us.html && ok "forms 06/08/09 on join-us" || no "form links"
grep -q "replies within a few working days" site/contact.html && grep -q "OWNER: confirm response time" site/contact.html && ok "contact response-time line + OWNER comment" || no "response time"
grep -q "Teams · U9 → Féminin" site/contact.html && ok "contact stat 3 replaced" || no "contact stat"
grep -q "Mtwapa · Kilifi County · Since 2020" site/index.html && ok "index hero label" || no "hero label"
grep -q "A Community United" site/index.html && ok "pillar 06 retitled" || no "pillar 06"
grep -q "01 · Who We Are" site/about-us.html && grep -q "01 · Why Partner With Us" site/partners.html && grep -q "01 · Our Safeguarding Commitment" site/safeguarding.html && ok "eyebrow renumbering" || no "renumber"
grep -q "repeat(3,1fr)" site/assets/css/shared/bl14m-hero-600.css && grep -q "font-size:0.75rem" site/assets/css/shared/bl14m-hero-600-b.css && ok "mobile stat grids + 12px labels" || no "stat grids"
grep -q "rgba(251,250,247,.68)" site/assets/css/pages/leadership-governance.css && ok "contrast alphas lifted" || no "contrast"
grep -q "margin-bottom:1.5rem" site/assets/css/pages/policy.css && ok "policy spacing" || no "policy spacing"
[ "$(stat -c%s site/logo.png)" -lt 200000 ] && [ "$(stat -c%s site/feminin-hero.jpg)" -lt 200000 ] && [ "$(stat -c%s site/sp-coach-address.jpg)" -lt 200000 ] && ok "three images under 200KB" || no "image sizes"
[ "$(grep -o 'loading="lazy"' site/*.html | wc -l)" -ge 200 ] && ok "lazy-loading present (209)" || no "lazy"
grep -q "sp-team-huddle.jpg" site/assets/css/pages/the-squad.css && ! grep -rq "Pearls/radoms" site/ && ok "squad CSS 404 fixed" || no "squad css"
grep -q "SEO origin" install.sh && ok "install.sh SEO origin re-pointing" || no "install seo"
[ -f CHANGELOG-REV20.md ] && ok "CHANGELOG-REV20.md retained" || no "changelog 20"

# prior-phase regression markers (rev 13-19)
grep -rq "form-10-safeguarding-report" backend/submissions/ && grep -q "SafeguardingReport" backend/submissions/views.py && ok "form-10 restricted route + model (P1)" || no "form-10"
[ -f backend/submissions/portal_dso.py ] && [ -f backend/submissions/management/commands/sp_dso.py ] && ok "DSO desk + command (P1)" || no "dso"
grep -q "script-src 'self'" backend/submissions/middleware.py && ok "CSP script-src self (P5)" || no "csp"
grep -q "healthz" backend/sporting_pearls_backend/urls.py && ok "healthz probe (P5)" || no "healthz"
grep -q "def media_serve" backend/submissions/portal.py && ok "media gating (P5)" || no "media gate"
[ -f backend/submissions/migrations/0005_coach.py ] && grep -q "path('coaches/'" backend/submissions/urls.py && ok "coaches API (P4)" || no "coaches"
[ -f backend/submissions/migrations/0006_result.py ] && grep -q "path('results/'" backend/submissions/urls.py && ok "results API (P7)" || no "results"
[ -f backend/submissions/portal_qr.py ] && grep -q "path('players/<slug:ref>/'" backend/submissions/urls.py && ok "QR + player API (P7)" || no "qr"
[ -f site/results.html ] && [ -f site/player.html ] && ok "results + player pages (P7)" || no "pages"
[ -f scripts/p6_acceptance.sh ] && [ -f scripts/phase0_guard_tests.py ] && ok "acceptance + guard scripts shipped" || no "scripts"
[ -f scripts/p8_verify.py ] && [ -f scripts/p8_browser_qa.sh ] && ok "rev-20 QA scripts shipped" || no "p8 scripts"
[ -f SAFEGUARDING-RUNBOOK.md ] && grep -q "24 months" SAFEGUARDING-RUNBOOK.md && ok "retention policy (P4)" || no "retention"
grep -q "KIT REVISION 20" FIX-NOTES-FORM-SYNC.txt && ok "FIX-NOTES rev 20 retained" || no "fixnotes 20"

# hygiene
! unzip -l "$OUT" | grep -qE "db\.sqlite3|\.env$|\.venv|__pycache__|media/players|\.git/" && ok "no db/.env/venv/cache/media/.git in zip" || no "hygiene"
! grep -rqiE "facebook\.com|instagram\.com|twitter\.com|tiktok\.com|youtube\.com|whatsapp\.com|linkedin\.com" site/ --include="*.html" && ok "no social links anywhere" || no "socials"
[ "$(grep -rhoE '[\w.+-]+@[\w-]+\.[\w.]+' site/*.html | grep -v sportingpearlsacademy.org | wc -l)" = "0" ] && ok "no published emails (enquiry policy)" || no "emails"

echo ""
echo "IN-ZIP CHECKS: $P pass, $F fail"
[ "$F" = "0" ] && echo "BUILD v21 OK" || { echo "BUILD v21 FAILED"; exit 1; }
