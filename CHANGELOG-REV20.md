# CHANGELOG — Kit Revision 20 (site polish round)

| | |
|---|---|
| **Revision** | 20 (supersedes 19) |
| **Date** | 2026-10-26 |
| **Scope** | Every improvement executable now, without owner input, real photos, rosters, DNS, a server or legal sign-off. No deployment, no email, no personal data, no safeguarding/DSO logic changes, no build step, no design redesign. |
| **Test results** | `manage.py check` clean; `manage.py test` **162/162 PASS** (before AND after the changes). Static suite `scripts/p8_verify.py`: **all pass**. Browser QA `scripts/p8_browser_qa.sh`: **41 pages × 2 widths (1440px, 390px) — 0 console errors, 0 failed assets, 0 horizontal overflow**. Enquiry-policy grep: no email address, phone number or social link on any public page. |

Working scripts (kept in `scripts/` for audit/re-run): `p8_audit.py`,
`p8_contrast.py`, `p8_site_edits.py`, `p8_css_edits.py`, `p8_renumber.py`,
`p8_images.py`, `p8_verify.py`, `p8_browser_qa.sh`; rollback copies of the
three compressed images in `scripts/originals/` (+ `comparison.jpg`
before/after sheet).

---

## 1. SEO and sharing basics — DONE

- **`site/robots.txt`** (new): allows all public pages; disallows
  `/portal/`, `/admin/`, `/api/`, `/media/`; points at the sitemap.
- **`site/sitemap.xml`** (new): 23 public content pages only. Excluded by
  design: the 10 form pages (transactional), the 4 `policy-*` pages
  (reference documents, not landing pages), `portal-guide.html` (see §9),
  `player.html` (per-player QR profile, already `noindex`), `404.html`,
  `50x.html`. Domain placeholder `https://www.sportingpearlsacademy.org`
  is centralised: one find-and-replace in this file re-points it, and
  **`install.sh` now re-points robots.txt + sitemap.xml + every canonical
  and `og:url`/`og:image` tag automatically when run with `--domain` /
  `--public-url`** (idempotent; handles the http→TLS progression).
- **Canonical + Open Graph** added to all 39 public pages: `og:title`
  (from the page `<title>`), `og:description`, `og:image`
  (`…/sp-pitch-aerial.jpg`), `og:type` (`website`; `profile` on
  player.html), `og:url`, `<link rel="canonical">`. `player.html` keeps
  its existing `noindex`. 404/50x deliberately carry none (error
  documents).
- **Descriptions**: 23 pages were over 160 characters — rewritten (all
  now unique, 114–158 chars). Pages already compliant were kept.
- **Viewport / favicon / lang**: every page already had `lang="en"` and
  the viewport meta (verified, no changes needed). `404.html` and
  `50x.html` were missing the favicon — added (`logo.png`).

## 2. Copy consistency — DONE (one item reported, not guessed)

- **index.html hero label**: the label duplicated the H1 word-for-word
  ("Developing Talent. Building Character. Transforming Lives Through
  Football.") — replaced with **"Mtwapa · Kilifi County · Since 2020"**.
- **Final pillar (PILLAR 06)** on the homepage retitled from
  "Building The Future Together" (identical to its section heading) to
  **"A Community United"** — matches the card copy (families, sponsors,
  coastal communities).
- **Place naming**: the first *visible body* mention of "Kilifi County"
  now reads "Mtwapa, Kilifi County" on: about-us (hero card), academy,
  boys-programme (caption), form-07 (pledge description),
  leadership-governance (hero card), our-story (hero sub),
  partner-with-us (section heading), safeguarding (hero contact line).
  Later mentions stay "Kilifi County". Head metadata, the shared
  nav/footer chrome and physical-address/venue content were not touched.
  *Not changed on purpose:* join-us (its only body county mention is the
  training-venues sentence — address content, protected) and
  education-life-skills (first mention is the quote attribution
  "Kilifi County Community Programme", which reads as a programme name).
- **Commitment counts — audit results**:
  - about-us "One institution. **Seven commitments.**" — the section
    shows exactly 7 cards (Football, Education, Character, Leadership,
    Coach Development, Girls' Football, Community). **Correct, kept.**
  - academy "**Eight commitments.** One culture." — the val-grid shows
    exactly 8 cards. **Correct, kept.**
  - vision-mission hero stat "**6 Commitments**" — its commitments
    section shows exactly 6 cards (Play, Learn, Develop, Lead, Belong,
    Transform). **Correct, kept.**
  - contact hero stat "**8 Development Programmes**" — **MISMATCH,
    REPORTED INSTEAD OF GUESSED.** No list anywhere on the site shows 8
    programmes: the homepage programmes grid shows **6** and the academy
    page's programme rail shows **7**. Because the "same section" (the
    contact hero) lists nothing to count, and the two candidate sources
    disagree, the number was left as-is for the owner to settle (see
    Owner decisions).
  - Also observed while auditing (out of scope, untouched):
    partners.html hero says "**4 Active Squads**" while index/join-us/
    the-squad all say **6** teams/squad tiers — flagged for the owner.

## 3. Section numbering — DONE

Renumbered so each page's numbered eyebrows start at 01 and stay
continuous (visible `NN ·` eyebrows only; the internal `<!-- NN -->`
comments are an all-sections index that also numbers the hero and
un-eyebrowed sections, so they were deliberately left alone):

| Page | Before | After |
|---|---|---|
| about-us.html | 02,04,05,06,07,08,09,10,11 | 01–09 |
| partners.html | 02–16 | 01–15 |
| safeguarding.html | 02–08 | 01–07 |
| leadership-governance.html | 02–06 | 01–05 |
| chairman-message.html | 03,04 | 01,02 |
| boys-programme.html | 01–04,**06**–08 | 01–07 (gap closed) |
| education-life-skills.html | 01–03,**05**,06 | 01–05 (gap closed) |
| coaching-philosophy.html | 01–07,**09** | 01–08 (gap closed) |

Checked and already correct: contact (01–04), policy-data-privacy
("Section 01–10" — starts at 01, continuous; a prose cross-reference
"see Section 3" was left untouched because privacy wording is frozen),
portal-guide (01–10), join-us (01–03). vision-mission keeps two parallel
series by design (main 01–05 + the three theme statements 01–03).
coaching-philosophy's 01–03 "In/Out of Possession/Transition" items are
tab buttons for the three phases of play, not section eyebrows — left
as designed.

## 4. Stat strips — DONE

- **Root cause**: at ≤600px the shared `bl14m-hero-600*.css` shrank the
  hero-stat labels to 0.66rem and kept the row as a wrapping flex —
  the third stat wrapped alone. Fixed by switching the mobile row to a
  **3-column grid with `min-width:0`** (and 12px labels, tighter
  tracking) in `bl14m-hero-600.css` (6 pages),
  `bl14m-hero-600-b.css` (2 pages — this variant also lacked the label
  rule entirely, which made "INSTITUTIONAL HORIZON" overlap its
  neighbour on chairman-message; found in visual QA, fixed),
  plus appended mobile grid blocks in `leadership-governance.css` and
  `player-development.css`, and in the inline styles of
  core-values/our-story/vision-mission (which had the same flex-wrap
  pattern). join-us/academy/coaching-philosophy already use 2×2 grids —
  verified aligned at 390px. Same content everywhere; measured after the
  fix: all 13 stat-strip pages render 3 equal columns, every label
  inside the 390px viewport.
- **contact.html "2020 · Serving the Community"** — **replaced** with
  "**6 · Teams U9 → Féminin**", a factual stat already published on the
  homepage impact strip (and on join-us/the-squad). Chosen over removal
  because the strip otherwise loses its third point, and over
  "44+ Registered Players" to avoid coupling the contact page to the
  roster-count claim.

## 5. Forms hub — DONE

join-us.html now shows **all ten forms in two labelled groups**:
- "**Main Pathways · Forms 01–06**" — the six gateway cards (Form 06
  Sponsorship & Partnership added as a sixth card linking directly to
  `form-06-sponsorship-partnership.html`).
- "**Other Forms · 07–10**" — the compact strip, now four cards:
  Form 07 Donation & Support (re-pointed from support-us.html to the
  form page itself), **Form 08 Contact & General Enquiry (added)**,
  **Form 09 Media & Photo Consent (added)**, Form 10 Safeguarding
  Report (unchanged).
- Heading fixed: "**Five gateways.** One family." → "**Ten gateways.**
  One family." (10 forms shown). Hero stat corrected 5 → **6
  Onboarding Pathways** (the six that actually onboard; 07–10 are
  other forms). All links verified working; partners.html and
  support-us.html remain linked from the main navigation.

## 6. Contact page response time — DONE (no number invented)

The kit already states an expectation: the auto-reply email sent for
every general submission says "A member of the academy office reads
every message and replies **within a few working days**" (partners.html
similarly promises five working days for partnership enquiries). The
contact page's enquiry intro now carries the same sentence, plus an
`<!-- OWNER: confirm response time -->` comment so the owner can firm it
up to a specific number. No new commitment was invented.

## 7. Typography and contrast — DONE (ratios recorded)

- **Tiny labels**: every uppercase monospace label under 12px was raised
  to **0.75rem (12px)** — 24 stylesheet files plus the inline styles of
  core-values/our-story/vision-mission, where the whole label scale sat
  at 0.52–0.72rem (8–11.5px). This includes the mobile hero-stat labels
  (were 0.66rem/0.56rem), results-page chips, policy/portal-guide
  document labels, player-page fact labels, the-squad pills, academy
  hero-meta, institutional-blueprint folio, leadership-governance bio
  labels and about-us captions. Post-fix sweep: **0 sub-12px
  declarations remain in any CSS file or inline style**.
- **Grey-on-dark contrast** (measured with `scripts/p8_contrast.py`,
  WCAG relative-luminance formula, against the declared solid
  backgrounds; full ratio table in the script output):
  - Standard body/muted text on dark (`--muted-d` = pearl .66) —
    **7.77:1 on #0c1a33 / 7.15:1 on #102141: PASS**, unchanged.
  - hero-stat labels .55 — **5.77:1 PASS**; join-us hstat .68 —
    **6.90:1 PASS**; charter-band paragraph .68 — **8.17:1 PASS** —
    kept.
  - **Fixed** (were below 4.5:1): `.card-meta` .45 → .68 (was 4.29:1);
    `.cb-meta span` .50 → .68 (charter band sits on the hero gradient,
    worst-case solid #1a3260); `.hs-txt` .50 → .68; `.cent-flow i` /
    `.path-flow i` arrows .40 → .62 (were 3.66:1); `.hero-side` /
    `.pitch-side` .45 → .62; `.vis .v-n` .40 → .62; contact enquiry
    placeholders .40 → .55. Post-fix lowest text ratio on dark:
    **5.08:1** (on the lightest navy #1a3260) — AA pass with margin.
  - Amber #f59d1e on navy (stat numbers) 8.03:1 PASS; light-background
    pairs (body #2f3b4d on pearl 10.85:1, muted 8.63:1, ink on sand
    15.07:1) PASS. The amber-2 kicker colour on light backgrounds
    measures 2.88:1 — it is a decorative brand accent above 14px bold
    headings, out of the task's "grey body text on dark" scope and part
    of the site's established design; left unchanged and noted.
- **policy-data-privacy.html**: paragraph spacing 1.1rem → 1.5rem,
  section padding clamp(1.75–2.5rem) → clamp(2.25–3.25rem), section
  headings 1.6–2.25rem → 1.8–2.5rem, subheadings 1.15rem → 1.3rem.
  Wording untouched. (policy.css is shared by all four policy pages —
  applied uniformly so the document family stays consistent.)

## 8. Images — DONE

- Compressed under 200 KB, same dimensions, same filenames; rollback
  originals in `scripts/originals/`:
  - `logo.png` 310 KB → **75 KB** (adaptive 256-colour palette;
    VLM-verified pixel-identical rendering of the crest).
  - `feminin-hero.jpg` 355 KB → **190 KB** (ffmpeg nlmeans denoise
    s=10 + JPEG re-encode; these photos carry heavy baked-in grain
    that made a plain re-encode plateau at ~300 KB).
  - `sp-coach-address.jpg` 361 KB → **188 KB** (nlmeans s=16 + q≈80).
    VLM review: logo identical; sp-coach accepted for use; feminin's
    only flagged defect (motion blur on the kicking player) was
    verified present in the ORIGINAL photograph — an action-shot
    characteristic, not a compression artifact — and the image renders
    behind the hero scrim + grain overlay.
- **Lazy-loading**: `loading="lazy"` added to **150 below-the-fold
  images** (content figures, footer/ghost images and the 117 nav
  mega-menu preview thumbs, which are hidden until hover). Kept eager:
  every hero/LCP image, the preloader crest and the nav brand mark
  (verified per page). `player.html`/`the-squad.html` JS-injected photos
  were already lazy by page position.

## 9. Duplicate pages — RECOMMENDATION (owner decision; nothing deleted)

- **partners.html vs partner-with-us.html**: ~80% content overlap
  (multiplier effect, investment areas, partnership levels,
  accountability, 100-year question, CTA to Form 06). partners.html is
  the canonical page: it embeds the partnership application form and is
  the "Partner With Us" nav target on 36 of 39 pages. partner-with-us
  is linked only from the three newer pages (core-values, our-story,
  vision-mission), whose nav/CTAs point at the variant — evidence of
  drift. **Recommendation: redirect** — at go-live, 301 partner-with-us
  → partners.html and repoint those three pages' links (a 10-minute
  change). Not done now: the owner has not confirmed retiring either
  page, so **no `noindex` was added and both files are untouched**.
- **portal-guide.html**: it is not linked from anywhere in the public
  navigation (only from the kit's README) — so **added to the sitemap
  exclusions**, matching the existing navigation pattern (the footer
  does not link portal content). The file itself is untouched and
  remains reachable by URL (it is the user guide the README hands to
  staff/parents).

## Bugs found and fixed along the way (pre-existing, caught by this QA)

1. `the-squad.css` referenced `../../Pearls/radoms/IMG_7082.jpg` — a
   designer-local folder never shipped in the kit — so the captains
   section background 404'd on every load. Re-pointed to the bundled
   `sp-team-huddle.jpg` (hidden under the 92–95% navy gradient, as
   designed).
2. chairman-message/about-us load the `bl14m-hero-600-b` mobile variant,
   which never contained the hero-stat label rule — at 390px the
   14px labels overflowed their grid cells and overlapped the next
   column. Fixed (rule added to the variant; found by VLM visual QA,
   confirmed by DOM measurement, re-verified clean).

## Not done (owner or external actions, by instruction)

- Player photos / rosters publication; `API_BASE`, `DSO_EMAIL`,
  `SP_ENV`, domain + hosts; privacy/safeguarding/retention wording
  (one place-naming edit inside the safeguarding policy was made and
  **reverted** when spotted); no page deletions; no form field or
  validation changes; no newsletter backend/analytics/cookies/third-
  party scripts; fixtures "Coming Soon" untouched; no new build step
  (robots.txt/sitemap.xml are plain static files).

## Owner decisions still needed

1. **"8 Development Programmes"** on contact.html — settle the real
   count (homepage grid says 6, academy rail says 7) and we adjust the
   stat (or re-point it to a list that shows the number).
2. **partners.html vs partner-with-us.html** — confirm the redirect
   recommendation (or keep both); noindex only after confirmation.
3. **partners.html "4 Active Squads"** vs 6 teams everywhere else —
   which is correct?
4. **Response time** — confirm/replace "within a few working days" on
   contact.html with a firm commitment if desired (OWNER comment is in
   the file).
5. **education-life-skills quote attribution** ("Kilifi County
   Community Programme") — tell us if it should read as a location or
   a programme name.
6. Standing Phase 4/5 items unchanged: player photos + technical team
   via admin, DSO appointment + `DSO_EMAIL`, then domain/TLS/monitoring
   per the go-live checklist.
