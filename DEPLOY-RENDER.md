# Deploying Sporting Pearls on Render

This guide takes the academy website live on [Render](https://render.com) —
first the website itself (free, ~15 minutes), then, when you are ready,
the Django form backend that collects the 13 forms into a staff portal
and emails the office.

The website is a **static site**: 41 HTML pages plus CSS, JS and images.
No build step is needed — Render serves the files exactly as they are,
from a global CDN, with free HTTPS and automatic deploys every time you
push to GitHub.

---

## Part 1 — What you are deploying

| Piece | What it is | Render service type | Cost |
|---|---|---|---|
| The website | `site/` folder (41 pages, assets) | **Static Site** | Free |
| Form backend (optional, later) | `backend/` folder (Django + gunicorn) | **Web Service** | Free tier available* |

\* Free web services sleep after 15 minutes of inactivity (first request
afterwards takes ~30–60 s to wake). The forms are offline-safe by design:
until the backend is connected, every form keeps a copy on the visitor's
device and offers a mailto fallback — nothing is silently lost.

**You can launch the website today and add the backend any time.**

---

## Part 2 — Push the site to GitHub (one-time, ~5 minutes)

1. Create a **free GitHub account** (github.com) if you don't have one.
2. Create a new repository, e.g. `sporting-pearls-site`. Do **not** add a
   README or .gitignore (the kit already has what it needs).
3. On your computer, copy the kit's `site/` folder somewhere you can work,
   then push it as the repo root:

   ```bash
   cd site
   git init
   git add .
   git commit -m "Sporting Pearls website — launch"
   git branch -M main
   git remote add origin https://github.com/<your-username>/sporting-pearls-site.git
   git push -u origin main
   ```

The repo now contains `index.html` at the root, `assets/`, `logo.png`,
`robots.txt`, `sitemap.xml`, and all the other pages.

> Tip: the whole site is roughly 30 MB — well within free limits.

---

## Part 3 — Create the Static Site on Render (~10 minutes)

1. Create a **free Render account** at dashboard.render.com (sign in with
   GitHub — easiest).
2. On the dashboard, click **New +** → **Static Site**.
3. Connect the `sporting-pearls-site` repository you just pushed.
4. Fill in the form exactly like this:

   | Field | Value |
   |---|---|
   | Name | `sporting-pearls` (becomes part of the URL) |
   | Branch | `main` |
   | Build command | *(leave empty)* |
   | Publish directory | `.` (just a dot — the pages are at the repo root) |

5. Click **Create Static Site**.
6. Render builds in under a minute and gives you a live URL such as
   `https://sporting-pearls.onrender.com`. Open it — every page, image,
   stylesheet and script is now served over HTTPS from Render's CDN.

**Updating the site later:** edit files, commit, `git push` — Render
redeploys automatically (usually <1 minute). Nothing else to do.

---

## Part 4 — Your own domain (sportingpearlsacademy.org)

1. In the Render service, open **Settings → Custom Domains** →
   **Add Custom Domain** and enter `sportingpearlsacademy.org`.
   Add `www.sportingpearlsacademy.org` too if you want it.
2. Render shows the exact DNS records to create at your domain registrar
   (where you bought the domain). Typically:
   - apex (`sportingpearlsacademy.org`) → an **A** or **ALIAS** record
     pointing at Render;
   - `www` → a **CNAME** record pointing at your Render site.
3. Add the records at the registrar, then click **Verify** in Render.
   DNS can take from minutes up to 48 h to propagate (usually ~1 h).
4. Render issues a free HTTPS certificate automatically once DNS resolves.
5. In **Settings → Redirects** you can send `www` → apex (or the reverse)
   so there is one canonical address. The site's `canonical` tags already
   point at `https://www.sportingpearlsacademy.org/`.

---

## Part 5 — Connect the form backend (when you are ready)

This makes the 13 forms (player registration, trials, contact, sponsorship,
safeguarding…) save into a database, appear in the staff portal, and email
`info@sportingpearlsacademy.org` via Resend.

### 5.1 Deploy the Django backend

1. Push the **whole kit** (or at least `backend/`) to a GitHub repo, e.g.
   `sporting-pearls-kit`, keeping the folder structure:
   `backend/`, `site/`, …
2. Render dashboard → **New +** → **Web Service** → connect that repo.
3. Settings:

   | Field | Value |
   |---|---|
   | Name | `sporting-pearls-backend` |
   | Root Directory | `backend` |
   | Environment | Python 3 (set env var `PYTHON_VERSION=3.12` or newer if the build picks an older one) |
   | Build command | `pip install -r requirements.txt` |
   | Start command | Render reads the kit's `Procfile` automatically (migrate → superuser → collectstatic → gunicorn). If you prefer it spelled out: `gunicorn sporting_pearls_backend.wsgi:application --log-file -` |
   | Instance type | Free (or Starter for always-on) |

4. Add the environment variables (Settings → Environment):

   | Variable | Value | Notes |
   |---|---|---|
   | `SECRET_KEY` | a long random string | e.g. from python: `import secrets; print(secrets.token_urlsafe(50))` |
   | `ALLOWED_HOSTS` | `sporting-pearls-backend.onrender.com` | plus any custom API domain later |
   | `CORS_ALLOW_ALL` | `0` | lock CORS down (below) |
   | `CORS_ALLOWED_ORIGINS` | `https://sporting-pearls.onrender.com,https://www.sportingpearlsacademy.org,https://sportingpearlsacademy.org` | the sites allowed to submit forms |
   | `CSRF_TRUSTED_ORIGINS` | same list as above | |
   | `RESEND_API_KEY` | your Resend key | optional — enables email alerts + auto-replies; without it submissions are still stored |

5. **Database — pick one:**

   - **Free Render PostgreSQL** (recommended to start): create it with
     **New + → PostgreSQL** (free tier: 1 GB, and note it **expires after
     90 days** — Render emails reminders; upgrade to paid ~$7/mo or
     export/import before then). Open its **Info** page, copy the
     **Internal Database URL**, and split it into backend env vars
     `postgres://USER:PASSWORD@HOST:PORT/NAME`:
     `DB_ENGINE=postgres`, `DB_USER=…`, `DB_PASSWORD=…`, `DB_HOST=…`,
     `DB_PORT=…`, `DB_NAME=…`.
   - **SQLite on a persistent disk** (needs a paid instance, Starter
     ~$7/mo): add a disk mounted at `/data` and set `DB_PATH=/data/db.sqlite3`.
   - **Do not** use SQLite on the free instance's own disk — free services
     are re-deployed from scratch on every deploy and the data would be lost.

### 5.2 Point the website at the backend

Edit **one line** in `site/assets/js/shared/site-config.js`:

```js
window.SP_CONFIG = {
  API_BASE: "https://sporting-pearls-backend.onrender.com"
};
```

Commit + push → the static site redeploys → every form now saves to the
server, shows a "Saved on our server — reference SP-…" confirmation, and
the Fixtures panel switches on.

### 5.3 Staff portal

Visit `https://sporting-pearls-backend.onrender.com/` and log in with the
superuser the Procfile created (set its password via the env vars the
kit's `ensure_superuser` command reads, or `python manage.py
changepassword <user>` in the Render shell — see `backend/README.md`).

---

## Part 6 — Post-launch checklist

- [ ] Open the site URL — homepage, Programs (5 cards), Beyond the Pitch,
      Player Pathway, About moments all render with real photos.
- [ ] Menu, footer and in-page links navigate (41 pages, spot-check 5–6).
- [ ] Submit the contact form once with a test message; confirm the
      success screen and (backend connected) the SP-… reference.
- [ ] Custom domain resolves over HTTPS; www/apex redirect works.
- [ ] `https://<site>/robots.txt` and `/sitemap.xml` return content.
- [ ] If backend live: submit a form, check the staff portal inbox and
      the office email.
- [ ] Bookmark Render's dashboard: **Events** tab shows every deploy.

## Costs summary

| Setup | Monthly cost |
|---|---|
| Static site only | **$0** |
| + form backend (sleeps when idle) | $0 |
| + always-on backend or persistent disk | from ~$7 |
| + paid PostgreSQL (after free 90 days) | from ~$7 |

---

## Appendix — render.yaml (optional, one-repo blueprint)

If you push the whole kit as one repo, you can drop this file at the repo
root and use Render's **Blueprint** (New + → Blueprint) to create both
services at once:

```yaml
services:
  - type: web            # the Django form backend
    name: sporting-pearls-backend
    rootDir: backend
    env: python
    buildCommand: pip install -r requirements.txt
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.4
      - key: SECRET_KEY
        generateValue: true
      - key: DB_ENGINE
        value: postgres
      - key: DB_USER
        fromDatabase:
          name: sp-db
          property: user
      - key: DB_PASSWORD
        fromDatabase:
          name: sp-db
          property: password
      - key: DB_HOST
        fromDatabase:
          name: sp-db
          property: host
      - key: DB_PORT
        fromDatabase:
          name: sp-db
          property: port
      - key: DB_NAME
        fromDatabase:
          name: sp-db
          property: database

  - type: web            # the static website
    name: sporting-pearls
    rootDir: site
    env: static
    buildCommand: ""
    staticPublishPath: .

databases:
  - name: sp-db
    plan: free           # expires after 90 days — upgrade or migrate before then
```

After the blueprint deploys, set `CORS_ALLOWED_ORIGINS`,
`CSRF_TRUSTED_ORIGINS`, `ALLOWED_HOSTS` and (optionally) `RESEND_API_KEY`
in the backend's environment, and paste the backend URL into
`site/assets/js/shared/site-config.js`.

---

*Kit reference: `README-form-backend.md` (how forms reach the backend),
`backend/README.md` (local run + gunicorn notes),
`PRODUCTION-READINESS.md` (the full hardening evidence trail).*
