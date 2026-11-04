════════════════════════════════════════════════════════════════════
  SPORTING PEARLS — POST-INSTALL NOTES
════════════════════════════════════════════════════════════════════

WHAT WAS INSTALLED (in this folder, ./sp-app by default)
  site/       the academy website (32 pages, self-contained images)
  backend/    Django API + staff/parent portals + admin (66-player roster)
  logs/       service logs (backend.log, site.log)
  sp.sh       control script — bash sp.sh {status|start|stop|restart|logs|health|backup}

DAILY USE
  Start after a reboot:   bash sp.sh start     (run inside the app folder)
  Check:                  bash sp.sh status
  Health:                 bash sp.sh health
  Logs:                   bash sp.sh logs
  Backup:                 bash sp.sh backup    (db + media + .env)

ADDRESSES
  Website       http://localhost:PORT_SITE
  On your LAN   http://YOUR-MACHINE-IP:PORT_SITE
  Staff portal  http://localhost:PORT_API/portal/login/
  Parent portal http://localhost:PORT_API/portal/parents/login/
  Admin         http://localhost:PORT_API/admin/
  User guide    http://YOUR-MACHINE-IP:PORT_SITE/portal-guide.html
                (staff & parent walkthroughs with screenshots; the
                portal sign-in pages link to it automatically)

LOGINS (created by the installer — CHANGE THEM)
  staff admin  — the random password the installer generated and showed
                once in its banner (or the one you passed via SP_ADMIN_PASS).
                If lost: re-set it from the server shell, see below.
  demo parent  — demo.parent@example.com / the random password shown once
                in the banner (only present with --demo-data installs).
  There are NO default passwords in this kit — every install generates
  its own random credentials.
  Forgot a password? Every sign-in page now has a "Forgot your password?
  Reset it by email" link (staff + parents). The reset link works once
  and expires after one hour. It needs RESEND_API_KEY to be set (below);
  without it, use the shell method:
  Lost the admin password? From the app directory run:
    backend/.venv/bin/python backend/manage.py shell -c \
      "from django.contrib.auth import get_user_model as g; \
       u=g().objects.get(username='admin'); \
       u.set_password('NEW-PASSWORD-HERE'); u.save()"
  (then remove it from your shell history:  history -c)

  SECURITY NOTES (Phase 2):
  * All three logins (staff portal, parent portal, Django admin) pause
    for 15 minutes after 8 failed attempts from one address.
  * Portal sessions expire after 12 hours (SESSION_COOKIE_AGE in .env).
  * Security headers (CSP etc.) are sent on every page; the nginx front
    (install with --with-nginx) also covers the static website.

  HOW THE WEBSITE FORMS NOW BEHAVE (Phase 3):
  * A form's "success" screen and its reference number appear only
    after the server has actually received the submission. If the
    server cannot be reached, the visitor sees an honest "Not sent yet"
    notice instead — their answers stay on the page and a copy is kept
    in THEIR browser for up to 48 hours, then sent automatically on
    their next visit.
  * While filling in a form, a draft autosaves in the visitor's browser
    (same 48-hour limit). This means the backend must be reachable when
    the public site is used — the installer sets
    site/assets/js/shared/site-config.js API_BASE to your backend
    automatically (re-point it any time with --public-url=...). NEVER
    serve the public site with an empty API_BASE: that is demo mode and
    forms would pretend success.
  * Notification emails no longer contain medical details or ID
    numbers — those answers are visible in the staff portal's answer
    sheet, and only to accounts in the "Portal Administrators" group
    (plus the superuser). Give that group only to staff who process
    registrations.
  * Every form links to the new privacy page (policy-data-privacy.html).
    Read it; it is your public promise under the Kenya Data Protection
    Act 2019.

  WHAT PHASE 5 CHANGED (this install):
  * Player photos under /media/ are no longer public. A photo shows
    without a login ONLY for players published on the squad pages
    (media-consented). Everything else needs a staff session or the
    owning guardian's login. Direct links that used to work for
    unpublished photos now return a plain 404.
  * Health probe:  curl http://your-server/healthz/  answers
    {"ok": true} (HTTP 200) when the database is reachable, 503 when
    not. Point any uptime monitor at it.
  * Backups now come with a restore drill:
       bash restore-drill.sh
    It restores the newest bundle into a scratch folder, boots a
    throwaway copy on the restored data and compares record counts —
    without touching the live system. Run it after install and at least
    once a quarter (PRODUCTION-READINESS.md R14).
  * CSP tightened: inline page scripts are gone (fonts and animation
    libraries are self-hosted now — no third-party requests from the
    public site). If you edit pages, keep scripts in external .js files.
  * Optional PostgreSQL + shared throttle counters: see the commented
    DB_ENGINE / SP_CACHE block in backend/.env.example. The default
    (SQLite, per-process cache) is right for a single-host install.
  * Form 01 collects less: no ID/insurance numbers online, one optional
    health note instead of a full medical history (a paper medical form
    is completed with the coach at enrolment).

  WHAT PHASE 6 CHANGED (this install):
  * The backend now runs as ONE gunicorn process with 8 threads
    (sp.sh and the systemd unit say: --workers 1 --threads 8). This
    is deliberate: the login-throttle and password-reset counters
    live in the process-local cache, and with several worker
    processes they would never reach the 8-failure limit — acceptance
    testing proved the throttles were silently inert with 3 workers.
    One process also matches how SQLite likes to be written. If you
    ever need more workers: switch to PostgreSQL AND set SP_CACHE=db
    FIRST (shared counters), then raise the count.
  * An acceptance-test script ships with the kit:
       SP_ADMIN_PASS='...' SP_DEMO_PASS='...' bash scripts/p6_acceptance.sh
    It re-runs the full fictional-data acceptance matrix (96 checks)
    against this install — including the login throttles, so run it
    when you can lock the portals for a few minutes. Use it for
    staging sign-off with academy staff and after every upgrade.

  Change the admin password:  Admin → change password, or:
    cd backend && .venv/bin/python manage.py shell -c \
      "from django.contrib.auth import get_user_model; u=get_user_model().objects.get(username='admin'); u.set_password('NEWPASS'); u.save()"

SAFEGUARDING REPORTS — APPOINT THE DSO (important)
  Confidential safeguarding reports (website form 10) now land in a
  RESTRICTED desk that only the Designated Safeguarding Officer can
  open. Until you appoint one, reports pile up unseen. To appoint:
    cd backend && .venv/bin/python manage.py sp_dso grant <username>
    (list/remove: sp_dso list / sp_dso revoke <username>)
  And set the DSO's PRIVATE inbox in backend/.env:
    DSO_EMAIL=officer@example.com
  New reports then send that inbox a minimal "a report is waiting"
  notice — never the report content. Full workflow, escalation ladder
  and a manual test script: SAFEGUARDING-RUNBOOK.md (kit root).

MAIL (outgoing email)
  Outbound email (form notifications, branded auto-replies, portal
  invites) uses Resend. Full step-by-step: EMAIL-SETUP-GUIDE.txt
  (copied next to this file). Short version: put your key in
  backend/.env as RESEND_API_KEY=... and restart (bash sp.sh restart).
  Without a key, submissions are still stored in the database and
  visible in the staff portal — email is simply skipped.

CONFIG FILE: backend/.env
  ALLOWED_HOSTS=*            LAN default; lock with --domain (below)
  CORS_ALLOW_ALL=1           LAN default; locked automatically by --domain
  SESSION_COOKIE_SECURE=0    this install serves plain HTTP; keep 0 until
  CSRF_COOKIE_SECURE=0       you put HTTPS (nginx + certs) in front
  CSRF_TRUSTED_ORIGINS=…     origins allowed for the portals
  SP_PUBLIC_URL=…            the API origin written into the site's JS

  After edits: bash sp.sh restart

GOING LIVE ON A REAL DOMAIN (hardening)
  Re-running the installer tightens the existing install (nothing is
  lost — .env, database, uploads are kept):

    bash install.sh --domain=sportingpearlsacademy.org

  That locks ALLOWED_HOSTS and CORS to your domain (plus www.), and
  switches the site's JS to the public API origin. For HTTPS too
  (Let's Encrypt, auto-renewing), on a server with DNS pointed at it:

    sudo apt install nginx certbot
    sudo bash install.sh --with-nginx --with-tls \
         --domain=sportingpearlsacademy.org --tls-email=you@…

  Once TLS is live the installer also flips on secure cookies and
  HTTP→HTTPS redirecting automatically.

DATA & BACKUPS
  Database: backend/db.sqlite3   (players, guardians, cases, announcements)
  Uploads:  backend/media/

  Manual backup (safe while running):
    bash sp.sh backup
  → backups/sp-backup-<timestamp>.tar.gz (db + media + .env)
  On systemd installs a timer also runs this automatically every
  day at 02:30 and keeps the newest 14 bundles.

  Restore:
    bash sp.sh stop
    tar -xzf backups/sp-backup-<timestamp>.tar.gz -C backend/
    bash sp.sh start

UPGRADING
  Re-running install.sh in the same folder is upgrade-safe: it keeps
  .env, the database and media, re-applies migrations, and skips demo
  seeds when data already exists.

UNINSTALL
  bash uninstall.sh   (in the extracted kit folder; asks for confirmation)
════════════════════════════════════════════════════════════════════

  WHAT PHASE 4 CHANGED (this install):

  COACHING STAFF — YOU PUBLISH IT YOURSELF
    The website's "Coaching & Technical Staff" section (squads page)
    is managed from the Django admin (http://localhost:8020/admin/):
      Coaches -> Add coach -> fill name, role, optional squad, a short
      bio, upload a photo -> save -> tick "published on website".
    Photos are re-encoded on save (hidden metadata stripped, extension
    corrected, oversized images rejected). Published coaches appear on
    the website within a page refresh. Nothing is shown until you
    publish — the section carries an honest "published at the start of
    each season" note meanwhile.

  PLAYER PHOTOS & SQUAD LISTS
    Real player photos: admin -> Players -> choose the player ->
    upload photo, then "published on website". Published players
    appear on the squads page automatically; their photos become
    public, unpublished ones stay private (staff/owning guardian
    only). The captains section shows the players you flag as
    "captain". Nothing published = honest "being finalised" panels.

  ENQUIRY POLICY (owner decision 2026-10-24)
    The public website no longer shows any email address or social
    media links. Fees, programme specifics, partnership terms and
    contact details are shared in reply to enquiries made through the
    site's forms. The office email address still WORKS (and is still
    the sender for reset mails and DSO notifications) — it is simply
    no longer published for visitors.

  SAFEGUARDING RECORDS RETENTION (owner policy)
    Kept for 24 months; if a case is still open when that period
    ends, kept until the case is closed, then 24 months from closure.
    Deletion is a deliberate act by the owner with the DSO — see
    SAFEGUARDING-RUNBOOK.md section 5.

  WHAT PHASE 7 CHANGED (this install):

  MATCH RESULTS PAGE (admin-settable)
    The website now has a dedicated Results page (the nav's Results
    item and the footer link point to it). Until you publish results
    it shows an honest "Coming Soon" panel. To publish:
      Django admin -> Results -> Add
        team ("SP U15"), opponent, competition (optional), date,
        venue (optional), home/away, our score, their score, and an
        optional 2-3 sentence report. Tick "published on results
        page" (or use the list's Publish toggle).
    Published results appear on the site automatically, newest first,
    grouped by month, with W/D/L badges. Unpublished rows never leave
    the database.

  PLAYER QR CODES (one per child)
    Every player now has a scannable QR code that opens their public
    profile page on this website (player.html?ref=...). Print them:
      Staff dashboard -> Players
        - "Print QR cards" button (top right) prints every player,
          grouped by squad
        - the QR icon on each player card prints just that player
      Parent portal -> open a child -> "Print QR profile card"
        (parents can print only their own child's card)
    The profile shows exactly what the squad page shows — name,
    squad, number, position, age, motto, photo. Nothing private
    (guardian, contact or medical data) is reachable through a QR.
    Unpublished players get a card too, flagged "not published yet" —
    publish the player first for the QR to open a profile.
    The QR points at SITE_URL from backend/.env (written by the
    installer). If you later move the site to a new domain, re-run
    install.sh --domain=... and print fresh cards.

  PLAYER PROFILE LINKS
    Squad pages now open the right squad tab from a link like
    the-squad.html#team-u13 (used by the profile page's
    "View the full squad" button).

  WHAT REVISION 20 CHANGED (site polish round):

  SEO + SHARING
    robots.txt and sitemap.xml now ship with the site (public content
    pages only). Every public page carries a canonical link, Open
    Graph tags and an under-160-character description, so shared
    links preview properly. The domain inside them is a PLACEHOLDER
    (https://www.sportingpearlsacademy.org): running the installer
    with --domain=your.domain re-points robots.txt, sitemap.xml and
    every canonical/OG tag automatically (idempotent — re-run it when
    TLS goes live to move them from http:// to https://).

  FASTER PAGES
    Below-the-fold images now lazy-load (the hero images still load
    first), and three heavy images were re-encoded under 200 KB with
    no visible change (logo, feminin hero, coach photo — originals
    kept in the kit's scripts/originals/ for rollback).

  READABILITY
    All small uppercase labels are now at least 12px, grey text on
    dark backgrounds meets WCAG AA contrast (4.5:1+), the policy
    pages have more breathing room, mobile stat rows are aligned
    grids, and the join-us page groups its ten forms into "Main
    Pathways (01-06)" and "Other Forms (07-10)".

  FOR THE OFFICE
    - Contact page now tells visitors the office replies "within a
      few working days" (same as the auto-reply email). Confirm or
      set a firm number — search contact.html for "OWNER: confirm
      response time".
    - The contact page's "8 Development Programmes" stat is
      unverified (site lists show 6 and 7) — decide the real number.
    - partners.html says "4 Active Squads" while other pages say 6 —
      decide which is right.
    - partner-with-us.html duplicates partners.html (~80%); the
      recommendation is to 301-redirect it to partners.html at
      go-live. Nothing was deleted or hidden — your call.

WHAT REVISION 21 CHANGED (owner UI round)
  The owner asked (with a screenshot): remove the carousel, no black,
  parallax. Applied across the site:

  CAROUSEL REMOVED
    The auto-scrolling text strip under the hero was removed from all
    14 pages that had it, together with its CSS and JS. The hero now
    flows straight into the next section.

  NO BLACK
    A long-standing bug was fixed: the decorative wave shapes under
    the hero rendered pure BLACK on many pages (a broken CSS selector
    meant the brand colours never applied). Waves now use the sand /
    pearl / navy brand colours everywhere. Dark near-black areas were
    recolored to the brand navy family and every page's footer is now
    the same readable navy.

  PARALLAX
    Every photo hero (16 pages) now gently drifts at quarter speed as
    you scroll, and the effect switches itself off for visitors who
    prefer reduced motion.

  PLAYER QR CARDS (THE SQUAD)
    Every player card on the squad page — the dossier window that
    opens when you tap a player — now carries that player's UNIQUE QR
    code. Scanning it opens the player's public profile page. No two
    players share a code: on the live roster each code is generated
    from the player's own reference (e.g. U19-01); in demo mode the
    codes are derived from the squad code and shirt number. The QR
    library is self-hosted with the site (no third-party CDN), and if
    anything goes wrong the QR simply hides itself rather than showing
    a broken code. The staff/parent printable QR cards from the
    previous revision are unchanged.

  ALSO
    - Asset versions bumped so no visitor gets stale CSS/JS after the
      upgrade.
    - The backend test suite no longer depends on the build machine's
      folder layout — it runs on any install path (no behaviour
      change).

  NOTE FOR THE OFFICE
    Some dark navy areas were left intentionally (hero shading on the
    home/academy/join-us/coaching pages, the training-section bands on
    the goalkeeper and education pages) — they are brand navy, not
    black. Say the word if you would like those lightened too.


────────────────────────────────────────────────────────────────────
  REAL SQUAD ROSTER (kit rev 22, 2026-11-03)
────────────────────────────────────────────────────────────────────

The squad page now shows the REAL academy register (season 2026-27),
imported from the Player Administration Excel:

  U12 Foundation .... 18 players   (4-2-3-1)
  U14 Development ... 16 players   (4-2-3-1)
  U16 Performance ... 11 players   (4-2-3-1)
  U19 Senior ......... 5 players   (4-2-3-1)
  Féminin ............ roster being finalised (empty by design
                       until the office sends the girls' register)

FOR THE OFFICE
  * Every player not on the drawn starting XI appears on the bench
    strip right below the pitch — nobody is left off the page.
  * Tap any player (pitch or bench) for their dossier: number, age,
    position, photo (where the register had one) and their personal
    QR code that opens the public profile page.
  * 21 players have no photo in the register yet — they show a
    jersey with their number instead. Send headshots (labelled with
    the player's name) and they will be added the same way.
  * Captains are not recorded in the register — the captains section
    stays in its honest "named at the start of the season" state
    until the office confirms them.
  * To update the roster later: edit the Excel, send it over, and the
    same import updates the squad page, the player profiles and the
    backend seed in one pass.
