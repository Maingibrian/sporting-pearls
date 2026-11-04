# Sporting Pearls — Django Backend on Render (field-tested guide)

This guide reflects what actually worked on the live deployment
(`https://sporting-pearlsorg.onrender.com`). Follow it top to bottom for a new
service, or use §3 to repair an existing one.

---

## 0. Prerequisites

- GitHub repo `Maingibrian/sporting-pearls`, branch `main`, backend code in `backend/`.
- A fine-grained PAT with **Repository permissions → Contents → Read and write**
  (read-only PATs cannot push — `git push` fails with 403 "denied").
- The static site (Render Static Site, publish directory `site/`) should already
  be live, e.g. `https://sportingpearlsacademy.org`.

## 1. Create the Web Service

Render Dashboard → **New + → Web Service** → connect the repo:

| Field | Value |
|---|---|
| Name | `sporting-pearlsorg` (or your choice) |
| Region | Closest to your users (e.g. Frankfurt) |
| Branch | `main` |
| Root Directory | `backend` |
| Runtime | Python 3 |
| Instance Type | **Starter** (0.5 CPU / 512 MB) — required: Free sleeps and wipes the disk on every deploy |

### Build & Deploy commands (field-tested)

| Field | Value | Why |
|---|---|---|
| **Build Command** | `pip install -r requirements.txt && python manage.py collectstatic --noinput` | collectstatic must run in **Build** — the build image is what gets uploaded. Running it in Pre-Deploy collects into a throwaway filesystem (admin shows unstyled). |
| **Pre-Deploy Command** | *(leave empty)* | **The pre-deploy instance has NO access to the `/data` disk.** Any `migrate` here writes to a throwaway database and the live service then fails with `no such table`. |
| **Start Command** | `python manage.py migrate --noinput && python manage.py ensure_superuser && gunicorn sporting_pearls_backend.wsgi:application --log-file -` | `migrate` runs **at boot on the live instance**, where the disk IS mounted. New migrations apply automatically on every deploy. |

## 2. Attach the persistent disk

Service → Settings → Disks → **Add Disk**:

| Field | Value |
|---|---|
| Name | `sp-data` |
| Mount Path | `/data` |
| Size | 1 GB |

## 3. Environment variables

Render console → Environment. **No trailing slashes** on any URL —
`django-cors-headers` rejects origins with a path (`corsheaders.E014`).

| Key | Value | Notes |
|---|---|---|
| `SP_ENV` | `production` | Enables the fail-closed security guard |
| `DJANGO_SECRET_KEY` | ≥ 50 random chars | Guard rejects placeholders / short keys |
| `DEBUG` | `0` | |
| `ALLOWED_HOSTS` | `sporting-pearlsorg.onrender.com` | Backend host only, **no `https://`** |
| `CORS_ALLOW_ALL` | `0` | Guard rejects `1` in production |
| `CORS_ALLOWED_ORIGINS` | `https://sportingpearlsacademy.org` | The static site URL, **no trailing slash** |
| `CSRF_TRUSTED_ORIGINS` | `https://sportingpearlsacademy.org` | Same, no trailing slash |
| `TRUST_PROXY_HEADER` | `1` | Correct client IPs behind Render's proxy |
| `SESSION_COOKIE_SECURE` | `1` | HTTPS-only cookies |
| `CSRF_COOKIE_SECURE` | `1` | |
| `SECURE_SSL_REDIRECT` | `1` | |
| `DJANGO_SUPERUSER_USERNAME` | `admin` | |
| `DJANGO_SUPERUSER_PASSWORD` | (strong password) | Your admin login |
| `DJANGO_SUPERUSER_EMAIL` | office@sportingpearlsacademy.org | |
| `DB_PATH` | `/data/db.sqlite3` | **Must be exactly this** — otherwise the DB is wiped on every deploy |
| `MEDIA_ROOT` | `/data/media` | Player photos survive deploys |
| `TIME_ZONE` | `Africa/Nairobi` | |
| `SITE_URL` | `https://sportingpearlsacademy.org` | Used in email links |
| `RATE_LIMIT_PER_MINUTE` | `8` | Form submit throttling |

Optional (email delivery): `RESEND_API_KEY`, `EMAIL_TO`, `EMAIL_FROM`,
`DSO_EMAIL`. Optional (Postgres instead of SQLite): add `psycopg` to
requirements and set `DATABASE_URL`.

## 4. First deploy + roster import

1. Deploy finishes green. In the log you should see the migrations applying
   **during "Deploying…"** (at boot), then `Your service is live`.
2. Verify health: `https://<service>.onrender.com/api/health/` → `{"ok": true, ...}`.
3. Import the roster once — service page → **Connect → Shell**:
   ```bash
   cd backend
   python manage.py import_roster
   ```
   (Shell opens at the repo root; `manage.py` lives in `backend/`.)
4. Log in at `/admin/` with the `DJANGO_SUPERUSER_*` values and check the
   Management Portal — 5 squads, 50 players, all formations 4-2-3-1.

Do **not** put `import_roster` in the Start Command — it is a one-time seed;
the office manages players through the portal afterwards.

## 5. Connect the website to the backend

Once the backend is live, edit `site/assets/js/shared/site-config.js`:

```js
API_BASE: 'https://sporting-pearlsorg.onrender.com'
```

then bump the cache version numbers on the script includes
(`the-squad.js?vNN`, etc.) and push. The site's fixtures panel, live squad
rosters, trial/contact forms and Féminin gallery then read from the API.

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `no such table: submissions_…` | Pre-Deploy ran `migrate` without the disk | Use the Start Command above; clear Pre-Deploy |
| `corsheaders.E014 … should not have path` | Trailing slash in an origin env var | Remove trailing slashes |
| `DJANGO_SECRET_KEY is a known placeholder…` | Short/placeholder key | Generate ≥ 50 random chars |
| `/admin/` unstyled | collectstatic ran in Pre-Deploy | Move collectstatic into Build Command |
| 403 on `git push` | PAT lacks write access | GitHub → Developer settings → token → Contents → Read and write |
