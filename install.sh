#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
#  SPORTING PEARLS — one-shot server installer
#  Extract this kit, then:  bash install.sh [--demo-data]
#  Options:
#    --demo-data     seed demo guardians/announcements/complaints
#    --with-nginx    same-origin :80 front (root + nginx required)
#    --domain=NAME   production hardening: lock ALLOWED_HOSTS + CORS to NAME
#                    (e.g. --domain=sportingpearlsacademy.org); implies
#                    the public API origin https://NAME / http://NAME
#    --with-tls      HTTPS via Let's Encrypt (needs --domain, root, nginx,
#                    certbot; see EMAIL-SETUP-GUIDE / POST-INSTALL notes)
#    --tls-email=MAIL  registration email for certbot (else no email)
#    --production    verify + enable SP_ENV=production (fail-closed mode:
#                    the backend then refuses to boot on insecure config).
#                    Requires --domain and secure cookies (i.e. TLS live);
#                    the check runs BEFORE the flag is written, so an
#                    insecure install is left in development mode.
#    --port-api=N    backend port   (default 8020)
#    --port-site=N   website port   (default 8090)
#    --dir=PATH      install location (default ./sp-app; /opt for root)
#    --public-url=URL force the API origin written into the site JS
#    --no-start      install without starting services
#  Upgrade-safe: existing .env / db.sqlite3 / media are kept.
#  Re-running with --domain on an existing install tightens its .env.
# ══════════════════════════════════════════════════════════════════
set -u
cd "$(dirname "$0")"

DEMO=0; NGINX=0; START=1; PROD=0
PORT_API=8020; PORT_SITE=8090; APPDIR=""
DOMAIN=""; TLS=0; TLS_EMAIL=""; PUBLIC_URL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --demo-data) DEMO=1 ;;
    --with-nginx) NGINX=1 ;;
    --with-tls) TLS=1 ;;
    --production) PROD=1 ;;
    --no-start) START=0 ;;
    --port-api=*) PORT_API="${1#*=}" ;;
    --port-site=*) PORT_SITE="${1#*=}" ;;
    --dir=*) APPDIR="${1#*=}" ;;
    --domain=*) DOMAIN="${1#*=}" ;;
    --tls-email=*) TLS_EMAIL="${1#*=}" ;;
    --public-url=*) PUBLIC_URL="${1#*=}" ;;
    *) echo "unknown option: $1"; exit 2 ;;
  esac
  shift
done
[ "$TLS" = "1" ] && [ -z "$DOMAIN" ] && { echo "ERROR: --with-tls requires --domain=your.domain"; exit 2; }
[ "$PROD" = "1" ] && [ -z "$DOMAIN" ] && { echo "ERROR: --production requires --domain=your.domain (wildcard hosts are never allowed in production)"; exit 2; }
# strip scheme/paths if pasted from a browser bar
DOMAIN="${DOMAIN#http://}"; DOMAIN="${DOMAIN#https://}"; DOMAIN="${DOMAIN%/}"

IS_ROOT=0; [ "$(id -u)" = "0" ] && IS_ROOT=1
RUNUSER="$(id -un)"
[ -z "$APPDIR" ] && { if [ "$IS_ROOT" = "1" ]; then APPDIR="/opt/sporting-pearls/sp-app"; else APPDIR="./sp-app"; fi; }
APP="$(mkdir -p "$APPDIR" && cd "$APPDIR" && pwd)"
KIT="$(pwd)"
LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
[ -z "${LAN_IP:-}" ] && LAN_IP="127.0.0.1"

echo "══════════════════════════════════════════════════════"
echo " Sporting Pearls — installing"
echo "   app dir : $APP"
echo "   ports   : site $PORT_SITE · api $PORT_API"
echo "══════════════════════════════════════════════════════"

step() { printf '\n── %s ──\n' "$1"; }

# upsert key=value in the .env (replace if present, append otherwise)
ENVF=""
env_set() {
  if grep -q "^$1=" "$ENVF" 2>/dev/null; then
    sed -i "s|^$1=.*|$1=$2|" "$ENVF"
  else
    echo "$1=$2" >> "$ENVF"
  fi
}

# ── 1/9 layout ─────────────────────────────────────────────────────
step "1/9  Layout"
mkdir -p "$APP/logs" "$APP/site" "$APP/backend"
[ -d "$KIT/site" ]      && cp -r "$KIT/site/."      "$APP/site/"
[ -d "$KIT/backend" ]   && cp -r "$KIT/backend/."   "$APP/backend/"
chmod +x "$KIT/templates/sp.sh" 2>/dev/null || true
cp "$KIT/templates/sp.sh" "$APP/sp.sh" && chmod +x "$APP/sp.sh"
cp "$KIT/templates/restore-drill.sh" "$APP/restore-drill.sh" 2>/dev/null \
  && chmod +x "$APP/restore-drill.sh" || true
cp "$KIT/templates/POST-INSTALL-README.txt" "$APP/POST-INSTALL-README.txt" 2>/dev/null || true
cp "$KIT/EMAIL-SETUP-GUIDE.txt" "$APP/EMAIL-SETUP-GUIDE.txt" 2>/dev/null || true
cp "$KIT/REMOTE-ACCESS-GUIDE.txt" "$APP/REMOTE-ACCESS-GUIDE.txt" 2>/dev/null || true
cp "$KIT/templates/uninstall.sh" "$APP/uninstall.sh" 2>/dev/null || true
chmod +x "$APP/uninstall.sh" 2>/dev/null || true
echo "site + backend copied."

# ── 2/9 python venv (probe candidates by REALLY creating + ensurepip) ──
step "2/9  Python venv"
VENV="$APP/backend/.venv"
if [ -x "$VENV/bin/gunicorn" ]; then
  echo "existing venv OK (upgrade)."
else
  PYOK=""
  for CAND in python3.13 python3.12 python3.11 python3; do
    command -v "$CAND" >/dev/null 2>&1 || continue
    echo "probing $CAND …"
    rm -rf "$VENV"
    if "$CAND" -m venv "$VENV" 2>/dev/null \
       && "$VENV/bin/python" -m ensurepip --version >/dev/null 2>&1; then
      PYOK="$CAND"; echo "venv OK with $CAND"; break
    fi
  done
  [ -z "$PYOK" ] && { echo "ERROR: no python3 with working venv/ensurepip found."; exit 1; }
fi
"$VENV/bin/pip" install -q --upgrade pip 2>/dev/null || true
step "   pip requirements"
"$VENV/bin/pip" install -q -r "$APP/backend/requirements.txt" || { echo "pip install failed"; exit 1; }
"$VENV/bin/pip" install -q gunicorn || { echo "gunicorn install failed"; exit 1; }
echo "dependencies installed."

# ── 3/9 .env ───────────────────────────────────────────────────────
step "3/9  Environment (.env)"
ENVF="$APP/backend/.env"
if [ -f "$ENVF" ]; then
  echo "keeping existing .env (upgrade-safe)."
else
  SECRET="$("$VENV/bin/python" -c "import secrets;print(secrets.token_urlsafe(48))")"
  if [ -n "$DOMAIN" ]; then
    {
      echo "DJANGO_SECRET_KEY=$SECRET"
      echo "DEBUG=0"
      echo "# --domain=$DOMAIN: hosts/CORS locked to this domain"
      echo "# (localhost/127.0.0.1 kept for health checks + local admin access)"
      echo "ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,localhost,127.0.0.1"
      echo "CORS_ALLOW_ALL=0"
      echo "CORS_ALLOWED_ORIGINS=http://$DOMAIN,https://$DOMAIN,http://www.$DOMAIN,https://www.$DOMAIN"
      echo "AUTO_REPLY=1"
      echo "# plain HTTP until certificates are issued (--with-tls flips these)"
      echo "SESSION_COOKIE_SECURE=0"
      echo "CSRF_COOKIE_SECURE=0"
      echo "CSRF_TRUSTED_ORIGINS=http://$DOMAIN,https://$DOMAIN,http://www.$DOMAIN,https://www.$DOMAIN,http://localhost:$PORT_API,http://127.0.0.1:$PORT_API${PUBLIC_URL:+,$PUBLIC_URL}"
      echo "EMAIL_TO=info@sportingpearlsacademy.org"
      echo "# Safeguarding (form 10): DSO's PRIVATE inbox for minimal notifications."
      echo "# Leave unset until appointed — then: DSO_EMAIL=officer@example.com"
      echo "SITE_URL=http://$DOMAIN"
      echo "SP_PORT_API=$PORT_API"
      echo "SP_PORT_SITE=$PORT_SITE"
      echo "SP_BIND=0.0.0.0"
    } > "$ENVF"
    echo ".env written (domain-hardened; mail off — add RESEND_API_KEY, see EMAIL-SETUP-GUIDE.txt)."
  else
    {
      echo "DJANGO_SECRET_KEY=$SECRET"
      echo "DEBUG=0"
      echo "ALLOWED_HOSTS=*"
      echo "CORS_ALLOW_ALL=1"
      echo "AUTO_REPLY=1"
      echo "SESSION_COOKIE_SECURE=0"
      echo "CSRF_COOKIE_SECURE=0"
      echo "CSRF_TRUSTED_ORIGINS=http://localhost:$PORT_API,http://127.0.0.1:$PORT_API,http://$LAN_IP:$PORT_API${PUBLIC_URL:+,$PUBLIC_URL}"
      echo "EMAIL_TO=info@sportingpearlsacademy.org"
      echo "# Safeguarding (form 10): DSO's PRIVATE inbox for minimal notifications."
      echo "# Leave unset until appointed — then: DSO_EMAIL=officer@example.com"
      echo "SITE_URL=http://$LAN_IP:$PORT_SITE"
      echo "SP_PORT_API=$PORT_API"
      echo "SP_PORT_SITE=$PORT_SITE"
      echo "SP_BIND=0.0.0.0"
    } > "$ENVF"
    echo ".env written (mail off — add RESEND_API_KEY to enable email)."
  fi
fi
# re-running with --domain tightens an existing .env too (upgrade path)
if [ -n "$DOMAIN" ]; then
  env_set ALLOWED_HOSTS "$DOMAIN,www.$DOMAIN,localhost,127.0.0.1"
  env_set CORS_ALLOW_ALL 0
  env_set CORS_ALLOWED_ORIGINS "http://$DOMAIN,https://$DOMAIN,http://www.$DOMAIN,https://www.$DOMAIN"
  env_set CSRF_TRUSTED_ORIGINS "http://$DOMAIN,https://$DOMAIN,http://www.$DOMAIN,https://www.$DOMAIN,http://localhost:$PORT_API,http://127.0.0.1:$PORT_API${PUBLIC_URL:+,$PUBLIC_URL}"
  env_set SITE_URL "http://$DOMAIN"
  echo "hardened: ALLOWED_HOSTS + CORS locked to $DOMAIN"
fi
# keep runtime ports fresh even on upgrades
sed -i "s|^SP_PORT_API=.*|SP_PORT_API=$PORT_API|; s|^SP_PORT_SITE=.*|SP_PORT_SITE=$PORT_SITE|" "$ENVF" 2>/dev/null || true
# ensure SITE_URL exists on upgraded installs (never overwrites a custom value)
grep -q '^SITE_URL=' "$ENVF" 2>/dev/null || echo "SITE_URL=http://$LAN_IP:$PORT_SITE" >> "$ENVF"

# ── 4/9 database ───────────────────────────────────────────────────
step "4/9  Database migration"
( cd "$APP/backend" && set -a && . ./.env && set +a && \
  DJANGO_SETTINGS_MODULE=sporting_pearls_backend.settings PYTHONPATH="$APP/backend" \
  "$VENV/bin/python" manage.py migrate --noinput ) || { echo "migrate failed"; exit 1; }

# ── 5/9 admin account ──────────────────────────────────────────────
# No default password exists (Phase 0 hardening). Either:
#   * SP_ADMIN_PASS is set in the operator's environment → used, never echoed
#   * or a random 20-char password is generated and shown ONCE below
# An existing admin account is never reset by re-installing.
step "5/9  Admin account"
ADMIN_USER="${SP_ADMIN_USER:-admin}"
ADMIN_EXISTS=0; ADMIN_CREATED=0; ADMIN_PASS=""; ADMIN_PASS_SHOWN=0
EXISTS=$( cd "$APP/backend" && set -a && . ./.env && set +a && \
  DJANGO_SETTINGS_MODULE=sporting_pearls_backend.settings PYTHONPATH="$APP/backend" \
  "$VENV/bin/python" manage.py shell -c "
from django.contrib.auth import get_user_model
print(1 if get_user_model().objects.filter(username='$ADMIN_USER').exists() else 0)" 2>/dev/null | tail -1 )
[ "${EXISTS:-0}" = "1" ] && ADMIN_EXISTS=1

if [ "$ADMIN_EXISTS" = "1" ]; then
  echo "admin '$ADMIN_USER' already exists — password unchanged (never reset on re-install)."
else
  if [ -n "${SP_ADMIN_PASS:-}" ]; then
    ADMIN_PASS="$SP_ADMIN_PASS"
  else
    ADMIN_PASS="$("$VENV/bin/python" -c 'import secrets;print(secrets.token_urlsafe(15))')"
    ADMIN_PASS_SHOWN=1
  fi
  export DJANGO_SUPERUSER_USERNAME="$ADMIN_USER" DJANGO_SUPERUSER_PASSWORD="$ADMIN_PASS"
  export DJANGO_SUPERUSER_EMAIL="info@sportingpearlsacademy.org"
  ( cd "$APP/backend" && set -a && . ./.env && set +a && \
    DJANGO_SETTINGS_MODULE=sporting_pearls_backend.settings PYTHONPATH="$APP/backend" \
    DJANGO_SUPERUSER_USERNAME="$ADMIN_USER" DJANGO_SUPERUSER_PASSWORD="$ADMIN_PASS" \
    "$VENV/bin/python" manage.py ensure_superuser ) \
  || ( cd "$APP/backend" && set -a && . ./.env && set +a && \
    DJANGO_SETTINGS_MODULE=sporting_pearls_backend.settings PYTHONPATH="$APP/backend" \
    DJANGO_SUPERUSER_PASSWORD="$ADMIN_PASS" \
    "$VENV/bin/python" manage.py shell -c "
from django.contrib.auth import get_user_model
import os
U = get_user_model()
u, created = U.objects.get_or_create(username='$ADMIN_USER')
u.is_staff = True; u.is_superuser = True
u.email = 'info@sportingpearlsacademy.org'
u.set_password(os.environ['DJANGO_SUPERUSER_PASSWORD'])
u.save(); print('superuser ready (fallback creator)')" ) \
  || { echo "ERROR: admin account could not be created"; exit 1; }
  ADMIN_CREATED=1
  echo "admin '$ADMIN_USER' ready."
fi

# ── 6/9 roster + demo data ─────────────────────────────────────────
step "6/9  Roster & demo data"
( cd "$APP/backend" && set -a && . ./.env && set +a && \
  DJANGO_SETTINGS_MODULE=sporting_pearls_backend.settings PYTHONPATH="$APP/backend" \
  "$VENV/bin/python" manage.py import_roster ) || echo "(roster import skipped/failed — check player_seed.json)"
# always-on seeds (idempotent, cheap, run on fresh install AND upgrade)
for S in seed-victor-hero.py; do
  [ -f "$APP/backend/seeds/$S" ] || continue
  ( cd "$APP/backend" && set -a && . ./.env && set +a && \
    DJANGO_SETTINGS_MODULE=sporting_pearls_backend.settings PYTHONPATH="$APP/backend" \
    "$VENV/bin/python" "seeds/$S" ) && echo "seeded: $S" || echo "seed $S failed (non-fatal)"
done
if [ "$DEMO" = "1" ]; then
  EXISTS=$( cd "$APP/backend" && set -a && . ./.env && set +a && \
    DJANGO_SETTINGS_MODULE=sporting_pearls_backend.settings PYTHONPATH="$APP/backend" \
    "$VENV/bin/python" manage.py shell -c "
import parents.models as m
print(1 if m.Guardian.objects.exists() else 0)" 2>/dev/null | tail -1 )
  if [ "${EXISTS:-0}" = "1" ]; then
    echo "demo data already present — skipping seeds (upgrade-safe)."
  else
    # Demo parent credential: random per install (shown once in the banner),
    # fictional address — never a real person's email, never a fixed password.
    DEMO_PARENT_PASS="$("$VENV/bin/python" -c 'import secrets;print(secrets.token_urlsafe(12))')"
    DEMO_PARENT_EMAIL="${SP_DEMO_PARENT_EMAIL:-demo.parent@example.com}"
    export SP_DEMO_PARENT_PASS DEMO_PARENT_EMAIL
    DEMO_SEEDED=1
    for S in seed-demo-dashboard.py seed-announcements-p2.py seed-complaints-p3.py; do
      [ -f "$APP/backend/seeds/$S" ] || continue
      ( cd "$APP/backend" && set -a && . ./.env && set +a && \
        SP_DEMO_PARENT_PASS="$DEMO_PARENT_PASS" SP_DEMO_PARENT_EMAIL="$DEMO_PARENT_EMAIL" \
        DJANGO_SETTINGS_MODULE=sporting_pearls_backend.settings PYTHONPATH="$APP/backend" \
        "$VENV/bin/python" "seeds/$S" ) && echo "seeded: $S" || echo "seed $S failed (non-fatal)"
    done
  fi
fi

# ── 7/9 static + site JS wiring ────────────────────────────────────
step "7/9  Static files & site wiring"
( cd "$APP/backend" && set -a && . ./.env && set +a && \
  DJANGO_SETTINGS_MODULE=sporting_pearls_backend.settings PYTHONPATH="$APP/backend" \
  "$VENV/bin/python" manage.py collectstatic --noinput --clear >/dev/null 2>&1 ) && echo "collectstatic ok"
mkdir -p "$APP/backend/media"
# public API origin written into the site JS
if [ -n "$PUBLIC_URL" ]; then
  PUB="$PUBLIC_URL"
elif [ -n "$DOMAIN" ]; then
  # https only when we can actually issue certificates this run
  TLS_ELIG=0
  [ "$TLS" = "1" ] && [ "$IS_ROOT" = "1" ] && command -v nginx >/dev/null 2>&1 && command -v certbot >/dev/null 2>&1 && TLS_ELIG=1
  if [ "$TLS_ELIG" = "1" ]; then PUB="https://$DOMAIN"; else PUB="http://$DOMAIN"; fi
else
  if [ "$NGINX" = "1" ] && [ "$IS_ROOT" = "1" ] && command -v nginx >/dev/null 2>&1; then
    PUB="http://$LAN_IP"            # nginx :80 front — site + /api/ same origin
  else
    PUB="http://$LAN_IP:$PORT_API"  # two-port dev mode — API on the LAN (SP_BIND)
  fi
fi
CFG="$APP/site/assets/js/shared/site-config.js"
if [ -n "$PUBLIC_URL" ]; then
  # explicit re-point (upgrade-safe): always rewrite to the requested origin
  sed -i "s|API_BASE: \"[^\"]*\"|API_BASE: \"$PUB\"|" "$CFG" && echo "site-config.js API_BASE -> $PUB (re-pointed)"
elif [ -f "$CFG" ] && grep -q 'API_BASE: ""' "$CFG" 2>/dev/null; then
  sed -i "s|API_BASE: \"\"|API_BASE: \"$PUB\"|" "$CFG" && echo "site-config.js API_BASE -> $PUB"
else
  echo "site-config.js already wired (kept; re-run with --public-url=... to re-point)."
fi

# ── SEO origin (canonical / OG / sitemap / robots) ──────────────────
# The kit ships https://www.sportingpearlsacademy.org as a placeholder.
# When a domain (or explicit public URL) is known, re-point every
# canonical link, og:url tag, robots.txt and sitemap.xml in one pass.
# Idempotent: detects the currently-baked origin from sitemap.xml, so
# placeholder -> http://domain (no TLS yet) -> https://domain (TLS run)
# all work on re-runs.
SEO_OLD="https://www.sportingpearlsacademy.org"
SEO_NEW=""
if [ -n "$PUBLIC_URL" ]; then
  SEO_NEW="$PUBLIC_URL"
elif [ -n "$DOMAIN" ]; then
  if [ "$TLS_ELIG" = "1" ]; then SEO_NEW="https://$DOMAIN"; else SEO_NEW="http://$DOMAIN"; fi
fi
if [ -n "$SEO_NEW" ]; then
  SM="$APP/site/sitemap.xml"
  SEO_CUR="$SEO_OLD"
  if [ -f "$SM" ]; then
    DETECTED=$(sed -n 's|.*<loc>\(https\{0,1\}://[^/<]*\)/.*|\1|p' "$SM" | head -1)
    [ -n "$DETECTED" ] && SEO_CUR="$DETECTED"
  fi
  if [ "$SEO_CUR" != "$SEO_NEW" ]; then
    for F in "$APP/site/robots.txt" "$APP/site/sitemap.xml"; do
      [ -f "$F" ] && sed -i "s|$SEO_CUR|$SEO_NEW|g" "$F"
    done
    grep -rl "$SEO_CUR" "$APP/site" --include='*.html' 2>/dev/null | while read -r H; do
      sed -i "s|$SEO_CUR|$SEO_NEW|g" "$H"
    done
    echo "seo origin $SEO_CUR -> $SEO_NEW (robots/sitemap/canonical/og)"
  fi
fi

# ── 8/9 services ───────────────────────────────────────────────────
step "8/9  Services"
TLS_DONE=0
if [ "$IS_ROOT" = "1" ] && command -v systemctl >/dev/null 2>&1; then
  PYBIN="$VENV/bin/python"
  for TPL in sp-backend sp-site; do
    sed -e "s|__RUNUSER__|$RUNUSER|g" \
        -e "s|__APP__|$APP|g" \
        -e "s|__PORT_API__|$PORT_API|g" \
        -e "s|__PORT_SITE__|$PORT_SITE|g" \
        -e "s|__BIND__|0.0.0.0|g" \
        -e "s|__PY__|$PYBIN|g" \
        "$KIT/templates/$TPL.service" > "/etc/systemd/system/$TPL.service"
  done
  # daily backup (db + media + .env) at 02:30
  sed -e "s|__RUNUSER__|$RUNUSER|g" -e "s|__APP__|$APP|g" \
      "$KIT/templates/sp-backup.service" > /etc/systemd/system/sp-backup.service
  cp "$KIT/templates/sp-backup.timer" /etc/systemd/system/sp-backup.timer
  systemctl daemon-reload
  systemctl enable sp-backend.service sp-site.service >/dev/null 2>&1
  systemctl enable sp-backup.timer >/dev/null 2>&1 && systemctl start sp-backup.timer 2>/dev/null
  echo "systemd units installed (auto-start on boot; daily backup 02:30)."
else
  echo "user-mode services (nohup) — survive logout, not reboot. (backup: bash sp.sh backup)"
fi
if [ "$NGINX" = "1" ] && [ "$IS_ROOT" = "1" ] && command -v nginx >/dev/null 2>&1; then
  # nginx fronts the app -> HTTPS detection must trust X-Forwarded-Proto
  # (Phase 2: was trusted unconditionally in settings, letting direct
  # exposures spoof "I am HTTPS"; now it is opt-in per front)
  env_set TRUST_PROXY_HEADER 1
  # HTTP front first — also the ACME fallback if TLS cannot be issued
  sed -e "s|__APP__|$APP|g" -e "s|__PORT_API__|$PORT_API|g" \
    "$KIT/templates/nginx.conf" > /etc/nginx/sites-available/sporting-pearls.conf
  ln -sf /etc/nginx/sites-available/sporting-pearls.conf /etc/nginx/sites-enabled/sporting-pearls.conf
  nginx -t && (systemctl reload nginx || service nginx reload) && echo "nginx :80 front enabled"
  if [ "$TLS" = "1" ] && command -v certbot >/dev/null 2>&1; then
    CBARGS="--non-interactive --agree-tos --keep-until-expiring"
    if [ -n "$TLS_EMAIL" ]; then CBARGS="$CBARGS -m $TLS_EMAIL"; else CBARGS="$CBARGS --register-unsafely-without-email"; fi
    if certbot certonly --webroot -w "$APP/site" -d "$DOMAIN" -d "www.$DOMAIN" $CBARGS \
         --deploy-hook 'systemctl reload nginx' \
       || certbot certonly --webroot -w "$APP/site" -d "$DOMAIN" $CBARGS \
         --deploy-hook 'systemctl reload nginx'; then
      if sed -e "s|__APP__|$APP|g" -e "s|__PORT_API__|$PORT_API|g" -e "s|__DOMAIN__|$DOMAIN|g" \
           "$KIT/templates/nginx-tls.conf" > /etc/nginx/sites-available/sporting-pearls.conf \
         && nginx -t; then
        (systemctl reload nginx || service nginx reload)
        # flip .env + site JS to TLS mode
        env_set SESSION_COOKIE_SECURE 1
        env_set CSRF_COOKIE_SECURE 1
        env_set SECURE_SSL_REDIRECT 1
        env_set CORS_ALLOWED_ORIGINS "https://$DOMAIN,https://www.$DOMAIN"
        env_set CSRF_TRUSTED_ORIGINS "https://$DOMAIN,https://www.$DOMAIN,http://localhost:$PORT_API,http://127.0.0.1:$PORT_API"
        env_set SITE_URL "https://$DOMAIN"
        [ -f "$CFG" ] && sed -i "s|http://$DOMAIN|https://$DOMAIN|g" "$CFG"
        TLS_DONE=1
        echo "TLS    : https://$DOMAIN live (auto-renews via certbot timer)"
      else
        echo "TLS    : certs issued but nginx-tls.conf invalid — reverted to :80"
        sed -e "s|__APP__|$APP|g" -e "s|__PORT_API__|$PORT_API|g" \
          "$KIT/templates/nginx.conf" > /etc/nginx/sites-available/sporting-pearls.conf
        nginx -t && (systemctl reload nginx || service nginx reload)
      fi
    else
      echo "TLS    : certificate issuance FAILED (DNS A record -> this server?)"
      echo "         HTTP front stays active; after fixing DNS re-run:"
      echo "         bash install.sh --with-nginx --with-tls --domain=$DOMAIN"
      [ -f "$CFG" ] && sed -i "s|https://$DOMAIN|http://$DOMAIN|g" "$CFG"
    fi
  elif [ "$TLS" = "1" ]; then
    echo "TLS    : certbot not installed (apt install certbot) — HTTP front only."
  fi
else
  [ "$NGINX" = "1" ] && echo "nginx front requested but not available (need root + nginx) — skipped."
fi

# ── 8.5/9 production mode gate (fail closed) ──────────────────────
# Try to actually boot the app under SP_ENV=production. Only if the
# hard security checks pass is the flag written to .env — an insecure
# configuration is left in development mode, loudly.
PROD_FAILED=0
if [ "$PROD" = "1" ]; then
  step "8.5/9  Production mode check (SP_ENV=production)"
  if PRODLOG="$( cd "$APP/backend" && set -a && . ./.env && set +a && \
       SP_ENV=production \
       DJANGO_SETTINGS_MODULE=sporting_pearls_backend.settings PYTHONPATH="$APP/backend" \
       "$VENV/bin/python" manage.py check 2>&1 )"; then
    env_set SP_ENV production
    echo "SP_ENV=production written to backend/.env — startup now fails closed on insecure config."
    echo "$PRODLOG" | grep -q 'hard security checks passed' && echo "$PRODLOG" | grep 'hard security'
  else
    PROD_FAILED=1
    echo "ERROR: production checks FAILED — SP_ENV was NOT written."
    echo "       The backend would refuse to start in production mode. Reasons:"
    printf '%s\n' "$PRODLOG" | grep '^  - ' | sed 's/^/         /'
    echo "       Fix these in $APP/backend/.env (template: backend/.env.production.example)"
    echo "       — typically: run again with --with-tls so cookies go secure, then re-add --production."
  fi
fi

# ── 9/9 start + health ─────────────────────────────────────────────
if [ "$START" = "1" ]; then
  step "9/9  Starting services"
  if [ "$IS_ROOT" = "1" ] && command -v systemctl >/dev/null 2>&1; then
    systemctl restart sp-backend.service sp-site.service
  else
    ( cd "$APP" && timeout 90 bash sp.sh start </dev/null )
  fi
  step "Health check"
  ok=0
  for i in $(seq 1 15); do
    if curl -sf "http://127.0.0.1:$PORT_API/api/health/" >/dev/null 2>&1; then ok=1; break; fi
    sleep 1
  done
  [ "$ok" = "1" ] && echo "API    (:${PORT_API}) is up" || echo "API    (:${PORT_API}) NOT responding — check $APP/logs/backend.log"
  if curl -sf "http://127.0.0.1:$PORT_SITE/index.html" >/dev/null 2>&1; then
    echo "Site   (:${PORT_SITE}) is up"
  else
    echo "Site   (:${PORT_SITE}) NOT responding — check $APP/logs/site.log"
  fi
fi

cat <<BANNER

══════════════════════════════════════════════════════
  SPORTING PEARLS IS READY
══════════════════════════════════════════════════════
  Website       : http://localhost:$PORT_SITE
  On your LAN   : http://$LAN_IP:$PORT_SITE
  Staff portal  : http://localhost:$PORT_API/portal/login/
  Parent portal : http://localhost:$PORT_API/portal/parents/login/
  Admin         : http://localhost:$PORT_API/admin/
  Control       : cd $APP && bash sp.sh {status|start|stop|logs|health|backup}
  Backups       : bash sp.sh backup (daily 02:30 automatically when systemd)
  Firewall tip  : ufw allow $PORT_SITE/tcp; ufw allow $PORT_API/tcp
  Share/remote  : see REMOTE-ACCESS-GUIDE.txt (LAN, Tailscale, tunnels, VPS)
BANNER
# ── credentials: shown ONCE, only when generated this run ──────────
if [ "$ADMIN_CREATED" = "1" ] && [ "$ADMIN_PASS_SHOWN" = "1" ]; then
  cat <<PWNOTE

  ── STAFF ADMIN LOGIN (shown once — save it now) ──────────────
  Username : $ADMIN_USER
  Password : $ADMIN_PASS
  This password is NOT stored anywhere else and will NOT be shown
  again. Change it after first sign-in (portal ▸ your name ▸
  Change password, or Django admin ▸ Change password).
PWNOTE
elif [ "$ADMIN_CREATED" = "1" ]; then
  echo "  Staff admin   : $ADMIN_USER (password taken from SP_ADMIN_PASS — not shown here)"
else
  echo "  Staff admin   : '$ADMIN_USER' kept — existing password unchanged"
fi
if [ "${DEMO_SEEDED:-0}" = "1" ]; then
  cat <<DEMONOTE

  ── DEMO PARENT LOGIN (demo data only — shown once) ───────────
  Username : $DEMO_PARENT_EMAIL
  Password : $DEMO_PARENT_PASS
  Fictional account for testing the parent portal. Before going live,
  remove demo data: back up, then re-install without --demo-data.
DEMONOTE
fi
if [ -n "$DOMAIN" ]; then
  if [ "$TLS_DONE" = "1" ]; then
    echo "  Public URL    : https://$DOMAIN — HTTPS live, hosts/CORS locked"
  else
    echo "  Public URL    : http://$DOMAIN — hosts/CORS locked (add --with-tls for HTTPS)"
  fi
fi
if [ -z "$DOMAIN" ] && grep -q '^ALLOWED_HOSTS=\*' "$ENVF" 2>/dev/null; then
  echo "  Hardening     : re-run installer with --domain=your.domain to lock hosts/CORS"
fi
if [ "$PROD" = "1" ]; then
  if [ "$PROD_FAILED" = "1" ]; then
    echo "  PRODUCTION    : ✗ NOT ACTIVATED — security checks failed (see above). Fix and re-run with --production."
  elif grep -q '^SP_ENV=production' "$ENVF" 2>/dev/null; then
    echo "  PRODUCTION    : ✓ SP_ENV=production active — startup now fails closed on insecure config"
  fi
fi
[ "$PROD_FAILED" = "1" ] && exit 1
exit 0
