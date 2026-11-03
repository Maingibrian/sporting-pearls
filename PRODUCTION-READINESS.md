# PRODUCTION-READINESS — Sporting Pearls Football Academy

| | |
|---|---|
| **Document status** | Living document — updated at every phase gate |
| **Kit revision** | 21 (owner UI round: carousel removed, no black, hero parallax, squad QR cards + test portability) |
| **Last updated** | 2026-10-27 |
| **Overall verdict** | **NOT PRODUCTION READY.** Phases 0–7 complete and gated; **rev 20 polish round (2026-10-26)** landed every owner-independent site improvement: robots.txt + sitemap.xml, canonical/Open Graph on all 39 public pages, 23 over-long descriptions rewritten, duplicated hero label + pillar title fixed, eyebrow renumbering, mobile stat-strip grids with 12px labels, join-us forms hub (Main Pathways 01–06 + Other Forms 07–10), contact response-time line (from the kit's own auto-reply wording), all sub-12px labels raised to 12px, grey-on-dark contrast lifted to WCAG AA (ratios recorded), policy-page spacing, three images compressed under 200 KB, 150 below-the-fold images lazy-loaded; two pre-existing bugs found and fixed (missing squad CSS background image 404; missing label rule in the bl14m -b mobile variant). No security control, safeguarding/DSO logic, form field or policy wording touched; one accidental policy-wording edit was caught and reverted. **Rev 21 (2026-10-27)** landed the owner UI round: marquee carousel removed from all 14 pages, the pre-existing black hero-wave bug fixed plus near-black areas recolored to brand navy (footer unified navy-4), parallax wired on all 16 photo heroes, cache busts, every squad player card now carrying the player's unique QR profile code (self-hosted CSP-safe QR library, new wiring test — suite now 163), and the backend test suite made path-portable (full record in CHANGELOG-REV21.md). Remaining owner-side actions unchanged: player photos, DSO appointment + `DSO_EMAIL`, then domain/TLS/monitoring per the go-live checklist; plus five new small owner decisions listed in CHANGELOG-REV20.md. |

This document is the single source of truth for the production-hardening
programme. Each phase: inspect → implement scoped changes → test → record
evidence here (§8) → stop at the release gate and wait for owner approval.

**Standing constraints (apply to every phase):**
- No deploying, no sending real email, no cloud accounts, no exposed servers,
  no real personal data without explicit owner approval.
- Preserve the public website design unless a change is required for
  security, accessibility, or usability.
- Safeguarding data is treated as highly restricted: only a specifically
  authorised DSO role may ever access it.

---

## 1. Architecture overview

Two serving planes share one SQLite database:

```
                        ┌──────────────────────────────────────────────┐
                        │  server (Linux Mint / Ubuntu / VPS)          │
                        │                                              │
 visitors ──HTTP(S)──▶  │  nginx :80/:443 (optional front)             │
                        │   ├── static site  (site/ … 22+ pages)       │
                        │   └── /api/ ──────────────┐                  │
                        │                           ▼                  │
 staff ──────────────▶  │  gunicorn :8020 (Django backend)             │
 parents ────────────▶  │   ├── /api/forms/<slug>/  public form API    │
 (browser)              │   ├── /portal/…            staff dashboard   │
                        │   ├── /portal/parents/…    guardian portal   │
                        │   ├── /admin/              Django admin      │
                        │   └── /media/…             player photos     │
                        │                           │                  │
                        │        SQLite ◀── db.sqlite3 (single file)   │
                        │        media/   ◀── uploaded player photos   │
                        │                           │                  │
                        │  systemd units + daily 02:30 backup timer    │
                        └──────────────────────────┬───────────────────┘
                                                   │ HTTPS (outbound only)
                                                   ▼
                                        Resend email API
                                        (notifications + auto-replies
                                         + guardian invitations)
```

- **Static site** — plain HTML/CSS/JS (no build step). `sp-forms.js`
  serialises each form by visible field label, POSTs JSON to the API,
  queues to `localStorage` when offline and retries on the next visit.
- **Django backend** — two apps: `submissions` (form ledger, squads,
  players, staff portal) and `parents` (guardian accounts, invitations,
  announcements, welfare complaints). WhiteNoise serves static assets;
  Django itself serves `/media/` (low traffic).
- **Deployment tooling** — `install.sh` (one-shot installer: venv, .env,
  migrate, superuser, systemd/nginx/TLS, backups), `sp.sh` (start/stop/
  logs/health/backup), `uninstall.sh`.
- **Email** — Resend HTTP API; no SMTP. All outbound mail is a `requests`
  POST; failures are recorded per-row (`email_status` / `email_error`).

### Trust boundaries
1. **Internet → site/API** (public; rate-limited form POSTs, honeypot)
2. **Internet → portals** (session auth; staff = Django `is_staff`,
   parents = `Guardian` profile linked to children via `GuardianPlayer`)
3. **API → Resend** (bearer token in `RESEND_API_KEY`)
4. **Reverse proxy → gunicorn** (only meaningful when nginx/TLS is used;
   `X-Forwarded-*` currently trusted unconditionally — see R6)

---

## 2. Inventory

### 2.1 Routes

**Public (no auth):**

| Route | Method | Purpose | Notes |
|---|---|---|---|
| `/api/forms/<slug>/` | POST | Store a form submission + trigger emails | CSRF-exempt; per-IP rate limit (8/min) + honeypot. **Form-10 takes a separate restricted path** (see below) |
| `/api/fixtures/` | GET | Published fixtures | Read-only |
| `/api/players/` | GET | Published player rosters | Read-only (published children's names/photos) |
| `/api/players/<ref>/` | GET | One published player's public profile — the QR-code target (Phase 7). Public fields only; unpublished/unknown refs 404 (fail closed) | Read-only (same public surface as the roster) |
| `/api/results/` | GET | Published match results, newest first, server-derived W/D/L (Phase 7) | Read-only (no personal data) |
| `/api/coaches/` | GET | Published coaching staff (Phase 4) | Read-only (published adult staff: name/role/squad/bio/photo) |
| `/api/health/`, `/healthz/`, `/` | GET | Uptime probes (Phase 5: `/healthz/` adds DB readiness, 503 on failure) | No data |
| `/media/*` | GET | Uploaded photos | Served through `portal.media_serve` (Phase 5, R17): **published** players'/coaches' photos public; everything else requires staff or the owning guardian; missing/forbidden/traversal all 404 alike |
| `/portal/login/` | GET/POST | Staff sign-in | **No rate limiting** (R4) |
| `/portal/parents/login/` | GET/POST | Parent sign-in | Throttled: 5 failures → 15 min lockout per IP |
| `/portal/parents/activate/<token>/` | GET/POST | One-time invitation (72 h) | Token is 64-char secret |
| `/portal/dso/`, `/portal/dso/r/<ref>/`, `/portal/dso/audit/` | GET/POST | **DSO desk (Phase 1)** | **DSO role only** (explicit group grant). Staff, parents and even superusers without the role receive a neutral 403. Every view/action audited |

**Staff (requires `is_staff`):** `/portal/` (dashboard: submissions ledger —
**safeguarding reports no longer appear anywhere in it**, they live in the
restricted store), `/portal/desk/announcements/`, `/portal/desk/complaints/`
(welfare inbox). All mutating portal actions are POST + CSRF-checked.

**Parent (requires active `Guardian`):** `/portal/parents/` home,
announcements, own child card, own complaints, account (password change).
Every query is filtered through `GuardianPlayer` — a parent can only ever
see their own children (verified in prior cycles).

**Superuser:** `/admin/` — Django admin over every model **except the
safeguarding store, which requires the DSO role even for superusers**
(break-glass = grant the role; see SAFEGUARDING-RUNBOOK.md §2).

### 2.2 Forms & collected data fields

12 public forms post to `/api/forms/<slug>/` and land in the generic
`FormSubmission.payload` JSON column, emailed in full to the `EMAIL_TO`
inbox. **The 13th — form-10 (safeguarding) — is routed to the restricted
`SafeguardingReport` store and never touches the ledger or the general
inbox (Phase 1).**

| Form (slug) | Ref prefix | Personal data collected |
|---|---|---|
| Player Registration (form-01) | REG | Child: full name, DOB, gender, **Birth Certificate/UPI No.**, school, class, residential area, sub-county, **passport photo upload**, playing profile, **blood group, NHIF/insurance provider + member number, allergies, chronic conditions, past injuries/surgeries, family physician + phone**. Guardian: full name, **National ID/Passport number**, phone, WhatsApp, email, occupation, **physical home address**. Emergency contact: name, relationship, 2 phones, town. Digital signature. |
| Trial Application (form-02) | TRIAL | Applicant name, **DOB**, age, school, positions, guardian name/phone/WhatsApp/email, residential area, emergency number, **medical declaration**, digital signature |
| Parent Association (form-03) | PARENT | Parent/guardian identity + contact details |
| Volunteer Application (form-04) | VOL | Identity, contacts, availability, references |
| Coach / Technical Staff (form-05) | COACH | Identity, contacts, coaching history |
| Sponsorship & Partnership (form-06) | SPON | Business contact data |
| Donation & Support (form-07) | SUP | Donor contact data (payments deliberately NOT online yet) |
| Contact Form (form-08) | ENQ | Name, email, phone, message |
| Media & Photo Consent (form-09) | MC | Child identity + consent decisions |
| **Safeguarding Report (form-10)** | SAFE | **Stored in the restricted `SafeguardingReport` model (Phase 1):** reporter identity/contact (blank when anonymous), role; child's name + estimated DOB; squad; incident nature/type; persons whose conduct is in question; date/time/location; full factual narrative; witnesses; disclosure history; external authority notification + police OB number. DSO-only access; every view/action audited |
| General Enquiry | GENQ | Name, email, phone, message |
| Partnership Application | PART | Business contact data |
| Newsletter Subscription | NEWS | Name, email |

**Uploads:** form-01 accepts a player passport photo. The player photo
editor in the staff portal accepts image uploads (`Player.photo`,
`ImageField`). Neither has server-side type/size validation beyond
Pillow's format sniffing on the model field (see R11).

**On-device copies (Phase 3):** while a visitor fills any form, a draft
autosaves to their browser's `localStorage`; if the server is unreachable
at submit time, the submission is queued there too. Both expire after 48
hours, the queue holds at most 5 per form, and successful delivery clears
the draft. The form-10 page discloses this on the form itself. The API
base URL (`site-config.js`) must be set on the public host — with it
empty the site runs in demo mode and forms pretend success.

### 2.3 User roles (current state)

| Role | Implementation | Can do today |
|---|---|---|
| Anonymous visitor | none | Submit forms, view published content |
| Parent/Guardian | `Guardian` profile + `GuardianPlayer` links | See own children, announcements, own complaints, change own password |
| Academy Staff | any user with `is_staff` (+ `Academy Staff` group, Phase 1) | All non-safeguarding portal work: submissions ledger (no form-10 rows exist), players, fixtures, invites, complaints, announcements. **Cannot see or infer that safeguarding reports exist** |
| Portal Administrator | `Portal Administrators` group (Phase 1) | User/account management in Django admin; no safeguarding access |
| Superuser | `is_superuser` | Django admin — **safeguarding store excluded without the DSO role** |
| **DSO (Designated Safeguarding Officer)** | **`DSO (Designated Safeguarding Officer)` group** — granted via `manage.py sp_dso grant <username>` (Phase 1) | The restricted store: `/portal/dso/` queue, report detail, status workflow, case notes, audit log; read-only admin views of the two models |

There are **no model permissions beyond the DSO group** — the staff portal
still authorises non-safeguarding sections on `is_staff` alone (Phase 3
will tighten the medical/ID data in the ledger; see R13).

### 2.4 Emails sent

| Email | Trigger | Recipient | Content |
|---|---|---|---|
| Submission notification | non-safeguarding form POST | `EMAIL_TO` (general academy inbox) | Full flattened answers |
| Branded auto-reply | non-safeguarding form POST (if visitor email found + `AUTO_REPLY=1`) | visitor | Confirmation + reference number (safe) |
| **Safeguarding DSO notification** | **form-10 POST (Phase 1)** | **`DSO_EMAIL` only — never the general inbox** | **Minimal: "a report is waiting in the DSO desk" + reference + portal link. No narrative, child name or reporter identity (tested in T19) ** |
| **Safeguarding reporter acknowledgment** | form-10 POST, confidential + email present (Phase 1) | the reporter | Neutral subject; reference + emergency numbers; no case content |
| Guardian invitation | staff clicks "Approve & invite guardian" | guardian email | One-time activation link (72 h) |
| Complaint notifications | new complaint / staff reply | guardian / assigned staff | Subject + link |
| QC redirect | `SP_MAIL_REDIRECT` set | redirect inbox | All outbound mail redirected (demo mode) |

Email is **off** until `RESEND_API_KEY` is set; delivery is untested with a
verified domain (R15).

### 2.5 External services

| Service | Use | Credential |
|---|---|---|
| Resend API (`api.resend.com`) | all outbound email | `RESEND_API_KEY` (bearer) |
| Let's Encrypt (certbot) | TLS certificates, `--with-tls` | none (ACME account per host) |
| No other third parties | — | — |

### 2.6 Secrets & credentials (after Phase 0)

| Secret | Where it lives | Generation (Phase 0 policy) |
|---|---|---|
| `DJANGO_SECRET_KEY` | `backend/.env` (never Git) | `secrets.token_urlsafe(48)` at install; no insecure default accepted in production mode |
| `RESEND_API_KEY` | `backend/.env` | owner-provided; no default |
| Staff admin password | set on the superuser account | `SP_ADMIN_PASS` env, **or** randomly generated and displayed **once** at install; **no default password in source** (removed in Phase 0) |
| Demo parent password (demo data only) | seeded account | randomly generated per install, displayed once; **no fixed password, no real email in source** (removed in Phase 0) |
| Guardian activation tokens | DB, 64-char random, 72 h expiry | single-use |
| `DSO_EMAIL` (Phase 1) | `backend/.env` | the DSO's private inbox — NOT a secret, but a data-protection control: unset means desk-only notifications |

### 2.7 Deployment & operational scripts

| Artefact | Role |
|---|---|
| `install.sh` | One-shot installer (venv, .env, migrate, superuser, seeds, wiring, systemd, nginx, TLS, backups) |
| `sp.sh` | start/stop/restart/status/logs/health/backup (backup = sqlite snapshot + media + .env tarball, 14-day rotation, stored **on the same host**) |
| `templates/sp-backend.service`, `sp-site.service`, `sp-backup.{service,timer}` | systemd units |
| `templates/nginx.conf`, `nginx-tls.conf` | reverse proxy (TLS profile: Mozilla intermediate, HSTS, 12 MB uploads) |
| `templates/uninstall.sh` | removal |
| `backend/.env.example`, `backend/.env.production.example` (new in Phase 0) | environment templates |
| `SAFEGUARDING-RUNBOOK.md` (new in Phase 1) | DSO operating runbook: roles, workflow, escalation ladder, manual QA script, residual risks |
| `backend/submissions/management/commands/sp_dso.py` (new in Phase 1) | grant/revoke/list the DSO role |
| `backend/submissions/tests/` (new in Phase 1) | permission-isolation + safeguarding test suite (`manage.py test`) |
| `backend/submissions/middleware.py` (new in Phase 2) | `SecurityHeadersMiddleware` (CSP / Permissions-Policy / COOP on every Django response) + `AdminLoginThrottle` (per-IP admin login throttling) |
| `backend/submissions/portal_auth.py` (new in Phase 2) | enumeration-free password reset for BOTH portals + branded 404/500 handlers |
| `backend/submissions/portal_assets/reset-*.html`, `error-*.html` (new in Phase 2) | branded reset + error pages |
| `site/404.html`, `site/50x.html` (new in Phase 2) | branded static-site error pages (wired via nginx `error_page`) |
| `site/policy-data-privacy.html` (new in Phase 3) | public data-privacy notice (Kenya DPA 2019): per-form collection table, access map, device-copy behaviour, retention approach, rights |
| `site/assets/js/shared/sp-forms.js` v3 (rewritten in Phase 3) | truthful submission contract: success only after server ack (real reference), honest offline/rejected panels, 48 h device copies + drafts, retry notification, honeypot |
| Git repository (new in Phase 0) | reviewable change history; `.gitignore` blocks .env/db/media/logs/backups |

---

## 3. Data classification

All categories except PUBLIC concern **children** (academy players), their
guardians, or reporters. Kenya Data Protection Act 2019 applies; medical
and safeguarding data are special-category-equivalent and attract the
highest duty of care.

| Class | Data | Stored in | Who can see it today | Required control |
|---|---|---|---|---|
| **PUBLIC** | published fixtures, published player cards (name, number, position, age, height, motto, photo) | `Fixture`, `Player` (`is_published`) | everyone (by design, with consent flow via form-09) | keep; verify consent before publishing |
| **PERSONAL** | names, DOB, phone, WhatsApp, email, residential area, sub-county, school, occupation, guardian relationship | `FormSubmission.payload`, `Guardian` | any staff (submissions ledger), superuser | staff-role gate (P1), minimisation (P3), retention policy (P1) |
| **SPECIAL-CATEGORY (MEDICAL)** | blood group, allergies, chronic conditions, injuries/surgeries, NHIF/insurance numbers, physician details, medical declarations | `FormSubmission.payload` | any staff + general inbox | restrict to authorised roles; **remove from email bodies**; question necessity (P3) |
| **ID DOCUMENTS** | Birth Certificate/UPI No. (child), National ID/Passport No. (guardian), police OB numbers | `FormSubmission.payload` | any staff + general inbox | high fraud risk; collect only if strictly necessary (P3 decision for owner) |
| **CHILDREN'S MEDIA** | passport photo uploads, player photos | `media/` on disk | anyone with the URL (`/media/` unauthenticated) + all staff | auth-gate or protect media (P2/P5), consent verification (P3) |
| **SAFEGUARDING-RESTRICTED** | entire form-10 payload (narrative, child, persons in question, witnesses, disclosure history) | `FormSubmission.payload` (generic row!) | **any staff, general inbox, superuser** — **unacceptable** | dedicated model + DSO-only access + minimal notification email + audit log (P1) |
| **AUTH / SECURITY** | password hashes, session cookies, activation tokens, IPs, user agents | Django tables, `FormSubmission.ip` | superuser (admin) | standard; keep tokens single-use + short-lived |

---

## 4. Known risks register

Severity × (likelihood, impact) — the single most important table in this
document. "Phase" = the planned remediation phase.

| ID | Sev | Risk | Status / Phase |
|---|---|---|---|
| R1 | **CRITICAL** | Safeguarding reports (form-10) are emailed **in full** (child name + narrative + witnesses) to the general academy inbox, and stored as generic ledger rows readable by **any** staff account and in the staff dashboard | **FIXED in Phase 1** — dedicated restricted model; DSO-only desk; minimal notification to `DSO_EMAIL` only (T16–T19) |
| R2 | **CRITICAL** | No DSO role / no permission model: `is_staff` grants access to everything, including safeguarding reports; no way to restrict or delegate | **FIXED in Phase 1** — DSO group via `sp_dso` grant; staff/superuser/parent locked out (T17, T21) |
| R3 | **HIGH** | No audit trail on access or status changes (who viewed/changed what, when) | **FIXED in Phase 1 (safeguarding scope)** — append-only `SafeguardingAuditEntry`; updates/deletes raise (T18, T24). Residual: audit covers the safeguarding store only |
| R13a | **HIGH** | Site claimed "100% Whistleblower Protection" (legally inaccurate) | **CLOSED** — replaced in Phase 1 with legally-careful "Confidential Reporting" wording incl. statutory-sharing caveat; **owner-approved as-is 2026-10-23** (gate-1) |
| R4 | **HIGH** | Staff login has no rate limiting / lockout (parent login does) → credential stuffing | **FIXED in Phase 2** — per-IP throttle 8 fails/15 min on staff portal login AND Django admin login (branded 429; T28–T30) |
| R5 | **HIGH** | No self-service password reset for staff or parents; no non-disclosing account recovery | **FIXED in Phase 2** — `/portal/reset/` + `/portal/parents/reset/`: identical neutral response for known/unknown accounts, one-use 1h links, PBKDF2 timing equaliser, request throttling + honeypot (T31–T34) |
| R6 | **MEDIUM** | `X-Forwarded-For` / `X-Forwarded-Proto` trusted unconditionally — clients can spoof IPs (rate-limit bypass) when not behind the proxy | **FIXED in Phase 2** — `SECURE_PROXY_SSL_HEADER` now opt-in via `TRUST_PROXY_HEADER=1` (installer writes it with `--with-nginx`); default off (T36) |
| R7 | **HIGH** | Settings failed **open**: wildcard hosts + wildcard CORS + insecure fallback secret key were the defaults; nothing refused to boot | **FIXED in Phase 0** — `SP_ENV=production` fails closed (T1–T5) |
| R8 | **CRITICAL** | Deterministic privileged credential: hardcoded default admin password in `install.sh`, echoed in every install banner (also on upgrades where it no longer matched) | **FIXED in Phase 0** — no default; `SP_ADMIN_PASS` or random one-time display |
| R9 | **MEDIUM** | Demo seed created a parent account with a real personal Gmail address + fixed password, printed in the banner | **FIXED in Phase 0** — fictional address + per-install random password |
| R10 | **MEDIUM** | No CSP; HSTS only at nginx (plain-HTTP installs unprotected); no `X-Content-Type-Options` etc. from Django | **Largely FIXED in Phase 2** — CSP/Permissions-Policy/COOP/nosniff/Referrer-Policy/XFO on all Django responses; nginx templates add the same set for the static site + branded error pages; env-driven HSTS for direct-HTTPS hosts. Residual: CSP keeps `unsafe-inline` for scripts (R27) |
| R11 | **HIGH** | Uploads: no server-side size/type validation or malware-scanning strategy (player photos, form-01 passport photo — note form-01 upload path not wired to disk yet, stored as payload reference only) | **Player photos FIXED in Phase 2** — full Pillow decode (renamed/truncated files rejected), format-checked, re-encoded with EXIF/GPS stripped, 40M-pixel bomb cap, stored extension matches real format (T37–T39). **Phase 3:** the form-01 photo field now says honestly that files are not attached online (bring a printed photo); wiring the upload remains an owner decision (would also need media auth-gating, R17). Residual: malware scanning (Phase 5) |
| R12 | **HIGH** | Form UX truthfulness: success UI can appear before the backend acknowledges (offline queue); "saved on this device" vs "received" not clearly distinguished; no reference number in offline state | **FIXED in Phase 3** — success screens now appear ONLY after the server acknowledges, showing the REAL reference (fabricated client-side refs removed from all 13 pages); offline/rejected states show an honest "Not sent yet / Not sent" panel, keep the answers on the page, and explain the 48-hour device copy; a later successful retry shows the real reference on screen; all success-modal copy rewritten to remove untrue claims ("Executive Committee", "email and SMS routed", "officially recorded in registry", "Under Immediate Assessment", "Assessment Slot Booked") (T43–T45) |
| R13 | **HIGH** | Data minimisation: form-01 collects ID numbers, full medical history, full home address — likely disproportionate | **CLOSED at gate-3 (2026-10-23).** Online form minimised: Birth Certificate/UPI and guardian National ID/Passport fields removed entirely; the medical section replaced by ONE optional "conditions or allergies coaches should know" note; a full medical form (blood group, insurance, doctor, injuries) moves to paper with the coach at enrolment; emergency-treatment authorisation kept (safety-critical). Privacy page + form copy updated to say exactly this |
| R25 | **MEDIUM** | Reporter's browser keeps an offline copy of a safeguarding submission in `localStorage` when the server is unreachable | **FIXED in Phase 3** — offline copies and drafts now expire after 48 hours (queue capped at 5, was 20); the form-10 page states plainly that a copy is kept on this device, for how long, and advises a trusted device; the offline panel for form-10 tells reporters in immediate danger to call Childline 116 instead of waiting (T46) |
| R26 | **MEDIUM** | Staff portal's other sections (form-01 medical data etc.) remain visible to ALL staff accounts | **FIXED in Phase 3** — medical and ID values in the ledger answer sheet are visible only to Portal Administrators and superusers; ordinary staff see a mask + "restricted" note; notification emails carry the same restriction (T47) |
| R14 | **MEDIUM** | SQLite single file on one host; backups local-only, same-disk; no restore drill documented for operators (script exists) | **Largely FIXED in Phase 5** — `restore-drill.sh` ships with the kit (installed by install.sh, referenced by `sp.sh backup`): extracts the newest bundle into a scratch dir, integrity-checks the DB, boots a throwaway instance on the restored data, probes it over HTTP and compares record counts with the live DB — executed here with a real bundle: **10/10 PASS** (T56). Residual: backups still local/same-disk — copying bundles off-host remains an owner-side action |
| R15 | **MEDIUM** | Email deliverability unverified (no verified sending domain test); email failures are recorded but not alerted | **Owner-confirmed working (2026-10-24): "mails do get delivered."** Deliverability guidance remains in EMAIL-SETUP-GUIDE (SPF/DKIM/DMARC progression, verification, DSO/reset-mail priority) as recommended hardening — publishing the DNS records is still advised when the domain panel is available. "Failures are recorded not alerted" still stands — pair with the `/healthz/` uptime monitor |
| R16 | **MEDIUM** | Debug/error leakage: `DEBUG=0` default, but nothing prevented `DEBUG=1` in a production env; stack traces would reach visitors | **FIXED in Phase 0** (guard) — custom 500 page **added in Phase 2**: branded, no internals, 404 also branded (Django + static site) (T40) |
| R17 | **MEDIUM** | `/media/` served without auth — any player photo URL is fetchable unauthenticated once known; unpublished photos same | **FIXED in Phase 5** — `/media/` now routes through `portal.media_serve`: published players' photos stay public (squad pages embed them, media-consented); every other file requires a staff session or the OWNING guardian; traversal and missing paths return the same plain 404 (no existence oracle); orphan files (no player row) fail closed to staff-only (T53) |
| R18 | **INFO** | Public form API is CSRF-exempt (cross-origin POST by design). Mitigations: CORS allow-list, per-IP rate limit, honeypot. Re-evaluate after CORS lockdown becomes default | **Reviewed in Phase 2 — kept by design** (static site may be served from a different origin in dev). Added: cross-form aggregate per-IP cap so one IP cannot multiply its budget across the 13 forms (T42). Revisit when the site is permanently same-origin (Phase 5) |
| R19 | **LOW** | `SECURE_PROXY_SSL_HEADER` active even without a proxy (pairs with R6) | **FIXED in Phase 2** — opt-in via `TRUST_PROXY_HEADER` (T36) |
| R20 | **MEDIUM** | Single server, single admin account, no monitoring/alerting/uptime checks; dependency versions unpinned (`>=`) | **Largely FIXED in Phase 5** — dependencies pinned exactly (`requirements.txt`, verified install); `/healthz/` liveness+DB probe on both `''` and `/healthz/` (503 on DB failure, no internals leaked); CI workflow (`.github/workflows/ci.yml`: test suite + phase-0 guard on every push once hosted); portable `scripts/phase0_guard_tests.py` inside the kit; restore drill for backups. Residual: an actual external uptime monitor / error-tracking service remains owner-side (point it at /healthz/) |

*(R25–R26 added in Phase 1. R27–R28 added in Phase 2.)*

| ID | Sev | Risk | Status / Phase |
|---|---|---|---|
| R25 | **MEDIUM** | Reporter's browser keeps an offline copy of a safeguarding submission in `localStorage` when the server is unreachable | Open — Phase 3 (messaging + retention window) |
| R26 | **MEDIUM** | Staff portal's other sections (form-01 medical data etc.) remain visible to ALL staff accounts | Open — Phase 3 (data minimisation / role scoping) |
| R27 | **MEDIUM** | CSP requires `unsafe-inline` for scripts and styles: the public site uses inline `onerror=` handlers on 36 pages and the portal dashboard ships one inline `<script>` block. The policy still blocks `object-src`, `base-uri`, `form-action`, `frame-ancestors` | **CLOSED in Phase 5 (scripts).** All 240 inline `onerror=` handlers across 37 pages became `data-fb`/`data-fb-hide` attributes handled by a shared `img-fallback.js` (capture-phase listener + triple sweep); the three pages with inline `<script>` blocks (core-values, our-story, vision-mission) load external files; the portal dashboard script moved to `/portal/assets/dash.js` (staff-only allow-list); the inline `onclick` toast closer is bound in index-2.js; CSP is now `script-src 'self'` everywhere (Django middleware + both nginx templates). ALSO fixed two latent CSP-vs-reality bugs QA had missed because the static test server sends no headers: Google Fonts (style-src/font-src 'self' would have blocked them) and four CDN scripts on index.html — both now self-hosted (36 woff2 + lenis/gsap/ScrollTrigger vendored; splittype replaced by a minimal local shim since the package vanished from CDNs). style-src keeps 'unsafe-inline' for inline style attributes (documented, no script vector) (T54, T57–T59) |
| R28 | **LOW** | Login throttles count per IP in the process-local cache: they reset on backend restart, and a shared NAT (school office) can hit the cap for everyone behind it. Window is deliberately short (15 min) and thresholds generous (8) | **Two mitigations now shipped.** (1) Phase 5: `SP_CACHE=db` moves the cache (and therefore every throttle counter) into the database, shared across all gunicorn workers (one-time `manage.py createcachetable`); pairs with the `DB_ENGINE=postgres` switch. (2) **Phase 6 finding + fix:** acceptance testing proved that with the previously shipped `--workers 3`, the per-process counters never reached the 8-failure threshold (attempts round-robined across workers) — the throttle was inert in the default install. Both service templates now ship `--workers 1 --threads 8` (one process, gthread): counters are process-shared, SQLite writes stay single-process, concurrency comes from threads. Scaling out later = PostgreSQL + `SP_CACHE=db` + more workers, as documented in the templates |

---

## 5. Launch checklist (final gate — all must be true)

- [x] Safeguarding access restricted to authorised DSO role, verified by tests + manual review (Phase 1 ✅ — T17, T21)
- [x] All safeguarding access/status changes produce immutable audit entries (Phase 1 ✅ — T18, T24)
- [x] Notification emails contain no report narrative or child data (Phase 1 ✅ — T19)
- [x] Privacy/legal text reviewed and approved by owner; "100% Whistleblower Protection" replaced (Phase 1 ✅ — new "Confidential Reporting" wording **owner-approved as-is, 2026-10-23**, gate-1 chat approval)
- [ ] DSO appointed by name and `DSO_EMAIL` configured on the production host (Phase 1 built the mechanism — the owner must staff it)
- [x] Self-service password reset for both portals without account enumeration (Phase 2 ✅ — T31–T34)
- [x] Login throttling on every login surface: staff portal, parent portal, Django admin (Phase 2 ✅ — T28–T30; parent portal already had it)
- [x] Security headers (CSP + Permissions-Policy + COOP + nosniff + Referrer-Policy + XFO) on every response, static site included via nginx (Phase 2 ✅ — T35)
- [x] Uploads content-verified and metadata-stripped (Phase 2 ✅ — T37–T39)
- [x] Branded, non-leaking 404/500 pages on both the Django app and the static site (Phase 2 ✅ — T40)
- [ ] Real production credentials configured; **no default/deterministic passwords anywhere** (Phase 0 ✅ for source; operator must still change the generated one after first login)
- [ ] `SP_ENV=production` active; startup fails closed on insecure config (Phase 0 ✅)
- [x] All forms: tested success / validation-error / offline / retry / backend-failure flows (Phase 3 ✅ — T43–T50: all 13 forms verified in a real browser; server guards unit-tested)
- [ ] `site-config.js` `API_BASE` set to the real backend on the public host — demo mode (empty `API_BASE`) must never face visitors (forms would pretend success with a DEMO reference) — owner action at deploy time
- [x] Backups verified by an actual restore; restore drill documented (Phase 5 ✅ — `restore-drill.sh` executed against a real bundle: 10/10 PASS, T56; re-run quarterly and after upgrades)
- [ ] Monitoring, health checks, error tracking, named operational owner (Phase 5 ✅ built: `/healthz/` liveness+DB probe (T55); owner action: point an uptime monitor at it and name the operational owner)
- [ ] Staging acceptance tests signed off by academy staff with fictional data (Phase 6 ✅ agent-side: fresh-install acceptance matrix 96/96 + browser journeys + visual QA, T62–T67; the academy-staff sign-off itself happens at staging with the same fictional data — owner-side)
- [ ] Rollback plan written and rehearsed (Phase 5)
- [ ] `ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` locked to the real domain (installer `--domain` + Phase 0 example)

**Recommended first release:** brochure site + minimal contact/trial-interest
form only. Registration, medical records, guardian accounts, payments and
safeguarding workflows stay disabled until their individual gates pass.

---

## 6. Operating modes (Phase 0 definitions)

| Mode | How | Behaviour |
|---|---|---|
| **Development** (default) | `SP_ENV` unset or `development` | Permissive defaults; wildcard hosts/CORS allowed; starter .env from installer |
| **Production** | `SP_ENV=production` in `backend/.env` (installer `--production`, or by hand from `.env.production.example`) | **Fails closed at startup** (every `manage.py` command, gunicorn worker import) if ANY of: `DEBUG=1`; `ALLOWED_HOSTS` empty/`*`; `CORS_ALLOW_ALL=1`; `DJANGO_SECRET_KEY` missing/known-insecure/<50 chars; `SESSION_COOKIE_SECURE=0`; `CSRF_COOKIE_SECURE=0` |

The installer's `--production` flag *verifies* the configuration by
actually booting the app under the guard before writing `SP_ENV=production`;
if verification fails, the flag is **not** written and the install ends
with an error listing the offending values.

---

## 7. Phase status

| Phase | Scope | Status |
|---|---|---|
| 0 | Safe baseline (inventory, this document, env examples, git hygiene, credential removal, fail-closed production mode) | **COMPLETE** — kit rev 12 |
| 1 | Safeguarding/data-protection redesign (DSO role, restricted model, audit log, minimal notifications, tests) | **COMPLETE** — kit rev 13. Gate items: legal wording **approved as-is 2026-10-23**; appointing the DSO + setting `DSO_EMAIL` remain owner-side server actions (mechanism built, tested, documented) |
| 2 | Auth & application hardening (rate limits, resets, headers/CSP, proxy trust, upload validation, abuse controls, error hygiene) | **COMPLETE — GATED.** Kit rev 14. Evidence T28–T42. Gate-2 closed 2026-10-23: owner accepted the new behaviours (reset emails, login lockouts after 8 failures/15 min, 12-hour session expiry) via chat approval ("continue") |
| 3 | Truthful, resilient public forms (states, validation parity, drafts, accessibility, privacy notice, minimisation) | **COMPLETE — GATED.** Kit rev 15. Evidence T43–T50. Gate-3 closed 2026-10-23 via chat approval ("continue"): (a) new form behaviours accepted; (b) form-01 minimised per the recommended default — ID/insurance numbers dropped, one optional health note kept, full medical form moved to paper (R13 CLOSED); (c) privacy-page wording accepted as-is; (d) photo-field honest note kept (upload wiring remains a later option tied to media auth-gating, now built in Phase 5) |
| 4 | User-facing content gaps (owner-provided content only) | **UNBLOCKED — IMPLEMENTED (kit rev 18).** Owner inputs received 2026-10-24: (a) chairman's message + leadership names (Dr. Stephen Abuor, Mrs. Joyleen Mbwika) confirmed real as published — no edits; (b) coaching staff made **admin-settable** — new `Coach` model managed in Django admin (hardened photo storage: Pillow-verified, EXIF/GPS-stripped, 40-Mpx cap, extension-matched), public `/api/coaches/` endpoint, technical-team section on the squads page with honest empty state; (c) **enquiry policy**: fees, programme specifics, partnership terms and contact details are no longer published — every published email address (16 spots incl. `partnerships@`) and every social link/mention removed site-wide, copy re-routed to the forms; offline-form mailto fallbacks removed; (d) squad-page truthfulness: fictional captain cards and the fictional-roster live-fallback removed — live sites render only published players/captains, with honest "being finalised" states (demo mode keeps its showcase data); fabricated stats ("38 Clean Sheets") replaced. Retention policy set (see runbook §5). Remaining owner-side: upload real player photos + publish rosters via the admin |
| 5 | Production engineering (tests, CI, Docker/host, PostgreSQL, object storage, monitoring, email verification, pinning) | **COMPLETE — GATED.** Kit rev 16. Evidence T52–T59. Done: pinned deps; `/healthz/`; media auth-gating (R17); CSP inline-JS refactor + self-hosted fonts/libs (R27); restore drill (R14); optional PostgreSQL + shared DB cache (R28); CI workflow + portable guard script; email deliverability guide (R15). Out of sandbox scope by constraint (documented, owner-side): Docker/host, object storage, DNS records, external monitoring. **Gate-5 closed 2026-10-24 via chat approval ("continue"):** (a) CSP/behaviour changes accepted (no functional change observed); (b) media-gating policy accepted (published photos public, everything else staff/owning-guardian); (c) form-01 minimisation accepted as applied at gate-3; (d) **SQLite stays the default** — PostgreSQL remains a documented config option (`DB_ENGINE=postgres` + `DB_*`), no migration now |
| 6 | Real-world acceptance testing with fictional data | **COMPLETE** — kit rev 17. Fresh install from the shipped v16 zip in a scratch directory, then the full journey matrix with fictional data: automated suites, live API/portal walkthroughs, DSO desk, resets, throttles, media gate, 404/500, restore drill, browser QA. Evidence T62–T67. Remaining owner-side: staging sign-off by academy staff, production credentials, domain/hosts locking, uptime monitor |
| 7 | Owner feature round: Results page + per-child QR codes (2026-10-26) | **COMPLETE** — kit rev 19. Dedicated public Results page (`results.html`, Coming Soon until the office enters results in the admin; auto-populates from `/api/results/`, grouped by month, W/D/L badges, honest empty state, cross-linked from the home fixtures board and every nav/footer); QR code per child pointing at a public player profile (`player.html?ref=…` — public fields only, fail-closed 404 for unpublished players, `noindex`); printable QR cards (staff bulk `/portal/qr/`, staff single `/portal/qr/<ref>/`, guardian own-child `/portal/parents/qr/<ref>/`) generated server-side with pinned `segno`; dashboard player cards gained a QR button, parents' child page a print link. Latent CSP bug fixed: inline `onerror=` in 9 JS nav templates → `data-fb` (Phase-5 sweep had only covered HTML files). Evidence T71–T74 |
| 8 | Site polish round: SEO / copy / numbering / stat strips / forms hub / contact / typography & contrast / images / duplicate-page review (2026-10-26 owner brief) | **COMPLETE** — kit rev 20. Every owner-independent improvement landed inside all standing constraints; full record in CHANGELOG-REV20.md. Owner decisions requested (5): contact “8 Development Programmes” count, partners “4 Active Squads” vs 6, partner-with-us.html redirect confirmation, contact response-time wording, education-life-skills attribution reading. Evidence T75–T78 |
| 9 | Owner UI round (2026-10-26 request): remove the carousel, ensure no black, parallax on the photo heroes; every squad player card carries the player's unique QR; plus backend test-suite portability | **COMPLETE** — kit rev 21. Marquee strip removed from all 14 pages (dead CSS/JS swept, seams fixed); real pre-existing black-wave bug fixed (dead selector `.tide .w1 path`) plus near-black areas recolored to the brand navy family and the footer unified navy-4 site-wide; parallax wired on all 16 photo heroes (new reduced-motion-safe `hero-parallax.js`); cache busts ?v22/?v23; squad dossier modal shows each player's unique QR → public profile (self-hosted `qr.min.js`, MIT, CSP-safe; API refs in live mode, squad-code refs in demo; fail-closed hide; demo-profile fallback in `sp-player.js`), locked by new test `test_squad_player_cards_carry_unique_qr`; `test_phase7.py` no longer hardcodes the build machine path. Full record in CHANGELOG-REV21.md. Evidence T79–T83 |
| 10 | Real register import (2026-11-03 owner request, Excel + two photo archives): replace demo squads with the real academy register | **COMPLETE** — kit rev 22. the-squad page rebuilt on the real 2026–27 register: squads U12(18)/U14(16)/U16(11)/U19(5) + Féminin (honest “being finalised” panel — no register rows); position-aware formation placement (new BANDS map) + bench strip so all 50 registered players stay visible and clickable; 29 real player photos wired via the register's inline refs; dossier chips factual only (no fabricated ratings/height/foot); captains honest-TBC; stats 50/4/5; QR refs stable per player (U12-01…U19-05) across the-squad.js v26, sp-player.js rev 22 and regenerated backend/player_seed.json; nav mega-menu + homepage pathway relabelled sitewide (41 pages); one test assertion moved from the retired demo ref to real refs. Full record in CHANGELOG-REV22.md. Evidence T84 |

---

## 8. Test evidence

Every phase appends rows. "PASS" claims must cite command/output kept in
the kit's FIX-NOTES or the agent worklog.

| ID | Date | Test | Method | Result |
|---|---|---|---|---|
| T1 | 2026-10-23 | Production guard rejects `DEBUG=1` under `SP_ENV=production` | settings import in subprocess | **PASS** — `ImproperlyConfigured`, exit≠0 |
| T2 | 2026-10-23 | Guard rejects wildcard `ALLOWED_HOSTS=*` | same | **PASS** |
| T3 | 2026-10-23 | Guard rejects `CORS_ALLOW_ALL=1` | same | **PASS** |
| T4 | 2026-10-23 | Guard rejects missing/insecure/short `DJANGO_SECRET_KEY` | same | **PASS** (3 variants) |
| T5 | 2026-10-23 | Guard rejects insecure cookies (`SESSION_COOKIE_SECURE=0` / `CSRF_COOKIE_SECURE=0`) | same | **PASS** |
| T6 | 2026-10-23 | Guard accepts a fully hardened env (no false positive) | subprocess boot + `manage.py check` | **PASS** |
| T7 | 2026-10-23 | Development mode unaffected (no SP_ENV) | fresh install + smoke | **PASS** |
| T8 | 2026-10-23 | No default admin password: install without `SP_ADMIN_PASS` generates random 20-char password, shown once; `grep` finds no default in source | fresh install + banner capture + `git grep` | **PASS** |
| T9 | 2026-10-23 | `SP_ADMIN_PASS` is honoured and never echoed in banner | install with env set | **PASS** |
| T10 | 2026-10-23 | Upgrade re-run keeps existing admin password; banner no longer prints any password on upgrades | second install run + login check | **PASS** |
| T11 | 2026-10-23 | Demo parent: fictional email + random password; the historical fixed demo credential and real personal email no longer appear anywhere in the kit | `--demo-data` install + login + `git grep` | **PASS** |
| T12 | 2026-10-23 | `--production` without `--domain` errors; `--production` on locked+TLS .env writes `SP_ENV=production`; on insecure .env refuses and lists reasons | installer runs | **PASS** |
| T13 | 2026-10-23 | Git hygiene: `.env`, `db.sqlite3`, `media/`, `logs/`, `backups/` never tracked | `git init` + `git ls-files` audit + `git check-ignore` | **PASS** |
| T14 | 2026-10-23 | Kit zip contains no secrets/.git/db | build + programmatic inspection | **PASS** |
| T15 | 2026-10-23 | Parser: full confidential payload → structured fields; anonymous strips identity; category lists + legacy shapes; unknown keys preserved | `manage.py test submissions` (unit) | **PASS** |
| T16 | 2026-10-23 | Form-10 POST creates a `SafeguardingReport` and **zero** ledger rows; audit writes received+notified | Django test client over HTTP | **PASS** |
| T17 | 2026-10-23 | Access matrix: anonymous→login, parent→bounce, staff→neutral 403, superuser (no role)→403, DSO→200, revoked role→403; staff cannot POST status/notes | `manage.py test` + live smoke | **PASS** |
| T18 | 2026-10-23 | Audit entries refuse update and delete (RuntimeError both) | unit tests | **PASS** |
| T19 | 2026-10-23 | DSO notification contains no narrative/child/reporter identity (subject+text+html scanned); ack is neutral-subject; anonymous gets no ack; unset `DSO_EMAIL` sends nothing to any academy inbox | mocked `resend_send` recorder | **PASS** |
| T20 | 2026-10-23 | Legacy migration: old ledger row moved to the restricted store + audited; ledger emptied; idempotent re-run | `migrate_legacy_rows()` unit test | **PASS** |
| T21 | 2026-10-23 | Staff dashboard shows no `SP-SAFE` refs / no DSO nav / no form-10 slug even with reports present; DSO nav appears only for the DSO | dashboard HTML assertions | **PASS** |
| T22 | 2026-10-23 | Django admin: safeguarding models hidden from staff AND bare superusers; DSO gets read-only views (no add/change/delete) | admin client tests | **PASS** |
| T23 | 2026-10-23 | DSO desk workflow: status transitions audited with old→new, first change auto-assigns, invalid status rejected, case notes verbatim, queue hides narrative | desk tests with `follow=True` | **PASS** |
| T24 | 2026-10-23 | Full lifecycle received→under_review→escalated→closed leaves a complete trail (3× status_changed, 3× note_added, 6× viewed + received + notified) | desk test | **PASS** |
| T25 | 2026-10-23 | Groups: DSO holds exactly 3 view permissions (least privilege); Portal Administrators hold account perms but zero safeguarding perms | migration + assertions | **PASS** |
| T26 | 2026-10-23 | Live smoke (real server, real sessions, fictional report): 19/19 checks — storage isolation, 403s, DSO queue/detail/status/note/audit, DB state | `scripts/p1_smoke.sh` | **PASS (19/19)** |
| T27 | 2026-10-23 | Visual QA of the new DSO desk (dashboard, queue, detail, audit) desktop 1440px + mobile 390px, and the revised form-10 copy box | agent-browser screenshots + VLM review | **PASS (6/6 after 2 fixes)** |
| T28 | 2026-10-23 | Staff portal login: 8 wrong passwords from one IP → 429 branded page with disabled form; 9th attempt blocked; different IP unaffected; correct login with 7 prior failures still works | `manage.py test` (unit) + live smoke | **PASS** |
| T29 | 2026-10-23 | Django admin login: same throttle via `AdminLoginThrottle` middleware; rest of the site stays reachable for that IP | unit + live smoke | **PASS** |
| T30 | 2026-10-23 | Login message hygiene: unknown user, wrong password, and valid-credentials-non-staff all return the identical "Wrong username or password" (no account-validity oracle); parent login likewise (paused accounts still get the informative message — post-auth only) | unit tests | **PASS** |
| T31 | 2026-10-23 | Reset request (both portals): known vs unknown account → identical status (200) + identical neutral page; email sent ONLY for real active accounts; page never echoes the typed address | unit + live smoke | **PASS** |
| T32 | 2026-10-23 | Reset email content: neutral subject/text + one-time link only; no username echo, no account details; expiry stated | mocked `resend_send` recorder | **PASS** |
| T33 | 2026-10-23 | Reset links: valid token opens the set-password form; setting a new password works and KILLS the token (400 on reuse); bad token / garbage uid → 400 neutral page; expiry enforced (`PASSWORD_RESET_TIMEOUT=1` + sleep) | unit + live smoke | **PASS** |
| T34 | 2026-10-23 | Reset abuse controls: 5 requests/IP/hour then silently swallowed; honeypot field swallows requests; weak/mismatched new passwords rejected with the old password intact | unit tests | **PASS** |
| T35 | 2026-10-23 | Security headers present on portal login, parent login, admin, API root, 404 and /media/ 404: CSP (object-src/base-uri/form-action/frame-ancestors locked), Permissions-Policy, COOP, nosniff, Referrer-Policy, XFO DENY; nginx templates carry the same set for the static site + `client_max_body_size 12m` added to the plain-:80 front (was missing — uploads >1 MB silently failed there) | unit + live smoke (curl -I) | **PASS** |
| T36 | 2026-10-23 | Proxy trust: `SECURE_PROXY_SSL_HEADER` is None by default and only set for `TRUST_PROXY_HEADER` ∈ {1,true,yes,on}; installer writes it with `--with-nginx` | unit test of `_proxy_ssl_header()` | **PASS** |
| T37 | 2026-10-23 | Upload content validation: text file named .jpg, HTML named .jpg, SVG renamed .jpg, truncated PNG all rejected 400; valid PNG/JPEG accepted | unit + live smoke | **PASS** |
| T38 | 2026-10-23 | Upload metadata stripping: JPEG with EXIF (orientation + software tag) re-encoded and stored WITHOUT any EXIF / GPS IFD; stored extension always matches the real format (PNG-bytes-as-.jpg stored as .png) | unit + live smoke (Pillow re-inspection of stored file) | **PASS** |
| T39 | 2026-10-23 | Decompression-bomb defence: 7000×6000 solid PNG (42 Mpx, under Pillow's own 89 M guard, over the app's 40 M cap) rejected before full decode with the "too large" message | unit test | **PASS** |
| T40 | 2026-10-23 | Branded 404/500: Django handler renders the branded page (no Traceback/settings/module paths); static-site 404.html + 50x.html wired via nginx `error_page` (internal); 500 handler logs path+ip, renders neutral page | unit tests + live smoke | **PASS** |
| T41 | 2026-10-23 | Session/auth settings pinned: cookies HttpOnly + SameSite=Lax, session age ≤12h, reset timeout ≤1h, nosniff on, XFO DENY; Phase 0 fail-closed guard still passes after the settings changes (all 12 guard cases) | settings assertions + `phase0_guard_tests.py` re-run | **PASS** |
| T42 | 2026-10-23 | Full suite regression: 89 automated tests (38 Phase 1 + 51 Phase 2) all pass; live smoke 25/25 (headers, throttles, reset flow, upload hardening, 404); visual QA 7/7 (login ×2, reset ×2, 404, mobile ×2) | `manage.py test submissions`, `scripts/p2_smoke.sh`, agent-browser + VLM | **PASS (89 + 25/25 + 7/7)** |
| T43 | 2026-10-23 | Truthful success states: form-08 and form-10 submitted in a real browser show the modal with the REAL server reference matching the database row; fabricated refs (`ENQ-2026-…`, `SAFE-2026-…` via `Math.random`) removed from all 13 pages; demo mode now shows a clearly-marked `DEMO-` code | agent-browser against live servers + DB comparison | **PASS** |
| T44 | 2026-10-23 | Offline truthfulness: with the network cut, submitting shows the honest "Not sent yet" panel (form stays, answers preserved, 48-h device copy explained, form-10 adds the Childline 116 urgency line); NO success modal appears; the queue entry carries a timestamp | agent-browser offline mode + localStorage inspection | **PASS** |
| T45 | 2026-10-23 | Retry + notification: queued submissions deliver automatically on the next visit once online; a discreet on-screen note shows the real reference for each; queue empties; delivered refs verified in the database | agent-browser reload + DB comparison | **PASS** |
| T46 | 2026-10-23 | Device-copy hygiene: drafts autosave while typing, survive reload, restore on "Continue", clear on "Start fresh" AND on successful submission (debounce race fixed); draft + queue entries expire after 48 h; queue capped at 5; form-10 page carries the on-device storage notice | agent-browser + code review | **PASS** |
| T47 | 2026-10-23 | R26 redaction: plain staff account sees masked medical/ID values + "restricted" note in the ledger answer sheet; portal administrator and superuser see full values; same values withheld from notification email bodies with an explanatory note; database keeps the full payload | unit tests + live browser + `scripts/p3_smoke.sh` | **PASS** |
| T48 | 2026-10-23 | Validation parity (server): empty/junk payloads, sentinel-only payloads, >200 fields, >20-item lists, >4000-char values, >64 KB bodies all rejected 4xx with honest messages and store nothing; newsletter requires a real email; an empty form-10 report is rejected; honeypot still fake-succeeds without storing | unit tests (22 new) + `scripts/p3_smoke.sh` | **PASS** |
| T49 | 2026-10-23 | Rejected-never-queued: a 429 rate-limit response shows the "Not sent" panel with the server's message, keeps the answers on the page, and does NOT create a localStorage queue entry (retrying immediately would hit the same limit) | agent-browser (61st submission in a minute) | **PASS** |
| T50 | 2026-10-23 | Page sweep + visual QA: all 13 form pages load with 0 JS errors, expose `SP_FORMS.finish`, and link the privacy notice (incl. partners.html after fix); privacy page renders 10 sections in the shared policy design; VLM review of 7 screenshots (modals, panels, restore bar, redaction, privacy page, mobile) — no defects (one false alarm on reveal-on-scroll full-page screenshots verified as an artefact) | agent-browser sweep + VLM | **PASS (13 pages, 7/7)** |
| T51 | 2026-10-23 | Full suite regression: 111 automated tests (89 prior + 22 Phase 3) all pass; Phase 0 guard tests 12/12; live smoke 17/17 | `manage.py test submissions`, `phase0_guard_tests.py`, `scripts/p3_smoke.sh` | **PASS (111 + 12 + 17/17)** |
| T52 | 2026-10-23 | Phase 5 suite: 133 automated tests (111 prior + 22 Phase 5) — healthz on both paths incl. 503-on-DB-failure, media gate matrix (anonymous/staff/owning guardian/other guardian/orphan/non-players dir/traversal/missing), portal asset ACL, settings switches (default/PG/cache via subprocess), regression guards for the numberless-player 500 and the Python-emitted inline onerror | `manage.py test submissions` | **PASS (133)** |
| T53 | 2026-10-23 | Media gating live (real server, real sessions): published photo anonymous 200; unpublished anonymous 404; traversal 404; staff 200; OWNING guardian 200; OTHER guardian 404; squad API still serves published photos | `scripts/p5_smoke.sh` T3 | **PASS (8/8)** |
| T54 | 2026-10-23 | CSP tightened and honored: `script-src 'self'` (no unsafe-inline) on portal login, admin login, healthz and 404; style-src keeps its documented inline allowance; dashboard page references external dash.js with ZERO inline code scripts; all 37 static pages carry zero inline event handlers and zero external css/js references | `scripts/p5_smoke.sh` T2/T5/T8 + refactor-script verify pass | **PASS** |
| T55 | 2026-10-23 | healthz: `''` and `/healthz/` both answer 200 `{ok:true}` against a live DB; DB failure returns 503 with no internals; admin login still renders under the tightened CSP | live smoke + unit tests | **PASS** |
| T56 | 2026-10-23 | Backup restore drill executed against a real bundle (sqlite snapshot + media + tar): archive extracts, integrity_check ok, media included, throwaway instance boots on restored data, /healthz/ + portal login + players API all 200 over HTTP, record counts identical to the live DB | `templates/restore-drill.sh` (kit) | **PASS (10/10)** |
| T57 | 2026-10-23 | Self-hosted assets: 36 woff2 font files + fonts.css replace Google Fonts on every page (computed styles confirm Fraunces/Work Sans actually render); lenis/gsap/ScrollTrigger vendored locally; splittype (package vanished from CDNs — the live reference was silently 404ing) replaced by a minimal local shim that restores the hero word-reveal | fetch script + browser computed-style checks | **PASS** |
| T58 | 2026-10-23 | Browser QA of changed pages: index (gsap/lenis/SplitType loaded, 0 console errors, 0 inline handlers), core-values/our-story/vision-mission (external page JS, reveals work, 0 errors), form-01 (6 sections, dropped fields absent, health note present, 0 errors), staff dashboard (dash.js external, view switching, 0 errors), admin login renders | agent-browser | **PASS** |
| T59 | 2026-10-23 | Photo-fallback chain (two bugs found and fixed during QA): portal/parent player-card photos use data-fb-hide="reveal-next" + /portal/assets/img-fallback.js (per-asset ACL: guardians can load it); broken photo → img hidden + monogram revealed on parent home, child page AND staff dashboard; verified against a stale-cache stale-server false alarm by fresh-boot re-test | agent-browser on fresh server | **PASS** |
| T60 | 2026-10-23 | Visual QA: 7 screenshots (homepage, core-values, form-01 section E, parent home + child, staff dashboard + players) — no overlap/overflow/broken layout/missing images | agent-browser + VLM review | **PASS (7/7)** |
| T61 | 2026-10-23 | Full Phase 5 regression: 133 tests + phase-0 guard 12/12 (portable kit copy) + live smoke 42/42 + CI workflow YAML parses with both jobs defined | `manage.py test`, `scripts/phase0_guard_tests.py` (kit), `scripts/p5_smoke.sh`, yaml parse | **PASS (133 + 12 + 42/42)** |
| T62 | 2026-10-24 | Phase 6 fresh install from the **shipped v16 zip** in a scratch directory (the owner's real path): installer completes 9/9 steps, boots gunicorn :8020 + static :8090, demo data seeds, admin password taken from `SP_ADMIN_PASS` (never echoed), demo-parent password random per install | `unzip` + `SP_ADMIN_PASS=… bash install.sh --demo-data` + banner capture | **PASS** |
| T63 | 2026-10-24 | Automated suites from the fresh install: 133/133 tests + portable phase-0 guard 12/12 (run with the installed venv python — plain `python3` fails with a clear message, itself a useful doc check) | `manage.py test submissions parents`, `scripts/phase0_guard_tests.py` | **PASS (133 + 12/12)** |
| T64 | 2026-10-24 | Live acceptance matrix against the installed stack (fictional data only), 14 groups: liveness + `sp.sh` stop/start restart; static site + minimised form-01; CSP/nosniff/XFO; form-01/02/08/newsletter submissions with real refs; payload guards (400/413/empty-report); form-10 → DSO desk end-to-end (queue, detail, status change, case note, full audit incl. received/notified/viewed/status_changed/note_added) with staff + superuser 403s and dashboard blindness; demo-parent journey (child, announcements, complaints, account); medical redaction (plain staff masked, portal admin full, safeguarding ref invisible); enumeration-free resets both portals + full token link flow (set, dead-on-reuse 400, new password logs in); media gate matrix (anon/staff/owning/other/traversal + dash.js ACL); upload hardening (fake jpg rejected, EXIF stripped from stored file); branded 404 app + site; staff + admin login throttles 429; backup bundle + restore drill | `scripts/p6_acceptance.sh` (persisted) | **PASS (96/96)** — after fixing one script-side squad-code collision |
| T65 | 2026-10-24 | **Real finding (R28 in the wild):** with the shipped `--workers 3`, 8 failed logins never tripped the 429 throttle — the per-process counters round-robined across workers (verified: 9th attempt 200). **Fix shipped:** both service templates (`templates/sp.sh`, `templates/sp-backend.service`) now run `--workers 1 --threads 8`; verified on the installed instance (9th attempt 429) and locked in with a regression check in the acceptance script (gunicorn must be master+1 process) | live throttle probe before/after + `pgrep -fc gunicorn` | **PASS (429 after fix; regression guard active)** |
| T66 | 2026-10-24 | Browser journeys on the fresh install (agent-browser, 1440×900): full form-01 registration across all 6 sections → success modal shows the REAL server reference `SP-REG-20261024-7A11`, matching the DB row exactly (the form correctly refused to submit while the required guardian signature was empty — no junk submissions); demo-parent login → child + announcements + complaints; staff dashboard (27 submissions, no safeguarding nav); DSO dashboard → queue (narratives hidden) → report detail → audit log; 0 console/page errors throughout | agent-browser + DB comparison | **PASS** |
| T67 | 2026-10-24 | Visual QA of 8 journey screenshots (homepage, form-01 success, parent home, staff dash, DSO dash/queue/detail/audit) | VLM review | **PASS (8/8)** — one initial FAIL on the homepage was the hero word-reveal animation caught mid-flight; re-shot after settle → PASS (same artefact class as Phase 3 QA) |
| T68 | 2026-10-24 | Phase 4 backend: `/api/coaches/` serves published coaches only, in sort order, correct shape (name/role/squad-label/bio/absolute photo URL); media gate `coaches/` branch — published photo anonymous 200, unpublished anonymous 404 / staff 200; `CoachPhotoStorage` strips EXIF + fixes extension on direct model saves and fails closed on non-images; admin form rejects renamed text files and bad extensions with friendly messages | `manage.py test submissions.tests.test_phase4` (13 tests) | **PASS (13/13)** |
| T69 | 2026-10-24 | Phase 4 regression: full suite 146/146 (133 prior + 13 Phase 4 — no regressions from the Coach model, migration 0005, media-gate branch or admin changes); phase-0 guard 12/12 after the changes | `manage.py test submissions parents`; `scripts/phase0_guard_tests.py` | **PASS (146 + 12/12)** |
| T70 | 2026-10-24 | Phase 4 site sweep: zero `class="socials"` blocks, zero `.socials` CSS rules, zero 3-track foot-grids left across the 37 pages + 29 stylesheets; zero published email addresses or `mailto:` links anywhere under `site/` (incl. `50x.html`, form success copy, sp-forms.js offline panels, site-config.js); contact/privacy/safeguarding/portal-guide/50x/form-08/form-09 copy re-routed to forms; the-squad.js + sp-forms.js pass `node --check`; the-squad.html tag balance parse OK | scripted sweep + `rg` verification + node/python parsers | **PASS** |
| T71 | 2026-10-26 | Phase 7 backend: `/api/results/` published-only, newest-first, server-derived W/D/L, full field shape (16 tests incl. honest-empty); `/api/players/<ref>/` public-fields-only with fail-closed 404 for unpublished/unknown refs; QR pages — staff-only bulk/single (anonymous redirected, guardians bounced), guardian own-child card + 404 on others' children, QR encodes `SITE_URL/player.html?ref=…`, segno SVG embedded, no inline handlers; qr.js asset allow-listed for signed-in users; dashboard/child-page QR buttons present | `manage.py test submissions.tests.test_phase7` (16 tests) | **PASS (16/16)** |
| T72 | 2026-10-26 | Phase 7 regression: full suite 162/162 (146 prior + 16 Phase 7 — no regressions from the Result model/migration 0006, portal_qr module, asset allow-list extension, player-card/child-page edits); phase-0 guard 12/12; all touched JS passes `node --check` (12 files) | `manage.py test submissions`; `scripts/phase0_guard_tests.py`; `node --check` | **PASS (162 + 12/12)** |
| T73 | 2026-10-26 | Phase 7 browser QA (43/43, live seeded backend + fresh site copy): results page renders 4 published results in 2 month groups with W/D/L badges + reports and never renders the unpublished one; API-down copy keeps the honest Coming Soon panel; nav Results item + footer link on every page; home fixtures board cross-links to results; player profile renders published player (name/squad/motto/squad deep-link) and fails closed for unpublished/unknown; `#team-<key>` deep link activates the right squad tab; staff dashboard shows QR buttons, single + bulk QR pages render segno SVG with SITE_URL target and draft flag; guardian prints own child's card and is 404-blocked from another child's; CSP `script-src 'self'` on portal; mobile nav carries the results link with zero inline onerror; zero console errors on every checked page | `scripts/p7_browser_qa.sh` (agent-browser, 1440×900 + 390×844) | **PASS (43/43)** |
| T74 | 2026-10-26 | Phase 7 visual QA: VLM review of 9 screenshots (results live + coming-soon, player profile + not-available, portal players view with QR buttons, staff single/bulk QR cards, guardian QR card, mobile nav) — no overlapping/clipped text, no broken images, no misaligned cards | `scripts/p7_vlm.sh` → `download/qa-p7/vlm/` | **PASS (9/9)** |
| T75 | 2026-10-26 | Rev 20 backend regression: `manage.py check` clean and full suite green BEFORE and AFTER the polish round (no backend file touched) | `manage.py test` | **PASS (162/162 twice)** |
| T76 | 2026-10-26 | Rev 20 static suite: tag balance (41 pages), every local href/src resolves, zero inline event handlers (CSP), canonical + 5 OG tags on all 39 public pages, descriptions unique & <160, 209 lazy attrs with 18 hero/LCP images eager, CSS brace balance everywhere, robots.txt directives, sitemap XML validity + exclusion set, enquiry-policy grep (no emails/phones/socials), join-us hub structure (6+4 cards, ten links, labels) | `scripts/p8_verify.py` | **ALL PASS** |
| T77 | 2026-10-26 | Rev 20 browser QA: all 41 pages loaded at 1440px and 390px — 0 console errors, 0 failed assets (one real pre-existing CSS-image 404 found and fixed: the-squad captains background), 0 horizontal overflow; stat-strip grids re-measured in-DOM (3 equal columns, labels inside viewport, 12px) on all 13 strip pages | `scripts/p8_browser_qa.sh` | **PASS (82/82 loads)** |
| T78 | 2026-10-26 | Rev 20 visual QA: VLM review of 19 screenshots (mobile 12 + desktop 6 + compression comparison sheet) — layouts OK; one real overlap (bl14m -b missing label rule) found, fixed and re-verified; logo compression pixel-identical; feminin photo's flagged blur verified present in the original action shot, not a compression artifact | `scripts/p8_qa_out/` → `download/qa-p8/` | **PASS (after 1 fix)** |
| T79 | 2026-10-27 | Rev 21 backend regression incl. the test-path portability fix (`test_phase7.py` resolves `site/` relative to the test file): venv rebuilt from pinned requirements, full suite green, phase-0 guard green | `manage.py test submissions` + `phase0_guard_tests.py` | **PASS (162/162 + 12/12)** |
| T80 | 2026-10-27 | Rev 21 static sweeps: 0 `marquee` in HTML / 0 `.mq-` in CSS / 0 `mqTrack` in JS; 16 `heroBg` photo heroes; 11 `hero-parallax.js` includes; 0 navy-3 footer rules (footer = navy-4 everywhere); wave selectors fixed (`.tide path.w1/.w2`) in 12 files; remaining `rgba(12,26,51)` uses verified as box-shadow tints / out-of-scope scrims, none in the recolored 14 files | grep sweeps | **PASS** |
| T81 | 2026-10-26 | Rev 21 browser QA (12 representative pages, 1440px + 390px): marquee 0, footer computed `rgb(26,50,96)`, hero waves sand/pearl + blue tints (black-wave bug gone), parallax tracks scroll at exactly 0.25×, 0 console errors; all 41 pages 200 | agent-browser | **PASS** |
| T82 | 2026-10-26 | Rev 21 visual QA: VLM review of hero-wave, footer, mobile-390, leadership and squad hero screenshots — no black curves, no ticker, readable navy footer, smooth hero transitions (one mid-animation capture investigated and re-shot clean) | VLM screenshots | **PASS** |
| T83 | 2026-10-27 | Rev 21 squad QR cards: new wiring test `test_squad_player_cards_carry_unique_qr` (vendor include self-hosted, `mQr`/`mQrLink` targets, `p.ref` live-mode plumbing, `SQUAD_CODE` demo-mode refs, MIT attribution, `eval`-free library, `DEMO_PROFILES` fallback); full suite re-run green | `manage.py test submissions` + static sweep | **PASS (163/163)** |
| T84 | 2026-11-03 | Rev 22 real register import: suite re-run green after the demo-ref→real-ref assertion update; gateway crawl 41/41 pages + 133/133 unique assets 200; 29/29 squad photos 200; 50 refs identical across the-squad.js / sp-player.js / player_seed.json; browser QA 1440px + 390px (5 tabs, U12 boot, 11 dots + 7 bench chips, modal photo/QR/chips, U19 5-dot honest layout, Féminin honest panel, player.html?ref=U12-02 renders with photo, 0 console errors); VLM QA 5 shots PASS | `manage.py test submissions` + crawl + agent-browser + VLM | **PASS (163/163 + all green)** |

---

## 9. Change log

- **2026-10-23 — Phase 0 (kit rev 12):** baseline git repo + `.gitignore`;
  this document; `.env.production.example`; deterministic admin password
  removed from `install.sh` (random one-time display or `SP_ADMIN_PASS`);
  demo parent credential de-hardcoded (fictional address + random password);
  `SP_ENV=production` fail-closed settings guard; installer `--production`
  verification flag. Evidence T1–T14.
- **2026-10-23 — Phase 1 (kit rev 13):** dedicated `SafeguardingReport`
  model + immutable `SafeguardingAuditEntry` (updates/deletes raise);
  form-10 routed out of the shared ledger (dashboard/CSV/admin blind to it);
  legacy ledger rows auto-migrated with audit (0004); DSO role via Django
  group (`sp_dso` grant/revoke/list) — staff, parents and even superusers
  without the role get a neutral 403, in the portal AND the Django admin;
  branded DSO desk `/portal/dso/` (queue, detail, status workflow, case
  notes, audit log) with per-view auditing; minimal DSO notification email
  (`DSO_EMAIL`, never the general inbox) + neutral reporter acknowledgment;
  "100% Whistleblower Protection" replaced with legally-careful wording
  (owner/legal sign-off pending); sp-forms.js checkbox-group serialization
  fixed (incident categories were being lost); `SAFEGUARDING-RUNBOOK.md`
  (workflow, escalation ladder, manual QA script, residual risks);
  test suite: 38 automated tests + 19-check live smoke + visual QA.
  Evidence T15–T27. **Gate items for the owner:** appoint the DSO
  (`manage.py sp_dso grant …`), set `DSO_EMAIL`, legal review of the
  public wording.
- **2026-10-23 — Phase 2 (kit rev 14):** auth & application hardening.
  Login throttling on the staff portal and Django admin (8 fails/15 min/IP,
  branded 429) — matching the parent portal; identical "wrong username or
  password" for unknown user / wrong password / non-staff credentials on
  both login forms; PBKDF2 timing equaliser so account existence cannot be
  probed by response time. Enumeration-free password reset for BOTH portals
  (`/portal/reset/`, `/portal/parents/reset/`): identical neutral pages for
  known/unknown accounts, one-use links expiring after 1 hour
  (`PASSWORD_RESET_TIMEOUT`), honeypot + 5/IP/hour request cap, neutral
  emails (link only), security-event logging (pk + ip, never
  credentials/tokens). Response hardening: CSP + Permissions-Policy + COOP
  middleware on every Django response, nosniff/Referrer-Policy/XFO via
  settings, env-driven HSTS, session cookies HttpOnly+SameSite=Lax with a
  12-hour age; nginx templates carry the same header set for the static
  site, add branded 404/50x pages and the missing `client_max_body_size`
  on the plain-:80 front. Proxy trust is now opt-in (`TRUST_PROXY_HEADER`).
  Player-photo uploads fully validated: Pillow double-pass decode
  (renamed/truncated files rejected), 40 Mpx bomb cap, EXIF/GPS stripped by
  re-encode, stored extension always matches the real format. Branded
  404/500 handlers for the Django app (no internals leaked). Cross-form
  aggregate rate cap on the public API. Residual risks R27 (CSP
  `unsafe-inline` until an inline-JS refactor) and R28 (per-IP counters in
  process-local cache) documented. Tests: 89 automated (51 new) + 25-check
  live smoke + 7-image visual QA, all passing. Evidence T28–T42.
- **2026-10-23 — Phase 3 (kit rev 15):** truthful, resilient public forms.
  sp-forms.js rewritten (v3): the success screen and reference number now
  appear only after the server acknowledges the submission — the fabricated
  client-side references (e.g. `SAFE-2026-<random>`) that could never be
  traced are gone from all 13 pages; offline and server-rejected states get
  an honest on-page panel (answers kept, 48-hour device copy explained,
  form-10 adds the Childline 116 urgency line, retry button); undelivered
  copies auto-retry on the next visit and then show the real reference;
  drafts autosave/restore with the same 48-hour expiry; queue capped at 5.
  Every success modal's copy rewritten to remove untrue claims ("Executive
  Committee", "email and SMS routed", "officially recorded in the registry",
  "Under Immediate Assessment", "Assessment Slot Booked"). Server-side
  validation parity: payload shape guards (empty/junk/oversize bodies and
  values rejected with honest 4xx), newsletter email check, empty-report
  guard for form-10; 4xx responses are never queued for retry. Data
  minimisation: new `policy-data-privacy.html` (Kenya DPA 2019) + a
  privacy mini-notice on every form; medical and ID values withheld from
  notification emails; the staff ledger answer sheet shows them only to
  Portal Administrators and superusers (R26). form-01's photo field now
  honestly states files are not attached online. Accessibility: success
  dialogs get role/aria + focus management; sync notes and panels are
  aria-live. Tests: 22 new unit tests (111 total), live smoke 17/17, all
  13 pages browser-verified (0 JS errors), VLM visual QA. Evidence
  T43–T51. **Gate-3 items:** accept new form behaviours; form-01 field
  minimisation decision; privacy-page wording review; photo-field decision.
- **2026-10-23 — Phase 3 gate-3 CLOSED (chat approval "continue"):**
  form behaviours accepted; form-01 minimised per the recommended
  default (Birth Certificate/UPI + National ID fields removed, medical
  section replaced by one optional conditions/allergies note + paper
  medical form with the coach, emergency authorisation kept — R13
  CLOSED); privacy-page wording accepted as-is; photo-field honest
  note kept. Implemented and verified before Phase 5 work began.
- **2026-10-23 — Phase 5 (kit rev 16): production engineering.**
  Dependencies pinned to the tested versions (Django 6.1.2, gunicorn
  26.2.0, whitenoise 6.12.0, requests 2.34.2, corsheaders 4.9.0,
  Pillow 13.0.0) with upgrade instructions. `/healthz/` (+ legacy `''`)
  liveness/database probe: 503 with no internals when the DB is down.
  Media auth-gating (R17): `/media/` served through `media_serve` —
  published players' photos public, everything else staff or the
  OWNING guardian only, uniform 404 for missing/forbidden/traversal,
  orphan files fail closed. CSP inline-JS refactor (R27 closed for
  scripts): 240 inline handlers across 37 pages → `data-fb` attributes
  + shared `img-fallback.js`; three inline-script pages externalised;
  portal dashboard script → `/portal/assets/dash.js` (allow-listed,
  per-asset ACL); Google Fonts and four CDN libraries self-hosted (the
  CDN references were latent CSP violations QA had missed, and
  splittype@0.3.4 has vanished from npm — the live script tag was
  silently 404ing — replaced with a minimal local shim that restores
  the hero word-reveal); `script-src 'self'` everywhere. Two real bugs
  found by the browser QA and fixed with regression tests: parent
  portal 500 for players without a shirt number, and Python-emitted
  inline `onerror=` handlers on player-card photos. Backups: new
  `restore-drill.sh` (R14) — executed against a real bundle, 10/10.
  Optional PostgreSQL (`DB_ENGINE=postgres` + `DB_*`) and shared
  throttle-counter cache (`SP_CACHE=db`, R28) — config-level switches,
  defaults unchanged, tested via subprocess settings import. CI
  workflow (`.github/workflows/ci.yml`) + portable phase-0 guard
  script inside the kit. EMAIL-SETUP-GUIDE deliverability section
  (SPF/DKIM/DMARC progression, verification, R15). Form-01
  minimisation applied per gate-3. Tests: 133 automated (22 new),
  guard 12/12, live smoke 42/42, browser QA, VLM 7/7. Evidence
  T52–T61. **Gate-5 items:** accept CSP/behaviour changes; accept the
  media-gating policy; confirm staying on SQLite (default) or moving
  to PostgreSQL; then Phase 6 (acceptance testing) remains, and
  Phase 4 (content) stays owner-input blocked.
- **2026-10-24 — Gate-5 CLOSED (chat approval "continue"):** (a)
  CSP/behaviour changes accepted (self-hosted scripts/fonts, no
  functional change observed during acceptance); (b) media-gating
  policy accepted (published photos public, everything else
  staff/owning-guardian); (c) form-01 minimisation accepted as applied
  at gate-3; (d) **SQLite stays the default** — the PostgreSQL switch
  (`DB_ENGINE=postgres` + `DB_*` + `SP_CACHE=db`) remains a documented
  config option for later, no migration now. Also closed out a
  documentation leftover from gate-1: `SAFEGUARDING-RUNBOOK.md` §9's
  closing paragraph still said the wording awaited owner review — now
  records the 2026-10-23 approval (and what to update together if
  counsel ever refines the wording).
- **2026-10-24 — Phase 6 (kit rev 17): acceptance testing from a fresh
  install.** The shipped v16 zip was unzipped into a scratch directory
  and installed exactly the way an owner would (`install.sh
  --demo-data` with `SP_ADMIN_PASS`); every subsequent check ran against
  that installed stack, not the development workspace. Automated:
  133/133 tests + phase-0 guard 12/12 from the installed tree. Live
  acceptance matrix (persisted as `scripts/p6_acceptance.sh` in the
  kit, 96/96): liveness + real `sp.sh` stop/start restart; minimised
  form-01 on the served site; CSP/nosniff/XFO; four public form
  submissions with real references; payload guards; the full form-10 →
  DSO desk journey including status change, case note and the complete
  audit trail, with staff/superuser 403s and dashboard blindness;
  demo-parent journey (child, announcements, complaints); medical
  redaction plain-staff vs portal-admin; enumeration-free resets with
  the full token link flow on both portals; the media-gate matrix;
  upload content-validation + EXIF strip; branded 404 on app and site;
  staff + admin login throttles; backup + restore drill. **One real
  defect found and fixed (T65):** with the shipped `--workers 3`, the
  login throttles were inert — per-process counters round-robined
  across workers and never reached 8 failures (R28 manifesting in the
  default install). Both service templates now ship `--workers 1
  --threads 8` (single process, gthread: shared counters, SQLite-safe,
  threaded concurrency); verified 429-on-9th-attempt on the installed
  instance and locked in with a regression check. Browser journeys
  (agent-browser): full 6-section form-01 registration showing the real
  server reference matching the DB row; parent/staff/DSO journeys; 0
  console errors. Visual QA 8/8 (one homepage FAIL was the hero
  word-reveal caught mid-animation — re-shot after settle, PASS).
  Remaining owner-side before go-live: academy-staff staging sign-off
  with the same fictional data, real credentials, domain locking,
  uptime monitor + operational owner, DSO appointment + `DSO_EMAIL`.
  Phase 4 (content) still owner-input blocked. Evidence T62–T67.
- **2026-10-24 — Phase 4 (kit rev 18): content & enquiry policy.** Owner
  content decisions received in chat: chairman's message and the
  published leadership names (Dr. Stephen Abuor, Mrs. Joyleen Mbwika)
  confirmed real — no edits. Coaching staff made admin-settable: new
  `Coach` model (Django admin, `CoachPhotoStorage` re-encodes every
  upload on every save path — EXIF/GPS stripped, extension matched to
  the real format, 40-Mpx bomb cap, invalid files fail closed),
  public read-only `/api/coaches/`, media gate extended to `coaches/`
  (published public, everything else staff-only). Enquiry policy
  implemented: all published email addresses removed from the public
  site (16 spots incl. `partnerships@` on partners.html), all social
  links/icons/copy removed from all 37 pages + 29 page stylesheets
  (footer grid rebalanced), offline-form mailto fallbacks and
  `CONTACT_EMAIL` removed; fees / programme specifics / partnership
  terms / contact details now stated as shared upon enquiry with
  routes into the forms. Squad-page truthfulness: hardcoded fictional
  captain cards replaced by dynamic rendering of published captains;
  the live-mode fictional-roster fallback removed (live sites show an
  honest "being finalised" panel when nothing is published or the
  backend was never reached; demo mode keeps its showcase data);
  "38 Clean Sheets" stat replaced with a structural fact; roster count
  now tracks the published total. Safeguarding retention policy set in
  writing (runbook §5 + privacy page §7): 24 months, open cases kept
  until closed then 24 months from closure. Email delivery
  owner-confirmed ("mails do get delivered") — R15 updated, DNS records
  still recommended. Tests: 146/146 (13 new Phase 4); phase-0 guard
  12/12. Evidence T68–T70.

- **2026-10-26 — Phase 7 (kit rev 19): Results page + per-child QR codes.**
  Owner feature round requested in chat: (1) "The results page should
  exist, currently links to the fixtures page… make it coming soon but
  needs to populate when [results are entered]" — new `Result` model
  (team/opponent/competition/date/venue/scores/optional report,
  publish flag, admin with date hierarchy), public `/api/results/`
  (published-only, newest first, server-derived W/D/L), and a dedicated
  public `results.html` built on the policy-page design system: honest
  Coming Soon panel until published results exist, then month-grouped
  match cards with W/D/L badges; the nav "Results" item (Teams dropdown)
  and every footer now link to it, and the home fixtures board gained a
  "Match results" cross-link. (2) "Every child needs a QR code that can
  point back at this website at their specific profile" — new public
  player profile page `player.html?ref=…` (public fields only — the
  same surface as the squad pages; unpublished/unknown refs fail closed
  to an honest not-available panel; `noindex` so individual children's
  profiles stay out of search engines), backed by `/api/players/<ref>/`;
  QR codes generated server-side with pinned `segno` (pure Python) as
  inline SVG on print-ready card pages: staff bulk `/portal/qr/`
  (grouped by squad, unpublished players flagged), staff single
  `/portal/qr/<ref>/` (QR button on every dashboard player card), and
  guardian own-child `/portal/parents/qr/<ref>/` (link on the child
  page); the QR encodes `SITE_URL/player.html?ref=…` (installer-written;
  a visible warning appears if it is unset). `#team-<key>` deep links
  now open the right squad tab. Bonus fix: latent CSP bug — inline
  `onerror=` in 9 JS nav templates (invisible to the Phase-5 HTML-only
  sweep) converted to `data-fb`, versions bumped. Tests: 162/162
  (16 new Phase 7); phase-0 guard 12/12; browser QA 43/43; visual QA
  9/9. Evidence T71–T74.
- **2026-10-26 — Site polish round (kit rev 20):** the full owner-brief
  improvement pass, executed without owner input and inside every
  standing constraint (no deploy/email/personal data; design, CSP,
  rate limits, DSO restrictions, media gating, audit logging, enquiry
  policy, form fields, policy wording all preserved — verified by
  grep/suite). SEO: robots.txt + sitemap.xml (23 public pages;
  forms/policies/portal-guide/player/error pages excluded),
  canonical + OG on all 39 public pages, 23 descriptions rewritten
  (<160, unique), favicon on 404/50x; `install.sh --domain` now
  re-points the placeholder origin across robots/sitemap/canonical/OG
  (idempotent http→https progression). Copy: hero label + pillar 06
  fixed, place naming standardised, counts audited (Seven/Eight/6
  verified; contact "8 Development Programmes" reported, not guessed).
  Numbering renumbered on 8 pages. Stat strips: mobile 3-col grids +
  12px labels (incl. the -b variant bug); contact stat 3 replaced
  with the factual "6 · Teams U9 → Féminin". Forms hub: ten forms in
  two labelled groups, Forms 08/09 added, "Five gateways" → "Ten
  gateways". Typography/contrast: zero sub-12px labels remain;
  grey-on-dark alphas lifted to AA (measured ratios in
  scripts/p8_contrast.py output; lowest text ratio now 5.08:1);
  policy-doc spacing increased. Images: logo 310→75 KB,
  feminin-hero 355→190 KB, sp-coach-address 361→188 KB (nlmeans +
  re-encode; originals in scripts/originals/); 150 below-the-fold
  images lazy-loaded, heroes/LCP eager. QA-found pre-existing bugs
  fixed: the-squad.css 404 on an unshipped designer-local image;
  bl14m-hero-600-b.css missing the label rule (chairman/about-us
  overlap at 390px). CSS cache versions bumped (40 links).
  Tests: 162/162 before AND after; static suite all-pass; browser QA
  41 pages × 1440/390px — 0 console errors / 0 failed assets / 0
  horizontal overflow; VLM visual QA of 19 screenshots PASS.
  Evidence T75–T78; full change record: CHANGELOG-REV20.md.
- **2026-10-27 — Owner UI round (kit rev 21):** with a support-us hero
  screenshot the owner asked for three things on the pages in that
  style family — remove the carousel, ensure no black, add a parallax
  effect. (1) The auto-scrolling marquee strip was removed from all 14
  pages that had it (12 sand variants, the-squad + leadership
  institutional bands, player-development amber tape), dead CSS/JS
  swept, and hero-to-section seams fixed so the wave blends into the
  following section. (2) A real bug present since the original build
  was found and fixed: the hero tide waves rendered pure black because
  the CSS selector `.tide .w1 path` never matched (`.w1` IS the path)
  so the SVG default black fill applied — fixed to `.tide path.w1/.w2`
  and verified via computed styles; near-black areas in the 14 style
  files were recolored to the brand navy family (stat-band stops,
  tints, hero fallbacks, gradients, theme-color metas, fig
  placeholders) and the footer was unified to navy-4 site-wide.
  (3) A new reduced-motion-safe, rAF-throttled `hero-parallax.js`
  (0.25×) was wired onto all 16 photo heroes. Cache versions bumped
  ?v22/?v23 across 39 pages. (4) Every squad player card (dossier
  modal) now carries the player's unique QR → public profile
  (`player.html?ref=…`): self-hosted `assets/js/vendor/qr.min.js`
  (qrcode-generator, MIT, eval-free, CSP-safe), live refs from the
  API / demo refs from the squad code, fail-closed hide on error,
  demo-profile fallback in `sp-player.js`; locked by the new test
  `test_squad_player_cards_carry_unique_qr`. Additionally
  `test_phase7.py` no longer hardcodes the build machine's absolute
  path (the shipped suite now runs on any install path). Out of scope
  by design and flagged: navy-2-based hero scrims on home/academy/
  join-us/coaching-philosophy, the .train-sec/.path-beyond-sec dark
  sections, the index media-tile placeholder. Tests: 163/163 +
  phase-0 guard 12/12 (venv rebuilt from pins); static sweeps all
  green; browser QA 12 pages — marquee 0, footer rgb(26,50,96),
  waves correct, parallax 0.25×, 0 console errors; VLM QA PASS.
  Evidence T79–T83; full change record: CHANGELOG-REV21.md.
