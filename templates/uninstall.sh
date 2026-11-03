#!/usr/bin/env bash
# Sporting Pearls — uninstall (removes services + app dir; asks before deleting data)
set -u
APP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "This removes Sporting Pearls services and the app at: $APP"
if [ "$1" != "--yes" ]; then read -r -p "Type DELETE to continue: " a; [ "$a" = "DELETE" ] || exit 1; fi

# stop user-mode services
bash "$APP/sp-app/sp.sh" stop 2>/dev/null || true
pkill -f "gunicorn sporting_pearls_backend.wsgi" 2>/dev/null || true
pkill -f "http.server 8090" 2>/dev/null || true

# remove systemd units if present
if [ "$(id -u)" = "0" ] && command -v systemctl >/dev/null; then
  systemctl stop sp-backend.service sp-site.service 2>/dev/null || true
  systemctl disable sp-backend.service sp-site.service 2>/dev/null || true
  rm -f /etc/systemd/system/sp-backend.service /etc/systemd/system/sp-site.service
  systemctl daemon-reload 2>/dev/null || true
fi

echo "App folder left in place: $APP"
echo "Remove it manually when ready:  rm -rf $APP"
echo "(This keeps db.sqlite3 / media in case you need the data.)"
