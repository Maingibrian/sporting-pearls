════════════════════════════════════════════════════════════════════
  SPORTING PEARLS — SERVER KIT (one-shot install)
════════════════════════════════════════════════════════════════════

WHAT THIS IS
  The complete academy website + Django backend (forms API, staff and
  parent portals, admin) with an installer that runs on any Linux
  machine with Python 3.10+. No root needed (root gets systemd).

RUN IT — two commands:

  1) extract
       tar -xzf sporting-pearls-server-kit.tar.gz && cd sporting-pearls

  2) install + start
       bash install.sh --demo-data

  Then open:  http://localhost:8090          (the website)
  Portals:    http://localhost:8020/portal/login/          (staff)
              http://localhost:8020/portal/parents/login/  (parent)
  User guide: http://localhost:8090/portal-guide.html
              (staff & parent walkthroughs with screenshots)
  Admin:      http://localhost:8020/admin/
  Logins:     staff admin — password is generated randomly at install and
              shown ONCE in the installer banner (or set via SP_ADMIN_PASS).
              Demo parent (only with --demo-data): demo.parent@example.com
              + the random password shown once in the banner.
              There are NO default passwords in this kit.

  After a reboot:  cd sp-app && bash sp.sh start

OPTIONS
  --demo-data      demo guardians/announcements/complaints (fresh db only)
  --with-nginx     same-origin :80 (needs sudo + nginx)
  --domain=NAME    lock ALLOWED_HOSTS + CORS to your domain (hardening)
  --with-tls       HTTPS via Let's Encrypt (needs --domain + sudo +
                   nginx + certbot; auto-renews, flips secure cookies on)
  --tls-email=MAIL registration email for the TLS certificate
  --port-api=N     backend port   (default 8020)
  --port-site=N    website port   (default 8090)
  --dir=PATH       where to install (default ./sp-app, or /opt for root)
  --public-url=URL force the public API origin
  --no-start       install without starting

GOING LIVE CHECKLIST
  1) Domain hardening:  bash install.sh --domain=your.domain
     (locks hosts/CORS; safe to re-run on an existing install)
  2) HTTPS:             sudo bash install.sh --with-nginx --with-tls \
                           --domain=your.domain --tls-email=you@…
     (needs DNS pointed at the server; apt install nginx certbot first)
  3) Email:             see EMAIL-SETUP-GUIDE.txt (Resend, ~15 min)
  4) Backups:           automatic daily 02:30 on systemd installs
     (bash sp.sh backup anytime; restores with one tar command)

Full details: POST-INSTALL-README.txt (copied into the app folder).
════════════════════════════════════════════════════════════════════
