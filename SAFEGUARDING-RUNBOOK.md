# SAFEGUARDING RUNBOOK — Sporting Pearls Football Academy

| | |
|---|---|
| **Audience** | Designated Safeguarding Officer (DSO), Academy Administrator, Owner |
| **Status** | **Operational. Phase 1 output; retention policy set 2026-10-24.** §9 public wording and the escalation ladder framing were **owner-approved as-is on 2026-10-23** (chat approval, gate-1). §5 retention policy is now set in writing (owner decision, 2026-10-24): **24 months, open cases kept until closed then 24 months from closure**. §4.1 contacts (named DSO/deputy, Children's Office, police/OB procedure) remain owner TODOs to fill in before go-live. |
| **Covers** | Kit revision 13+ (the restricted safeguarding store) |

This runbook explains how safeguarding reports move through the academy:
who can see them, what the system does automatically, what the DSO must
do by hand, and how the whole flow is audited. It should be read
together with `policy-safeguarding-child-protection.html` on the website
(the external policy) and `PRODUCTION-READINESS.md` (the hardening
programme).

---

## 1. What changed in Phase 1 (and why)

Before Phase 1, a form-10 submission was stored in the same ledger as
every other form, emailed **in full** to the general academy inbox, and
visible to **any** staff account in the dashboard. For data that can
contain a child's name, an abuse narrative and a reporter's identity,
that was unacceptable (Kenya Data Protection Act 2019 — special-category
data; risks R1–R3 in `PRODUCTION-READINESS.md`).

Now:

- Reports live in a **dedicated, permission-gated store** (`SafeguardingReport`).
- Only the **DSO role** can open the desk at `/portal/dso/` — regular
  staff and even superusers without the role get a neutral 403. The staff
  dashboard cannot even reveal that a report exists (no row, no count,
  no nav link).
- The only email the academy receives is a **minimal notification** to
  the DSO's private inbox: "a report is waiting" + a link. No narrative,
  no child name, no reporter identity — ever.
- Every view, status change, assignment and case note is written to an
  **append-only audit log** that refuses edits at the application layer.
- The website's "100% Whistleblower Protection" claim was replaced with
  wording that reflects the law (see §9).

## 2. Roles and access

| Role | How it is granted | What it can do |
|---|---|---|
| **DSO** | `python manage.py sp_dso grant <username>` | Everything in `/portal/dso/`: read reports, change status, assign, write case notes, read the audit log |
| **Academy Staff** | is_staff account (default) | Normal portal work; **no** safeguarding access, not even visibility that reports exist |
| **Portal Administrator** | `Portal Administrators` group (Django admin) | User/account management; **no** safeguarding access unless separately granted the DSO role |
| **Parent/Guardian** | `Guardian` profile (parents app) | Own children, announcements, own welfare cases only |
| **Superuser** | Django admin account | **Not** exempt: without the DSO role the safeguarding admin pages and desk stay locked |

Appointment rules (recommended):

- One DSO (the Safeguarding Lead) plus at most one deputy.
- The role is personal, not positional: review membership after any
  staff change (`python manage.py sp_dso list`).
- Break-glass: if the sole DSO is unreachable, an administrator grants
  the role to a named deputy temporarily and records why in the audit
  log (a case note on the affected report). Remove the grant afterwards.

## 3. What happens automatically when a report arrives

1. The report is parsed and stored in the restricted store with a
   reference `SP-SAFE-YYYYMMDD-XXXX`.
2. An audit entry **received** is written.
3. If `DSO_EMAIL` is configured, the DSO gets the minimal notification
   email and an audit entry **notified** records the outcome. If it is
   not configured, **no email is sent at all** — the report waits in the
   desk. (Deliberately, nothing is ever sent to the general inbox.)
4. If the reporter chose the confidential option and left an email, they
   receive a neutral acknowledgment with the reference and the emergency
   numbers. Anonymous reporters get nothing (by design).

**If the reporter's internet drops before the report reaches the server
(Phase 3):** the website keeps a copy in the reporter's own browser and
retries automatically the next time they visit the site — the on-screen
confirmation ("Safeguarding Report Received" + the `SP-SAFE-` reference)
appears only once the report has actually reached the server. If they
were offline, they saw an honest "Not sent yet" panel instead, warning
that the copy sits on that device for up to 48 hours and giving the
Childline 116 number for emergencies. Two consequences for the DSO:
reports can arrive minutes to hours after the incident was written up
(check the incident date/time fields, not just the arrival time), and an
anonymous reporter's only record of their reference number is the screen
they saw (or the delivery note shown when the copy finally went through).

## 4. DSO workflow — from receipt to closure

**Step 0 — emergency first.** If the report suggests a child is in
immediate danger: call the Police (999 / 112) or Childline Kenya (116)
*before* anything else. Then record the call in the report's audit trail
(case note) and set the status to **Escalated — external authority**.

**Step 1 — acknowledge (same working day).** Open the report in the DSO
desk (this writes a **viewed** audit entry) and read it fully. If the
reporter is reachable and the matter is not anonymous, note that it is
being handled. Assign the report to yourself.

**Step 2 — initial assessment (within 24 hours).** Decide, and record as
a case note:
- Is the child safe right now? (If not → Step 0 rules apply.)
- Internal matter (coaching conduct, academy environment) or statutory
  matter (criminal, or a child in need of care/protection)?
- Who needs to be involved — nobody beyond the DSO unless they *need to
  know*. Do not paste report content into chats, group emails or
  announcements.

**Step 3 — act.** Use the status buttons, which exist to make the state
of every report obvious at a glance:
- **Received** — untouched.
- **Under review** — assessment in progress.
- **Escalated — external authority** — handed to the Children's Officer
  (Sub-County Children's Office), the Police/DCI, or medical services.
  Record the authority, the officer and any OB/case number in a case
  note (the form already captures what the reporter knew).
- **Actioned** — internal steps completed (e.g. suspension pending
  investigation, supervision plan, environment fixed).
- **Closed** — outcome recorded in a final case note.

**Step 4 — record.** Every action lives in the audit trail. Case notes
should be factual and dated: what you did, whom you called, what was
decided and why. Notes are append-only — corrections are added as new
notes, never by rewriting.

**Escalation ladder (owner to confirm contacts in §4.1):**
academy DSO → Sub-County Children's Officer → Police/DCI (OB record) →
medical services; in parallel, the owner/chairman where academy-level
decisions (e.g. suspending a staff member) are needed.

### 4.1 Owner TODO — confirm before go-live
- [ ] Name and phone of the current Safeguarding Lead (DSO) and deputy.
- [ ] Sub-County Children's Office contact (Kilifi County).
- [ ] Confirm the police station / OB procedure for your area.
- [ ] Set `DSO_EMAIL` in `backend/.env` to the DSO's private inbox.
- [x] Legal review of §9 wording (and the website copy) — **owner-approved
  as-is, 2026-10-23** (gate-1 chat approval). No changes requested to the
  wording or to the website copy.

## 5. Data handling rules

- **Never** forward, screenshot, print or copy report content out of the
  DSO desk. The narrative stays in the restricted store.
- Access is logged. Review the audit log weekly
  (`/portal/dso/audit/`): every **viewed** entry should have a case
  behind it.
- **Retention (owner policy, set 2026-10-24).** Safeguarding records
  are kept for **24 months**. A record whose case is **still open** when
  that period ends is kept until the case is closed, and then for a
  further **24 months from closure**. Deletion is a deliberate,
  owner-authorised act performed with the DSO — the application never
  deletes on its own. Audit entries are retained alongside the report
  they belong to, so the case history stays complete as long as the
  record does. (Owner wording: "safeguarding records are kept for 24
  months unless the case is still open" — the closure-anchored reading
  above is the protective default; confirm with counsel if a different
  anchor was intended.)
- Note (Phase 4, 2026-10-24): the public website no longer advertises
  the academy's email address (enquiries are routed through the site's
  forms). Email intake continues to work for anyone who already has the
  address — handle such mail exactly as before.
- Backups contain the safeguarding store: treat backup files with the
  same care (already excluded from the web root; see
  `PRODUCTION-READINESS.md` §5 backup notes).

## 6. Operating the desk (quick reference)

| Task | How |
|---|---|
| Open the desk | `/portal/dso/` (nav link "Safeguarding desk" appears only for the DSO) |
| Grant / check / remove the role | `python manage.py sp_dso grant|list|revoke <username>` |
| Notification inbox | `DSO_EMAIL` in `backend/.env`; empty = no notifications |
| Audit log | `/portal/dso/audit/`, filterable by action |
| Legacy data | Migration 0004 moved old ledger rows into the store automatically (audited as **migrated**) |

## 7. Manual verification script (dummy data)

Run after every install/upgrade; uses fictional data only.

1. `python manage.py sp_dso list` — confirm who holds the role.
2. Sign in to the website, open form 10, submit a **fictional** report
   (child "Test Child", narrative "QA test — please ignore").
3. As **staff (non-DSO)**: dashboard shows no trace (no new row, count
   unchanged, no "Safeguarding desk" nav item; `/portal/dso/` shows the
   neutral "Not authorised" page).
4. As **DSO**: nav item visible; the queue lists the report; open it
   (audit shows *received*, *notified*, *viewed*); change status; add a
   case note; check `/portal/dso/audit/` shows every step.
5. Check the DSO inbox: notification contains **only** the reference and
   the portal link — no narrative, no child name.
6. Delete the test report only via a deliberate admin action by the
   owner (it cannot be deleted from the desk UI), or keep it flagged as
   a QA row.

## 8. What is deliberately NOT built (residual risks)

- **Encryption at rest** is not implemented (SQLite file). The store is
  permission-gated at the application layer; anyone with OS/file access
  to the server can read the database file. Physical/host security and
  the backup handling in §5 carry this risk until Phase 5.
- The **staff portal's other sections** (submissions ledger incl. form-01
  medical data) are still accessible to any staff account — that is
  Phase 3 (data minimisation) work; this phase isolated only the
  safeguarding stream.
- Audit immutability is enforced at the application layer only.
- The reporter's browser may keep an offline copy of a submission in
  `localStorage` when the server is unreachable (Phase 3 addresses the
  messaging around this).

## 9. Public wording — what the website now promises

Replaced the "100% Whistleblower Protection" claim with:

> **Confidential Reporting** — You may submit this report completely
> anonymously. If you choose to give your details, they are visible only
> to the academy's Designated Safeguarding Officer (DSO), on a strict
> need-to-know basis. Please understand: where a child is at risk, the
> DSO may be required by law to share relevant information with
> statutory authorities (such as the Children's Officer or the Police).
> Reports made in good faith are handled seriously and discreetly, and
> retaliation against anyone raising a genuine concern is a
> disciplinary offence at the academy.

This wording is deliberately careful: it promises only what the system
and Kenyan law support. **Owner-approved as-is on 2026-10-23 (gate-1
chat approval)** — no changes were requested to this wording or to the
website copy, and the corresponding Phase 1 gate item in
`PRODUCTION-READINESS.md` is closed. If counsel later refines the
wording, update this section, the website copy and the privacy notice
together, and note the change in the readiness change log.
