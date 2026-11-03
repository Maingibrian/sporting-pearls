# Sporting Pearls — Form Backend (Django wiring, v2)

The site's **13 forms** all submit to the Django backend that ships in this
kit (`../backend`): every entry is stored in the database and the academy
office is emailed automatically (once a `RESEND_API_KEY` is configured).

## How it works

```
Form (any of the 13) → sp-forms.js watches the page's own success UI
  → serializes the answers keyed by each field's visible label
  → POST {API_BASE}/api/forms/<slug>/
      → validates + rate-limits (8 submissions/min/IP/form)
      → stores the entry (SQLite; visible in the staff portal + admin)
      → emails info@sportingpearlsacademy.org via Resend with every field
      → sends a branded auto-reply to the visitor
  → the visitor sees a discreet "Saved on our server — reference SP-…"
    note on the success screen (the page's local reference stays too)
```

`API_BASE` is set in `assets/js/shared/site-config.js`. The kit installer
(`install.sh`) patches it automatically; for a manual/split deploy, point
it at your backend origin, e.g. `https://api.sportingpearlsacademy.org`.

Spam protection (reCAPTCHA skipped per instruction): a hidden honeypot
field ("company") + per-IP rate limiting run inside the Django view.

## The 13 wired forms

| Page | Form id | Slug |
|---|---|---|
| contact.html | generalEnquiry | contact-general-enquiry |
| form-01-player-registration.html | playerRegForm | form-01-player-registration |
| form-02-trial-application.html | trialForm | form-02-trial-application |
| form-03-parent-association.html | parentForm | form-03-parent-association |
| form-04-volunteer-application.html | volunteerForm | form-04-volunteer-application |
| form-05-coach-technical-staff.html | coachForm | form-05-coach-technical-staff |
| form-06-sponsorship-partnership.html | sponsorForm | form-06-sponsorship-partnership |
| form-07-donation-support.html | donationForm | form-07-donation-support |
| form-08-contact-form.html | contactForm | form-08-contact-form |
| form-09-media-photo-consent.html | consentForm | form-09-media-photo-consent |
| form-10-safeguarding-report.html | safeForm | form-10-safeguarding-report |
| partners.html | partnerForm | partnership-application |
| index.html | newsletterForm | newsletter-subscription |

## Offline safety

If the backend cannot be reached when a form is completed, the submission
is queued in the visitor's localStorage (up to 20 per form) and retried on
their next visit to any page. The visitor sees a "copy kept on this
device" note with a mailto fallback — nothing is silently lost.

## Email delivery

Outbound email uses Resend and requires a verified domain. Add
`RESEND_API_KEY=…` to `backend/.env` and restart. Without a key,
submissions are still stored and visible in the staff portal — email is
simply skipped.

## History

- **v1 (Netlify):** forms posted to `/.netlify/functions/submit`. That
  layer was replaced by the Django backend; the old
  `form-submit.js` hook has been removed from the kit.
- **v2 (Django, current):** `sp-forms.js` syncs all 13 forms to
  `/api/forms/<slug>/`. Form 07 (donation), Form 08 (contact) and
  Form 09 (media consent) were added to the sync layer in this revision,
  and the serializer was rewritten to collect answers by field label
  (the pages' inputs carry ids, not name attributes).
