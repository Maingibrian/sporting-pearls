#!/usr/bin/env bash
# Sporting Pearls — backup RESTORE DRILL (Phase 5, R14).
#
# A backup nobody has restored is a hope, not a backup. This drill proves
# a bundle actually restores: it extracts the newest sp-backup-*.tar.gz
# into a SCRATCH directory (the live backend is never touched), checks
# the restored SQLite file, boots a throwaway instance against the
# restored data, probes it over HTTP, and compares record counts with
# the live database.
#
# Usage:   bash restore-drill.sh [path/to/sp-backup-….tar.gz]
#          (default: newest bundle in <app>/backups/)
# Exit:    0 = every check passed, 1 = anything failed.
#
# Run it after the first install, after any upgrade, and at least once a
# quarter. Safe to run any time — it only reads the live database.

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP="${SP_APP:-$HERE}"                 # script sits at the app root
BACKEND="$APP/backend"
BACKUPS="$APP/backups"
DRILL_PORT="${SP_DRILL_PORT:-8099}"
PY="$BACKEND/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

fail=0
note() { printf '  %-10s %s\n' "$1" "$2"; }
check() { if [ "$1" -eq 0 ]; then note PASS "$2"; else note FAIL "$3"; fail=1; fi; }

echo "Sporting Pearls restore drill"
echo "app       : $APP"

# ── 1. locate the bundle ─────────────────────────────────────────────
BK="${1:-$(ls -1t "$BACKUPS"/sp-backup-*.tar.gz 2>/dev/null | head -n1)}"
if [ -z "$BK" ] || [ ! -f "$BK" ]; then
  note FAIL "no backup bundle found in $BACKUPS (run: bash sp.sh backup)"
  exit 1
fi
echo "bundle    : $BK"

SCRATCH="$(mktemp -d /tmp/sp-restore-drill.XXXXXX)"
trap 'kill "$SRV_PID" 2>/dev/null; rm -rf "$SCRATCH"' EXIT

# ── 2. extract into the scratch dir ──────────────────────────────────
tar -xzf "$BK" -C "$SCRATCH" 2>/dev/null
check $? "archive extracts cleanly" "archive is corrupt or incomplete"

# ── 3. the database file is there and passes SQLite's own check ─────
if [ -f "$SCRATCH/db.sqlite3" ]; then note PASS "db.sqlite3 present in bundle"
else note FAIL "db.sqlite3 missing from bundle"; exit 1; fi
"$PY" - "$SCRATCH/db.sqlite3" <<'PYEOF'
import sqlite3, sys
db = sqlite3.connect(f'file:{sys.argv[1]}?mode=ro', uri=True)
result = db.execute('PRAGMA integrity_check').fetchone()[0]
if result != 'ok':
    print(f'FAIL sqlite integrity_check said: {result}')
    raise SystemExit(1)
print('PASS sqlite integrity_check: ok')
PYEOF
[ $? -eq 0 ] || fail=1

# ── 4. media files came along (if the install has any) ───────────────
# (grep reads the whole listing: with -q it would exit early, tar would
# get SIGPIPE, and pipefail would misreport a healthy bundle)
if tar -tzf "$BK" 2>/dev/null | grep '^media/' >/dev/null; then
  note PASS "media/ included in bundle"
elif [ -d "$BACKEND/media" ] && [ -n "$(ls -A "$BACKEND/media" 2>/dev/null)" ]; then
  note FAIL "live media/ exists but is not in the bundle"
else
  note PASS "no media to carry (none on disk)"
fi

# ── 5. boot a throwaway instance on the restored data ────────────────
# DB_PATH/MEDIA_ROOT env vars win over backend/.env (settings reads the
# real environment first), so the live database is never at risk.
echo "boot      : throwaway instance on 127.0.0.1:$DRILL_PORT (restored data)"
DB_PATH="$SCRATCH/db.sqlite3" MEDIA_ROOT="$SCRATCH/media" \
  "$PY" "$BACKEND/manage.py" runserver "127.0.0.1:$DRILL_PORT" --noreload \
  >/dev/null 2>&1 &
SRV_PID=$!
up=1
for _ in $(seq 1 40); do
  if curl -sf -o /dev/null "http://127.0.0.1:$DRILL_PORT/healthz/"; then up=0; break; fi
  sleep 0.5
done
check $up "restored backend boots and /healthz/ answers 200" \
          "restored backend did not come up (see backend logs)"

if [ $up -eq 0 ]; then
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$DRILL_PORT/portal/login/")
  [ "$code" = "200" ]; check $? "staff portal login renders (HTTP $code)" "portal login broken (HTTP $code)"
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$DRILL_PORT/api/players/")
  [ "$code" = "200" ]; check $? "public players API answers (HTTP $code)" "players API broken (HTTP $code)"
fi
kill "$SRV_PID" 2>/dev/null; wait "$SRV_PID" 2>/dev/null

# ── 6. record counts match the live database ─────────────────────────
if [ -f "$BACKEND/db.sqlite3" ]; then
  "$PY" - "$BACKEND/db.sqlite3" "$SCRATCH/db.sqlite3" <<'PYEOF'
import sqlite3, sys
def counts(path):
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    out = {}
    for table in ('submissions_formsubmission', 'submissions_player',
                  'submissions_safeguardingreport', 'parents_guardian'):
        try:
            out[table] = db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        except sqlite3.OperationalError:
            out[table] = 'n/a'
    return out
live, restored = counts(sys.argv[1]), counts(sys.argv[2])
ok = True
for table in live:
    same = live[table] == restored[table]
    ok = ok and same
    print(f"{'PASS' if same else 'FAIL'} {table}: live={live[table]} restored={restored[table]}")
if not ok:
    raise SystemExit(1)
PYEOF
  check $? "record counts match the live database" \
           "record counts DIFFER from the live database (restore is not current)"
else
  note PASS "no live database on this host to compare against (fresh install)"
fi

echo
if [ $fail -eq 0 ]; then
  echo "RESULT: RESTORE DRILL PASSED — this bundle is a real, bootable backup."
else
  echo "RESULT: RESTORE DRILL FAILED — fix backups before you need them."
fi
exit $fail
