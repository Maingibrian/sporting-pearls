# Sporting Pearls — Django Backend

Form backend + fixtures store + review dashboard for the Sporting Pearls
website. Receives the site's 10 forms, emails every submission to the
academy inbox through **Resend**, stores a permanent ledger, gives you a
password-protected **admin dashboard** for reviewing (with CSV export),
serves published **fixtures** to the homepage, and runs the **Player
Profile Manager** — the six squads' rosters, published straight to the
website's squad pages.

```
POST /api/forms/<form-slug>/   ← the 10 site forms (JSON)
GET  /api/fixtures/            ← homepage fixtures panel
GET  /api/gallery/feminin/     ← published real photos for the Féminin page
GET  /api/players/             ← published rosters for the six squad pages
GET  /api/health/              ← uptime probe
GET  /admin/                   ← review dashboard (password protected)
```

---

## 1. Run it locally (optional test)

```bash
cd sp-backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py ensure_superuser
python manage.py runserver
```

- Site API test: `curl -X POST http://127.0.0.1:8000/api/forms/newsletter-subscription/ -H "Content-Type: application/json" -d '{"data":{"email":"you@example.com"}}'`
- Dashboard: open http://127.0.0.1:8000/admin/ and log in with the
  credentials in `.env` (`DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD`).

## 2. Deploy (pick ONE — both free-tier friendly)

### Option A — Railway (recommended, easiest)
1. Push this `sp-backend/` folder to a GitHub repo (the included
   `.gitignore` keeps `.env` and the database out of git).
2. railway.new → **Deploy from GitHub repo** → select the repo.
3. Add a **Volume** mounted at `/data` and set variable `DB_PATH=/data/db.sqlite3`
   (keeps submissions across deploys) **and `MEDIA_ROOT=/data/media`**
   (keeps uploaded player photos across deploys).
4. In **Variables**, add everything from `.env`:
   `DJANGO_SECRET_KEY`, `RESEND_API_KEY`, `EMAIL_TO`, `EMAIL_FROM`,
   `AUTO_REPLY=1`, `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD`,
   `CORS_ALLOW_ALL=1`.
   Railway auto-runs the `Procfile` release line, which applies migrations
   and creates your admin user.
5. Note your URL, e.g. `https://<app>.up.railway.app`.

### Option B — Render
1. Push to GitHub → render.com → **New Web Service** → connect the repo.
2. Build command: `pip install -r requirements.txt && python manage.py migrate && python manage.py ensure_superuser && python manage.py collectstatic --noinput`
3. Start command: `gunicorn sporting_pearls_backend.wsgi:application --log-file -`
4. Add a **Disk** mounted at `/data` and set `DB_PATH=/data/db.sqlite3`.
5. Add the same environment variables as above. Deploy.
6. Note your URL, e.g. `https://<app>.onrender.com`.

## 3. Connect the website (one line)

Edit `assets/js/shared/site-config.js` in the website:

```js
window.SP_CONFIG = {
  API_BASE: "https://<app>.up.railway.app",   // ← paste your backend URL
  CONTACT_EMAIL: "info@sp"
};
```

That single change:
- syncs all **10 forms** (7 numbered forms, contact enquiry, partnership
  application, newsletter) to the backend — each still shows its normal
  success screen, plus a "Saved on our server — reference SP-…" line;
- makes published fixtures replace the homepage **Coming Soon** panel;
- if the backend is briefly unreachable, submissions are queued in the
  visitor's browser and retried automatically.

## 4. Email notes (Resend)

- `EMAIL_TO` / `EMAIL_FROM` are `info@sportingpearlsacademy.org` (Task 24:
  real inbox wired and the domain verified in Resend — live test delivered
  HTTP 200). If you ever change the inbox, update both keys in `.env` /
  your host's dashboard; no code change needed.
- If `EMAIL_FROM` is ever replaced, keep it on a domain verified in the
  Resend dashboard, otherwise Resend rejects the send.
- Every submission triggers (a) a notification email to `EMAIL_TO` with
  the full answers and (b) a branded thank-you auto-reply to the visitor
  (`AUTO_REPLY=0` to disable).
- Visitor-facing emails (auto-reply + parent invitation) are fully
  branded — navy/amber shell, amber CTA, and a text email signature
  ("The Academy Office", contacts, tagline) — sent as multipart
  HTML + plain text. All templates live in one place:
  `submissions/email_branding.py` (email-safe tables, web-safe fonts).

## 5. Admin dashboard (your review inbox)

Log in at `https://<app>/admin/`:
- **Submissions** — all 10 forms land here with reference, name, email,
  full answers, delivery status. Filter by form/date, search anything,
  mark *reviewed/archived*, and use **Export selected to CSV** for Excel.
- **Fixtures** — add a match (team, opponent, competition, date, kick-off,
  venue, home/away) and tick **"published on homepage"**. Published
  fixtures instantly replace the homepage "Fixtures Coming Soon" panel —
  this is the "added from the user side" flow. Unpublish to return to
  Coming Soon.
- **Squads / Players** — the Player Profile Manager. Every squad (Féminin,
  U9, U13, U15, U17, U19) and player profile: shirt number, position,
  age, height, footedness, motto, photo, captain flag, pitch slot.
  Publish players in bulk (actions menu) and they appear on the website
  squad pages instantly — no code, no redeploy.

## 6. The branded management portal (recommended — no Django screens)

The backend now serves its own branded dashboard at `https://<app>/portal/` —
one private sign-in, the academy's navy-and-amber look, zero technical
screens. This is where day-to-day work happens:

- **Submissions** — open any entry, *Reply by email* (opens your mail app
  addressed to the sender), **Mark reviewed** or **Archive** — one click,
  the ledger updates.
- **Fixtures** — click the **Published/Draft** switch on any fixture card
  to put it on, or pull it off, the website homepage panel.
- **Players (the Player Profile Manager)** — every card carries four
  buttons:
  - **Eye** — hide from / show on the website (reversible — profiles are
    kept, ideal for injuries and transfers);
  - **Pencil** — edit everything the card shows (names, shirt number,
    position, age, height, foot, motto, pitch slot, captain, published);
  - **Camera** — upload the scanned photo (JPG/PNG/WebP up to 8 MB) —
    the website card updates instantly;
  - **Bin** — delete permanently (asks twice; prefer the eye for squad
    changes).
  - **+ Add player** signs a new player into any squad and assigns the
    next free REF code (FEM-12, FEM-13, …) — the paper-form mapping keeps
    working.

Sign-in uses the same account as the admin (`admin` + the password from
`DJANGO_SUPERUSER_PASSWORD` in `.env`). Change it after the first login
(Django admin ▸ Change password, or ask your developer). Once the portal
is live you never need to open `/admin/` again — it remains available as
a technical fallback.

## 7. Parent accounts — invite a guardian in one click (P1 live)

Parents whose child's application has been approved get their own branded
**Parent Portal** at `https://<app>/portal/parents/` — same academy look,
their own email + password, and they can only ever see their own child.

**Approving a family (the daily flow):**

1. Open the entry in **Submissions** — the answer sheet now carries a
   *Guardian invitation* panel, pre-filled from the form (guardian email,
   phone, and — when the form names a child — the child's profile is
   matched automatically).
2. Type the guardian's name if the form did not capture it, pick the
   relationship, and confirm the child (or choose *new player profile*
   to create a draft profile straight from the application).
3. Click **Approve & invite guardian** — an activation email (valid
   72 hours) goes out through Resend and the entry gets a
   *Guardian invited* pill. Once the parent finishes setup the pill
   turns **Parent active**.
4. If an email never arrives, the same panel shows a **copy-link**
   fallback, and `/admin/ ▸ Parent invites` can re-send any invite with
   a fresh 72-hour window.

**What parents see today:** their child's card (photo, squad, shirt
number, next published fixture) at `/portal/parents/`. Announcements and
the private complaints desk arrive in the next portal update (the schema
is already in place). Parents are locked out of every staff screen —
hitting a staff page or action bounces them home — and 8 failed sign-ins
pause that address for 15 minutes.

Revoking access: `/admin/ ▸ Guardian accounts ▸ untick *account active*
— instant, reversible, keeps all history.

## 8. The roster & photos workflow

The website's squad pages read `GET /api/players/` every visit (with a
built-in fallback if the backend is ever unreachable — visitors never
see a broken page):

1. **Roster import (one-time, already done in this package):**
   `python manage.py import_roster` loads `player_seed.json` (the roster
   exported from the site) into the dashboard. Re-running is safe — it
   updates in place, keyed by the REF codes printed on the paper form.
2. **Paper forms → dashboard:** as the printed data sheets come back
   (REF codes FEM-01…U19-13 map each sheet row to a player), edit the
   player's profile in the dashboard and tick *published on website*.
3. **Photos:** scan/photograph the pasted photo on each sheet and upload
   it on the player's profile — it overrides the placeholder instantly.
   Uploaded files are stored under `MEDIA_ROOT` (point it at the volume
   so they survive deploys).
4. **Captains & formation:** tick *captain* on one player per squad and
   set the squad's formation (4-2-3-1, 4-3-3, 4-4-2, 3-5-2) — the site
   pitch and captain marker update automatically.
5. **Technical team (coaches):** manage coaches from the portal's
   *Technical team* view — add name, role, squad link, short bio and a
   photo, then flip the eye switch to publish. Published coaches replace
   the "once confirmed" notice on the website's squad page immediately;
   drafts stay private. (The Django admin still works too — the portal
   and admin edit the same records.)

## 9. Security checklist (before going live)

- [ ] Set a long random `DJANGO_SECRET_KEY` (done in `.env` template — change it).
- [ ] Set `CORS_ALLOW_ALL=0` and `CORS_ALLOWED_ORIGINS=https://your-site-domain`.
- [ ] Replace `ALLOWED_HOSTS=*` with your backend domain.
- [ ] Change the admin password (`DJANGO_SUPERUSER_PASSWORD`) — it was shared in chat.
- [ ] Complete `EMAIL_TO` with the real academy inbox.
- [ ] HTTPS is automatic on Railway/Render.

Spam protection included: per-IP rate limit (8 submissions/min/form) +
honeypot field. reCAPTCHA intentionally skipped per your decision.

## 10. Form slugs (reference)

| Site form | API slug |
|---|---|
| Contact — General enquiry | `contact-general-enquiry` |
| Form 01 — Player registration | `form-01-player-registration` |
| Form 02 — Trial application | `form-02-trial-application` |
| Form 03 — Parent association | `form-03-parent-association` |
| Form 04 — Volunteer application | `form-04-volunteer-application` |
| Form 05 — Coach / technical staff | `form-05-coach-technical-staff` |
| Form 06 — Sponsorship / partnership | `form-06-sponsorship-partnership` |
| Form 10 — Safeguarding report | `form-10-safeguarding-report` |
| Partners — Partnership application | `partnership-application` |
| Newsletter (homepage) | `newsletter-subscription` |
