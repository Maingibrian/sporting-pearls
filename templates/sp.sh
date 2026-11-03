#!/usr/bin/env bash
# Sporting Pearls — service control (works from a cold shell: sources .env itself)
# Usage: bash sp.sh {status|start|stop|restart|logs|health|backup}
#   backup — snapshot db.sqlite3 (safe while running) + media/ + .env into
#           backups/sp-backup-<timestamp>.tar.gz; keeps the newest 14
set -u
APP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$APP/backend"
LOGS="$APP/logs"
mkdir -p "$LOGS"

# Cold-shell bootstrapping FIRST: load .env so port vars below can come from it.
if [ -f "$BACKEND/.env" ]; then
  set -a; . "$BACKEND/.env"; set +a
fi
export DJANGO_SETTINGS_MODULE=sporting_pearls_backend.settings
export PYTHONPATH="$BACKEND${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONUNBUFFERED=1
PY="$BACKEND/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

PORT_API="${SP_PORT_API:-8020}"
PORT_SITE="${SP_PORT_SITE:-8090}"
BIND="${SP_BIND:-0.0.0.0}"

api_pid()  { pgrep -f "gunicorn sporting_pearls_backend.wsgi" | head -1; }
site_pid() { pgrep -f "http.server $PORT_SITE" | head -1; }

start_api() {
  [ -n "$(api_pid)" ] && { echo "api     : already running (pid $(api_pid))"; return 0; }
  cd "$BACKEND"
  # BIND comes from SP_BIND (.env, default 0.0.0.0) so the API + portals are
  # reachable from other machines on the LAN — same as the website port.
  # Set SP_BIND=127.0.0.1 in backend/.env to keep the API loopback-only.
  # ONE process + threads (not --workers 3): the login/reset throttles count
  # in the process-local cache, and SQLite writes best from a single process.
  # Concurrency comes from gthread (--threads 8). To scale out later: move to
  # PostgreSQL + SP_CACHE=db (shared counters), then raise the worker count.
  nohup "$BACKEND/.venv/bin/gunicorn" sporting_pearls_backend.wsgi:application \
      --bind "$BIND:$PORT_API" --workers 1 --threads 8 --timeout 60 \
      >> "$LOGS/backend.log" 2>&1 < /dev/null &
  disown
  cd "$APP"
  sleep 1.5
  [ -n "$(api_pid)" ] && echo "api     : started (pid $(api_pid))" || echo "api     : FAILED to start — see $LOGS/backend.log"
}
start_site() {
  [ -n "$(site_pid)" ] && { echo "site    : already running (pid $(site_pid))"; return 0; }
  nohup "$PY" -m http.server "$PORT_SITE" --bind "$BIND" --directory "$APP/site" \
      >> "$LOGS/site.log" 2>&1 < /dev/null &
  disown
  sleep 1
  [ -n "$(site_pid)" ] && echo "site    : started (pid $(site_pid))" || echo "site    : FAILED to start — see $LOGS/site.log"
}
stop_pids() {
  local p
  for p in $(pgrep -f "$1"); do kill "$p" 2>/dev/null; done
}

case "${1:-status}" in
  start)
    start_api
    start_site
    ;;
  stop)
    stop_pids "gunicorn sporting_pearls_backend.wsgi"
    stop_pids "http.server $PORT_SITE"
    echo "stopped."
    ;;
  restart)
    "$APP/sp.sh" stop; sleep 1; "$APP/sp.sh" start
    ;;
  status)
    if [ -n "$(api_pid)" ];  then echo "backend  : RUNNING (pid $(api_pid),  port $PORT_API)"; else echo "backend  : STOPPED"; fi
    if [ -n "$(site_pid)" ]; then echo "site     : RUNNING (pid $(site_pid), port $PORT_SITE)"; else echo "site     : STOPPED"; fi
    ;;
  logs)
    echo "== backend.log (last 40) =="; tail -40 "$LOGS/backend.log" 2>/dev/null
    echo "== site.log (last 20) ==";    tail -20 "$LOGS/site.log" 2>/dev/null
    ;;
  health)
    curl -sf "http://127.0.0.1:$PORT_API/api/health/" && echo && exit 0
    echo "backend unhealthy"; exit 1
    ;;
  backup)
    TS="$(date +%Y%m%d-%H%M%S)"
    DEST="$APP/backups"
    mkdir -p "$DEST"
    # 1. consistent sqlite snapshot (online-safe: uses sqlite3 backup API)
    if [ -f "$BACKEND/db.sqlite3" ]; then
      ( cd "$BACKEND" && "$PY" - "db-$TS.sqlite3" <<'PYEOF'
import sqlite3, sys
s = sqlite3.connect('db.sqlite3')
d = sqlite3.connect(sys.argv[1])
with d: s.backup(d)
d.close(); s.close()
PYEOF
      ) && echo "db     : snapshot ok" || echo "db     : snapshot FAILED (services running? try again)"
    else
      echo "db     : no database yet (skipped)"
    fi
    # 2. bundle snapshot + uploads + .env (archive paths are relative to
    #    backend/ so restoring is a plain extract into backend/)
    ITEMS=".env"
    [ -f "$BACKEND/db-$TS.sqlite3" ] && ITEMS="db-$TS.sqlite3 $ITEMS"
    [ -d "$BACKEND/media" ]         && ITEMS="$ITEMS media"
    ( cd "$BACKEND" && tar -czf "$DEST/sp-backup-$TS.tar.gz" \
        --transform="s|^db-$TS.sqlite3$|db.sqlite3|" $ITEMS ) 2>/dev/null \
      || ( cd "$BACKEND" && tar -czf "$DEST/sp-backup-$TS.tar.gz" $ITEMS ) \
      || { echo "tar    : FAILED"; rm -f "$BACKEND/db-$TS.sqlite3"; exit 1; }
    rm -f "$BACKEND/db-$TS.sqlite3"
    # 3. rotate: keep the newest 14 bundles
    ls -1t "$DEST"/sp-backup-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
    echo "backup : $DEST/sp-backup-$TS.tar.gz"
    echo "restore: bash sp.sh stop && tar -xzf sp-backup-$TS.tar.gz -C backend/ && bash sp.sh start"
    echo "verify : bash restore-drill.sh   (proves a bundle restores — run it quarterly)"
    ;;
  *)
    echo "usage: bash sp.sh {status|start|stop|restart|logs|health|backup}"; exit 2
    ;;
esac
