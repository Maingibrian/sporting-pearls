# Sporting Pearls Football Academy — Website & Backend

Official repository for the Sporting Pearls Football Academy website
(static frontend) and its Django backend (forms API, staff portal,
parent portal, admin) with a one-shot Linux installer.

## Repository structure

| Path          | What it is                                                                 |
| ------------- | -------------------------------------------------------------------------- |
| `site/`       | The complete static website (41 pages, self-contained assets)                |
| `backend/`    | Django backend — forms API, staff & parent portals, admin, seeds             |
| `templates/`  | systemd units, nginx configs, backup/restore scripts used by the installer   |
| `scripts/`    | Build & QA scripts used to produce and verify the kit                        |
| `install.sh`  | One-shot installer for any Linux box with Python 3.10+ (no root required)    |
| `.github/`    | CI workflow                                                                  |

## Quick start (local server)

```bash
bash install.sh --demo-data
```

Then open:

- Website — <http://localhost:8090>
- Staff portal — <http://localhost:8020/portal/login/>
- Parent portal — <http://localhost:8020/portal/parents/login/>
- User guide — <http://localhost:8090/portal-guide.html>
- Django admin — <http://localhost:8020/admin/>

Admin passwords are generated randomly at install time and shown once
in the installer banner (or preset via `SP_ADMIN_PASS`). There are no
default passwords in this kit. After a reboot: `cd sp-app && bash sp.sh start`.

Installer options (domains, nginx, TLS, ports) are documented at the top
of `install.sh` and in `README-START-HERE.txt`.

## Deploying the frontend only

`site/` is a fully static site — serve it from any web server or CDN
(GitHub Pages, Netlify, nginx, etc.). Point the forms API origin at your
backend via `site/assets/js/shared/site-config.js`.

## Documentation

- `README-START-HERE.txt` — installer walkthrough
- `DEPLOY-RENDER.md` — deploying the backend on Render
- `EMAIL-SETUP-GUIDE.txt` — transactional email configuration
- `SAFEGUARDING-RUNBOOK.md` — safeguarding reporting operations
- `REMOTE-ACCESS-GUIDE.txt` — remote access notes
- `PRODUCTION-READINESS.md` — production checklist
- `CHANGELOG-REV20.md` → `CHANGELOG-REV22.md` — revision history

## Security notes

- Never commit real secrets: copy `backend/.env.example` /
  `backend/.env.production.example` to `.env` and fill in values locally.
- `db.sqlite3`, `media/`, `.venv/` and `.env` are git-ignored.
