#!/usr/bin/env bash
# Phase 6 — REAL-WORLD ACCEPTANCE TEST (fictional data only).
#
# Runs against an INSTALLED kit (the sp-app/ directory install.sh creates),
# not the kit sources — exactly the path an owner takes.
#
# Usage:
#   SP_APP=/path/to/sp-app \
#   SP_ADMIN_PASS='the-install-admin-password' \
#   SP_DEMO_PASS='the-demo-parent-password-from-the-install-banner' \
#   bash scripts/p6_acceptance.sh
#
# SP_APP defaults to ../sp-app relative to this script (the standard layout
# after extracting the kit and running install.sh in the kit root).
# Optional: SP_BASE (default http://127.0.0.1:8020), SP_SBASE (site, :8090).
#
# The script CREATES its own fictional accounts (accept_staff, accept_admin,
# accept_dso, two guardians, two players) inside the installed database and
# leaves them there — remove them after staging sign-off if you wish.
#
# Covers: liveness, service restart, static site, headers/CSP, public form
# submissions + guards, parent portal (demo data), staff portal + redaction,
# DSO desk end-to-end + audit, enumeration-free resets (full link flow),
# media gating matrix, upload hardening, branded 404, login throttles,
# and the backup/restore drill. Login-throttle tests run LAST by design
# (they burn the local IP's failure budget for 15 minutes — a backend
# restart via sp.sh clears it, which the script does up front anyway).
set -uo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
APP="${SP_APP:-$(cd "$HERE/.." && pwd)/sp-app}"
BACKEND=$APP/backend
PY=$BACKEND/.venv/bin/python
BASE="${SP_BASE:-http://127.0.0.1:8020}"
SBASE="${SP_SBASE:-http://127.0.0.1:8090}"
SITE="$(cd "$HERE/.." && pwd)/site"
ADMIN_USER="${SP_ADMIN_USER:-admin}"
ADMIN_PASS="${SP_ADMIN_PASS:?set SP_ADMIN_PASS to the admin password you installed with}"
DEMO_USER="${SP_DEMO_USER:-demo.parent@example.com}"
DEMO_PASS="${SP_DEMO_PASS:?set SP_DEMO_PASS to the demo-parent password shown once in the install banner}"
[ -d "$BACKEND" ] || { echo "ERROR: no backend at $BACKEND — set SP_APP to your sp-app directory"; exit 2; }
WORK=$(mktemp -d)
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  PASS: $1"; }
bad() { FAIL=$((FAIL+1)); echo "  FAIL: $1"; }
section() { echo; echo "== $1 =="; }

# ---------- helpers ----------
login() { # $1=user $2=pass $3=jar $4=login_path -> 302?
  rm -f "$3"
  local tok code
  tok=$(curl -s -c "$3" "$BASE$4" | grep -o 'csrfmiddlewaretoken" value="[^"]*' | cut -d'"' -f3)
  code=$(curl -s -b "$3" -c "$3" -o /dev/null -w '%{http_code}' \
    -d "csrfmiddlewaretoken=$tok&username=$1&password=$2&next=/portal/" "$BASE$4")
  [ "$code" = "302" ]
}
csrfjar() { awk '$6 ~ /csrftoken/ {print $7}' "$1" | tail -1; }
api() { # $1=slug $2=json -> http code (body in $WORK/resp.json)
  curl -s -o "$WORK/resp.json" -w '%{http_code}' -X POST \
    -H 'Content-Type: application/json' --data "$2" "$BASE/api/forms/$1/"
}

# ---------- A. liveness + ops ----------
section "A. Liveness & service restart (real ops path)"
C=$(curl -s -o "$WORK/hz" -w '%{http_code}' "$BASE/healthz/")
[ "$C" = "200" ] && grep -q '"ok": *true' "$WORK/hz" && ok "healthz 200 + ok:true" || bad "healthz: $C"
C=$(curl -s -o "$WORK/hz2" -w '%{http_code}' "$BASE/")
[ "$C" = "200" ] && grep -q '"ok": *true' "$WORK/hz2" && ok "root health path 200" || bad "root health: $C"

( cd "$APP" && bash sp.sh stop >/dev/null 2>&1 )
sleep 1
C=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$BASE/healthz/" || true)
[ "$C" != "200" ] && ok "sp.sh stop actually stops the API" || bad "API still up after stop"
( cd "$APP" && bash sp.sh start >/dev/null 2>&1 )
for _ in $(seq 1 40); do curl -sf -o /dev/null "$BASE/healthz/" && break; sleep 0.5; done
C=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/healthz/")
[ "$C" = "200" ] && ok "sp.sh start brings the API back (healthz 200)" || bad "restart failed: $C"
C=$(curl -s -o /dev/null -w '%{http_code}' "$SBASE/" )
[ "$C" = "200" ] && ok "static site still serving after restart" || bad "site: $C"
# Regression guard (Phase 6 finding): the default install MUST run a single
# gunicorn worker — login/reset throttles count in the process-local cache,
# and --workers 3 diluted them below their thresholds (R28 in the wild).
NW=$(pgrep -fc "gunicorn sporting_pearls" || true)
[ "$NW" = "2" ] && ok "gunicorn runs ONE worker (master+1) — throttles effective" || bad "gunicorn process count: $NW (throttles diluted!)"

# ---------- B. static site ----------
section "B. Static site (installed copy)"
for p in index.html form-01-player-registration.html form-10-safeguarding-report.html policy-data-privacy.html; do
  C=$(curl -s -o /dev/null -w '%{http_code}' "$SBASE/$p")
  [ "$C" = "200" ] && ok "site $p 200" || bad "site $p: $C"
done
curl -s "$SBASE/form-01-player-registration.html" -o "$WORK/f01.html"
grep -qi "birth certificate\|upi" "$WORK/f01.html" && bad "form-01 still shows ID fields" || ok "form-01 minimised (no cert/UPI fields)"
grep -qi "conditions / allergies\|allergies" "$WORK/f01.html" && ok "form-01 health note present" || bad "form-01 health note missing"
grep -q "policy-data-privacy.html" "$WORK/f01.html" && ok "form-01 links privacy notice" || bad "form-01 privacy link missing"

# ---------- C. headers / CSP ----------
section "C. Security headers on live responses"
for path in /portal/login/ /admin/login/ /portal/definitely-missing/; do
  H=$(curl -sI "$BASE$path")
  if echo "$H" | grep -q "script-src 'self'" && ! echo "$H" | grep -q "script-src 'self' 'unsafe-inline'"; then
    ok "CSP script-src 'self' on $path"
  else
    bad "CSP on $path"
  fi
  echo "$H" | grep -qi "x-content-type-options: nosniff" && ok "nosniff on $path" || bad "nosniff on $path"
  echo "$H" | grep -qi "x-frame-options: DENY" && ok "XFO DENY on $path" || bad "XFO on $path"
done

# ---------- D. seed fictional accounts & players ----------
section "D. Seed fictional accounts (acceptance data)"
cd "$BACKEND"
"$PY" manage.py shell -c "
from django.contrib.auth.models import User, Group
from submissions.models import Squad, Player
from submissions.safeguarding import DSO_GROUP
from parents.models import Guardian, GuardianPlayer
sq,_ = Squad.objects.get_or_create(key='u13a', defaults={'code':'U13A','label':'U13 Acceptance'})
def ensure(ref, pub):
    p = Player.objects.filter(ref=ref).first() or Player(squad=sq, ref=ref, first_name='Accept', last_name=ref.replace('-',' '))
    p.is_published = pub; p.save(); return p
pubp = ensure('U13A-PUB', True); prvp = ensure('U13A-PRV', False)
def mkuser(u, e, pw, staff=False, grp=None):
    x = User.objects.filter(username=u).first() or User.objects.create_user(u, e, pw, is_staff=staff)
    x.set_password(pw)  # deterministic on re-runs
    x.is_staff = staff or x.is_staff
    x.save()
    if grp: x.groups.add(Group.objects.get(name=grp))
    return x
mkuser('accept_staff','staff.accept@example.com','Acc-Staff-7q!',staff=True)
mkuser('accept_admin','admin.accept@example.com','Acc-Admin-7q!',staff=True,grp='Portal Administrators')
mkuser('accept_dso','dso.accept@example.com','Acc-Dso-7q!',staff=True,grp=DSO_GROUP)
if not User.objects.filter(username='accept_own@example.com').exists():
    u = User.objects.create_user('accept_own@example.com','own.accept@example.com','Acc-Own-7q!')
    g = Guardian.objects.create(user=u, full_name='Own Acceptance')
    GuardianPlayer.objects.create(guardian=g, player=prvp)
if not User.objects.filter(username='accept_oth@example.com').exists():
    u2 = User.objects.create_user('accept_oth@example.com','oth.accept@example.com','Acc-Oth-7q!')
    Guardian.objects.create(user=u2, full_name='Other Acceptance')
print('SEEDED-OK')
" 2>&1 | grep -q "SEEDED-OK" && ok "fictional accounts seeded" || bad "seeding failed"
mkdir -p media/players
cp "$SITE/logo.png" media/players/acc_pub.png
cp "$SITE/logo.png" media/players/acc_priv.png
"$PY" manage.py shell -c "
from submissions.models import Player
Player.objects.filter(ref='U13A-PUB').update(photo='players/acc_pub.png')
Player.objects.filter(ref='U13A-PRV').update(photo='players/acc_priv.png')
print('PHOTOS-OK')
" 2>&1 | grep -q "PHOTOS-OK" && ok "fictional player photos set" || bad "photo seed failed"

# ---------- E. public form submissions ----------
section "E. Public form submissions (fictional)"
code=$(api form-01-player-registration '{"data":{"first name":"Acceptance","last name":"Junior","guardian phone":"+254700111222"}}')
[ "$code" = "200" ] && ok "form-01 fictional registration 200" || bad "form-01: $code"
ref=$(python3 -c "import json;print(json.load(open('$WORK/resp.json')).get('ref',''))" 2>/dev/null)
case "$ref" in SP-*) ok "form-01 real reference ($ref)";; *) bad "form-01 ref: $ref";; esac
code=$(api form-02-trial-application '{"data":{"first name":"Trial","last name":"Candidate","medical declaration / pre-existing conditions":"Acceptance-Asthma-7x"}}')
[ "$code" = "200" ] && ok "form-02 trial (with medical canary) 200" || bad "form-02: $code"
REF02=$(python3 -c "import json;print(json.load(open('$WORK/resp.json')).get('ref',''))" 2>/dev/null)
code=$(api form-08-contact-form '{"data":{"name":"Acceptance Visitor","message":"Acceptance test message"}}')
[ "$code" = "200" ] && ok "form-08 contact 200" || bad "form-08: $code"
code=$(api newsletter-subscription '{"data":{"enter your email address":"fan.accept@example.com"}}')
[ "$code" = "200" ] && ok "newsletter with email 200" || bad "newsletter: $code"

section "E2. Server guards (shape/content)"
code=$(api form-08-contact-form '{"data":{"name":"x"}}')
[ "$code" = "400" ] && ok "junk payload 400" || bad "junk payload: $code"
code=$(api form-10-safeguarding-report '{"data":{"reporting preference":"Completely Anonymous"}}')
[ "$code" = "400" ] && ok "empty safeguarding report 400" || bad "empty report: $code"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
  --data "{\"data\":{\"a\":\"$(python3 -c 'print("y"*70000)')\",\"b\":\"z\"}}" "$BASE/api/forms/form-08-contact-form/")
[ "$code" = "413" ] && ok "oversize body 413" || bad "oversize: $code"

# ---------- F. form-10 + DSO desk ----------
section "F. Form-10 + DSO desk end-to-end"
code=$(api form-10-safeguarding-report '{"data":{"reporting preference":"Completely Anonymous","detailed factual description of the concern / incident":"Acceptance QA fictional concern at the training pitch."}}')
[ "$code" = "200" ] && ok "form-10 anonymous report 200" || bad "form-10: $code"
REF10=$(python3 -c "import json;print(json.load(open('$WORK/resp.json')).get('ref',''))" 2>/dev/null)
case "$REF10" in SP-SAFE-*) ok "form-10 SP-SAFE reference ($REF10)";; *) bad "form-10 ref: $REF10";; esac

login accept_staff 'Acc-Staff-7q!' "$WORK/staff.ck" /portal/login/ && ok "staff login 302" || bad "staff login"
curl -s -b "$WORK/staff.ck" -o "$WORK/sdash.html" "$BASE/portal/"
grep -q "$REF10" "$WORK/sdash.html" && bad "staff dashboard leaks safeguarding ref" || ok "staff dashboard blind to SP-SAFE ref"
grep -q 'Safeguarding desk' "$WORK/sdash.html" && bad "staff sees DSO nav" || ok "staff has no DSO nav item"
C=$(curl -s -b "$WORK/staff.ck" -o /dev/null -w '%{http_code}' "$BASE/portal/dso/")
[ "$C" = "403" ] && ok "staff GET /portal/dso/ -> 403" || bad "staff dso desk: $C"

# superuser without role: neutral 403
rm -f "$WORK/root.ck"
tok=$(curl -s -c "$WORK/root.ck" "$BASE/admin/login/" | grep -o 'csrfmiddlewaretoken" value="[^"]*' | cut -d'"' -f3)
C=$(curl -s -b "$WORK/root.ck" -c "$WORK/root.ck" -o /dev/null -w '%{http_code}' \
  -d "csrfmiddlewaretoken=$tok&username=$ADMIN_USER&password=$ADMIN_PASS&next=/admin/" "$BASE/admin/login/")
[ "$C" = "302" ] && ok "superuser admin login 302" || bad "admin login: $C"
C=$(curl -s -b "$WORK/root.ck" -o /dev/null -w '%{http_code}' "$BASE/portal/dso/")
[ "$C" = "403" ] && ok "superuser WITHOUT role -> 403 (not exempt)" || bad "superuser dso: $C"

# DSO journey
login accept_dso 'Acc-Dso-7q!' "$WORK/dso.ck" /portal/login/ && ok "DSO login 302" || bad "DSO login"
curl -s -b "$WORK/dso.ck" -o "$WORK/dqueue.html" "$BASE/portal/dso/"
grep -q "$REF10" "$WORK/dqueue.html" && ok "DSO queue lists the report" || bad "report not in queue"
grep -q "Acceptance QA fictional concern" "$WORK/dqueue.html" && bad "queue shows narrative" || ok "queue hides narrative"
curl -s -b "$WORK/dso.ck" -o "$WORK/ddetail.html" "$BASE/portal/dso/r/$REF10/"
grep -q "Acceptance QA fictional concern" "$WORK/ddetail.html" && ok "detail shows narrative to DSO" || bad "detail missing narrative"
CSRF=$(csrfjar "$WORK/dso.ck")
# status -> under_review
curl -s -b "$WORK/dso.ck" -H "X-CSRFToken: $CSRF" -H "Referer: $BASE/portal/dso/" \
  -d "action=status&status=under_review" -o /dev/null "$BASE/portal/dso/r/$REF10/"
curl -s -b "$WORK/dso.ck" -o "$WORK/ddetail2.html" "$BASE/portal/dso/r/$REF10/"
grep -q "Under review" "$WORK/ddetail2.html" && ok "status changed to Under review" || bad "status change failed"
# case note
curl -s -b "$WORK/dso.ck" -H "X-CSRFToken: $CSRF" -H "Referer: $BASE/portal/dso/" \
  --data-urlencode "action=note" --data-urlencode "note=Acceptance QA: initial assessment done (fictional)." \
  -o /dev/null "$BASE/portal/dso/r/$REF10/"
curl -s -b "$WORK/dso.ck" -o "$WORK/daudit.html" "$BASE/portal/dso/audit/"
for marker in received notified viewed; do
  grep -q "$marker" "$WORK/daudit.html" && ok "audit shows $marker" || bad "audit missing $marker"
done
grep -q "status_changed" "$WORK/daudit.html" && ok "audit shows status_changed" || bad "audit missing status_changed"
grep -q "note_added" "$WORK/daudit.html" && ok "audit shows note_added" || bad "audit missing note_added"
grep -q "Acceptance QA: initial assessment" "$WORK/daudit.html" && ok "case note visible in audit trail" || bad "note not in audit"

# ---------- G. parent portal (demo data) ----------
section "G. Parent portal journey (demo guardian, fictional)"
login "$DEMO_USER" "$DEMO_PASS" "$WORK/parent.ck" /portal/parents/login/ \
  && ok "demo parent login 302" || bad "demo parent login"
curl -s -b "$WORK/parent.ck" -o "$WORK/phome.html" "$BASE/portal/parents/"
[ -s "$WORK/phome.html" ] && grep -q "U15" "$WORK/phome.html" && ok "parent home shows own child (U15)" || bad "parent home missing child"
for p in announcements complaints account; do
  C=$(curl -s -b "$WORK/parent.ck" -o "$WORK/p_$p.html" -w '%{http_code}' "$BASE/portal/parents/$p/")
  [ "$C" = "200" ] && ok "parent $p 200" || bad "parent $p: $C"
done
grep -qi "training fee\|goal net\|bus" "$WORK/p_complaints.html" && ok "demo complaints visible" || bad "complaints list empty"
# parent must NOT see other children / staff data
grep -q "U13A-PRV" "$WORK/phome.html" && bad "parent sees fictional staff-side player" || ok "parent home scoped to own children"

# ---------- H. staff ledger + redaction ----------
section "H. Staff ledger + medical redaction (R26)"
login accept_admin 'Acc-Admin-7q!' "$WORK/admin.ck" /portal/login/ && ok "portal-admin login 302" || bad "admin login"
staff_json=$(curl -s -b "$WORK/staff.ck" "$BASE/portal/" | grep -o 'id="subs-json">[^<]*' | sed 's/id="subs-json">//')
admin_json=$(curl -s -b "$WORK/admin.ck" "$BASE/portal/" | grep -o 'id="subs-json">[^<]*' | sed 's/id="subs-json">//')
echo "$staff_json" | grep -q "Acceptance-Asthma-7x" \
  && bad "plain staff SEES medical canary" || ok "plain staff: medical value masked"
echo "$staff_json" | grep -qi "withheld\|restricted" && ok "plain staff: restriction marker present" || bad "no restriction marker"
echo "$staff_json" | grep -q '"first name": "Acceptance"' && ok "plain staff: ordinary data visible" || bad "ordinary data hidden from staff"
echo "$admin_json" | grep -q "Acceptance-Asthma-7x" && ok "portal admin: full medical value visible" || bad "admin cannot see medical value"
echo "$staff_json" | grep -q "$REF10" && bad "ledger leaks SP-SAFE ref to staff" || ok "ledger blind to safeguarding"

# ---------- I. password reset (both portals, full link flow) ----------
section "I. Enumeration-free password reset"
for portal_path in "portal/reset" "portal/parents/reset"; do
  rm -f "$WORK/rst.ck"
  tok=$(curl -s -c "$WORK/rst.ck" "$BASE/$portal_path/" | grep -o 'csrfmiddlewaretoken" value="[^"]*' | cut -d'"' -f3)
  R=$(curl -s -b "$WORK/rst.ck" -c "$WORK/rst.ck" -w '\n%{http_code}' \
    -d "csrfmiddlewaretoken=$tok&identify=ghost-unknown@example.com" "$BASE/$portal_path/")
  CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
  [ "$CODE" = "200" ] && ok "$portal_path: unknown account 200 (neutral)" || bad "$portal_path unknown: $CODE"
  echo "$BODY" | grep -qi "check your inbox" && ok "$portal_path: neutral wording" || bad "$portal_path wording"
  echo "$BODY" | grep -qi "ghost-unknown" && bad "$portal_path echoes typed address" || ok "$portal_path echoes nothing"
done
LINK=$("$PY" - << PY
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','sporting_pearls_backend.settings')
django.setup()
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from base64 import urlsafe_b64encode
u = get_user_model().objects.get(username='accept_staff')
print(f"/portal/reset/{urlsafe_b64encode(str(u.pk).encode()).decode()}/{default_token_generator.make_token(u)}/")
PY
)
C=$(curl -s -o "$WORK/set1" -w '%{http_code}' "$BASE$LINK")
[ "$C" = "200" ] && grep -q "Choose a new password" "$WORK/set1" && ok "reset link opens form" || bad "link GET $C"
rm -f "$WORK/set.ck"
tok=$(curl -s -c "$WORK/set.ck" "$BASE$LINK" | grep -o 'csrfmiddlewaretoken" value="[^"]*' | cut -d'"' -f3)
C=$(curl -s -b "$WORK/set.ck" -o "$WORK/set2" -w '%{http_code}' \
  -d "csrfmiddlewaretoken=$tok&password=Acc-Staff-8q!&password2=Acc-Staff-8q!" "$BASE$LINK")
grep -q "Password saved" "$WORK/set2" && ok "password set via link" || bad "set failed ($C)"
C=$(curl -s -o /dev/null -w '%{http_code}' "$BASE$LINK")
[ "$C" = "400" ] && ok "used link dead (400)" || bad "dead link: $C"
login accept_staff 'Acc-Staff-8q!' "$WORK/staff2.ck" /portal/login/ && ok "new password signs in" || bad "login after reset"

# ---------- J. media gating ----------
section "J. Media gating matrix"
C=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/media/players/acc_pub.png"); [ "$C" = "200" ] && ok "published photo anon 200" || bad "pub anon: $C"
C=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/media/players/acc_priv.png"); [ "$C" = "404" ] && ok "unpublished photo anon 404" || bad "priv anon: $C"
C=$(curl -s -o /dev/null -w '%{http_code}' --path-as-is "$BASE/media/players/../../db.sqlite3"); [ "$C" = "404" ] && ok "traversal 404" || bad "traversal: $C"
C=$(curl -s -b "$WORK/staff2.ck" -o /dev/null -w '%{http_code}' "$BASE/media/players/acc_priv.png"); [ "$C" = "200" ] && ok "unpublished photo staff 200" || bad "priv staff: $C"
login 'accept_own@example.com' 'Acc-Own-7q!' "$WORK/own.ck" /portal/parents/login/ && ok "owning guardian login" || bad "own login"
C=$(curl -s -b "$WORK/own.ck" -o /dev/null -w '%{http_code}' "$BASE/media/players/acc_priv.png"); [ "$C" = "200" ] && ok "unpublished photo OWNING guardian 200" || bad "priv own: $C"
login 'accept_oth@example.com' 'Acc-Oth-7q!' "$WORK/oth.ck" /portal/parents/login/ && ok "other guardian login" || bad "oth login"
C=$(curl -s -b "$WORK/oth.ck" -o /dev/null -w '%{http_code}' "$BASE/media/players/acc_priv.png"); [ "$C" = "404" ] && ok "unpublished photo OTHER guardian 404" || bad "priv oth: $C"
C=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/portal/assets/dash.js"); [ "$C" = "404" ] && ok "dash.js anon 404" || bad "dash anon: $C"
C=$(curl -s -b "$WORK/staff2.ck" -o /dev/null -w '%{http_code}' "$BASE/portal/assets/dash.js"); [ "$C" = "200" ] && ok "dash.js staff 200" || bad "dash staff: $C"

# ---------- K. upload hardening ----------
section "K. Upload hardening (live)"
CSRF=$(csrfjar "$WORK/staff2.ck")
PID=$("$PY" - << PY
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','sporting_pearls_backend.settings')
django.setup()
from submissions.models import Player
print(Player.objects.get(ref='U13A-PUB').pk)
PY
)
printf 'definitely not an image at all' > "$WORK/fake.jpg"
R=$(curl -s -b "$WORK/staff2.ck" -H "X-CSRFToken: $CSRF" -H "Referer: $BASE/portal/" \
  -F "file=@$WORK/fake.jpg;type=image/jpeg" "$BASE/portal/players/$PID/photo/")
echo "$R" | grep -q "not a readable image" && ok "fake jpg rejected" || bad "fake jpg accepted: $R"
"$PY" - << PY
import io
from PIL import Image
buf = io.BytesIO()
img = Image.new('RGB', (60, 40), (10, 120, 200))
exif = Image.Exif(); exif[0x0112] = 6; exif[0x0131] = 'acceptance camera'
img.save(buf, 'JPEG', exif=exif)
open('$WORK/tracked.jpg','wb').write(buf.getvalue())
PY
R=$(curl -s -b "$WORK/staff2.ck" -H "X-CSRFToken: $CSRF" -H "Referer: $BASE/portal/" \
  -F "file=@$WORK/tracked.jpg;type=image/jpeg" "$BASE/portal/players/$PID/photo/")
echo "$R" | grep -q '"ok": true' && ok "real jpeg with EXIF accepted" || bad "jpeg rejected: $R"
STORED=$("$PY" - << PY
import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','sporting_pearls_backend.settings')
django.setup()
from submissions.models import Player
from PIL import Image
p = Player.objects.get(pk=$PID)
img = Image.open(p.photo)
ex = img.getexif()
print(json.dumps({"has_exif": bool(ex), "path": p.photo.name}))
PY
)
echo "$STORED" | grep -q '"has_exif": false' && ok "stored upload has no EXIF/GPS" || bad "EXIF survived: $STORED"

# ---------- L. branded 404 ----------
section "L. Branded 404"
R=$(curl -s -w '\n%{http_code}' "$BASE/portal/definitely-missing/")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
[ "$CODE" = "404" ] && ok "404 status" || bad "404 status: $CODE"
echo "$BODY" | grep -qi "does not exist\|not found" && ok "404 branded body" || bad "404 body wrong"
echo "$BODY" | grep -q "Traceback" && bad "404 leaks traceback" || ok "404 leaks nothing"
C=$(curl -s -o "$WORK/s404" -w '%{http_code}' "$SBASE/definitely-missing.html")
[ "$C" = "404" ] && grep -qi "not found\|does not exist" "$WORK/s404" && ok "static site 404 branded" || bad "site 404: $C"

# ---------- M. login throttles (LAST: burns this IP's budget) ----------
section "M. Login throttles (run last by design)"
for i in 1 2 3 4 5 6 7 8; do
  rm -f "$WORK/thr.ck"
  tok=$(curl -s -c "$WORK/thr.ck" "$BASE/portal/login/" | grep -o 'csrfmiddlewaretoken" value="[^"]*' | cut -d'"' -f3)
  curl -s -b "$WORK/thr.ck" -c "$WORK/thr.ck" -o /dev/null \
    -d "csrfmiddlewaretoken=$tok&username=accept_staff&password=wrong-$i&next=/portal/" "$BASE/portal/login/"
done
rm -f "$WORK/thr.ck"
tok=$(curl -s -c "$WORK/thr.ck" "$BASE/portal/login/" | grep -o 'csrfmiddlewaretoken" value="[^"]*' | cut -d'"' -f3)
C=$(curl -s -b "$WORK/thr.ck" -c "$WORK/thr.ck" -o "$WORK/thr.html" -w '%{http_code}' \
  -d "csrfmiddlewaretoken=$tok&username=accept_staff&password=wrong-9&next=/portal/" "$BASE/portal/login/")
[ "$C" = "429" ] && ok "9th staff login attempt throttled (429)" || bad "throttle: $C"
grep -qi "too many" "$WORK/thr.html" && ok "429 page is branded" || bad "429 body wrong"
# admin throttle (separate surface)
for i in 1 2 3 4 5 6 7 8; do
  rm -f "$WORK/thr2.ck"
  tok=$(curl -s -c "$WORK/thr2.ck" "$BASE/admin/login/" | grep -o 'csrfmiddlewaretoken" value="[^"]*' | cut -d'"' -f3)
  curl -s -b "$WORK/thr2.ck" -c "$WORK/thr2.ck" -o /dev/null \
    -d "csrfmiddlewaretoken=$tok&username=$ADMIN_USER&password=wrong-$i&next=/admin/" "$BASE/admin/login/"
done
rm -f "$WORK/thr2.ck"
tok=$(curl -s -c "$WORK/thr2.ck" "$BASE/admin/login/" | grep -o 'csrfmiddlewaretoken" value="[^"]*' | cut -d'"' -f3)
C=$(curl -s -b "$WORK/thr2.ck" -o /dev/null -w '%{http_code}' \
  -d "csrfmiddlewaretoken=$tok&username=$ADMIN_USER&password=wrong-9&next=/admin/" "$BASE/admin/login/")
[ "$C" = "429" ] && ok "admin login throttled too (429)" || bad "admin throttle: $C"

# ---------- N. backup + restore drill ----------
section "N. Backup + restore drill (installed script)"
( cd "$APP" && bash sp.sh backup >/dev/null 2>&1 )
BUNDLE=$(ls -t "$APP"/backups/sp-backup-*.tar.gz 2>/dev/null | head -1)
[ -n "$BUNDLE" ] && ok "backup bundle created ($(basename "$BUNDLE"))" || bad "no backup bundle"
DR=$(cd "$APP" && bash restore-drill.sh "$BUNDLE" 2>&1 | tail -14)
echo "$DR" | grep -q "RESTORE DRILL PASSED" && ok "restore drill PASS (real bundle, boots + counts match)" || { echo "$DR"; bad "restore drill failed"; }

echo
echo "=================================================="
echo "PHASE 6 ACCEPTANCE: $PASS passed, $FAIL failed"
echo "=================================================="
[ "$FAIL" = 0 ]
