# CHANGELOG — Revision 24 (gallery restoration + real-photo heroes)

| | |
|---|---|
| **Revision** | 24 (site-only) |
| **Date** | 2026-11-03 |
| **Scope** | Restores the gallery round lost when a later rebuild regenerated pages from a pre-gallery baseline: the About "Life at the Academy" collage now carries the academy's real training photographs, the Féminin page regains its "On the Pitch" gallery, the homepage moment wall gets Sunday's captions, all three galleries open in the new photo lightbox, the "Rolling Pearl" page transition is wired site-wide, and every photo hero on the site now uses real academy photography instead of stock imagery. |
| **Test results** | Static reference check: 0 missing assets. Browser QA (Playwright): 17 hero pages PASS for text contrast (3 scrims strengthened after first-run FAILs); About collage, Féminin gallery and moment wall PASS on desktop + mobile; lightbox opens, arrow-key navigates (1 / 4 → 2 / 4) and Esc closes; page-veil navigation smoke test lands on target page with 0 console errors, 0 page errors. |

---

## 1. What happened (root cause)

The gallery round (Nov 1) updated the site inside the preview tree, but a
subsequent rebuild regenerated the page templates from a pre-gallery
baseline and the kit (and the first GitHub push) shipped without it. The
photo assets and the lightbox script survived on disk; only the markup
wiring was lost. This revision re-applies that wiring and extends it.

## 2. "Life at the Academy" collage — real photographs (about-us.html)

The 10-tile collage section keeps its design (navy band, ring motif,
`Real sessions. Real faces.` heading) but every tile now carries a
photograph from the academy's own training highlights (Mtwapa, Kilifi
County) in place of stock imagery: the gathered squad under the trees,
the tactics-board school, the cones on the dirt pitch, the briefing
semicircle, the growing crowd, the flipchart debrief, the review circle,
the neighbourhood grounds. Tiles are grouped under `data-lightbox`.

## 3. New shared photo lightbox (assets/js/shared/sp-lightbox.js)

Click any collage / gallery / moment-wall photo: it flies open
centre-screen (FLIP animation) while the page behind is dimmed and
blurred. Browse with the on-screen arrows or ←/→, close with ×, Esc or
the backdrop. A `n / total` counter and the tile's kicker + caption
render beneath the photo. CSP-safe (no injected styles, no eval),
honours `prefers-reduced-motion`, restores focus and scroll on close.

## 4. Féminin — "On the Pitch" gallery (feminin.html)

New section before the promise CTA: `The Butterflies, in motion.` over
a cream band, with five staggered tiles from the girls' and women's game
(on the ball / pass & move / the briefing / practice days / the
pathway). All five browse in the lightbox.

## 5. Homepage moment wall (index.html)

Sunday's captions are restored: `One family — the whole academy, one
address.`, `School of the game — tactics first, boots second.`, `One
squad, one message — the talk before the work.`, `The debrief — every
session ends with lessons.` The wall joins the lightbox group (1 / 4).

## 6. Real-photo heroes (17 pages)

Every hero banner with photography now uses the academy's own pictures
(briefings, line-ups, gatherings, the training ground) instead of stock
images: index, the-squad, about-us, chairman-message, contact,
core-values, education-life-skills, partners, partner-with-us,
boys-programme, goalkeeper-development, our-story, support-us,
leadership-governance, vision-mission, player-development and
safeguarding (deliberately a silhouette — no identifiable faces on a
welfare page). Féminin keeps its girls'-football hero; the real batch
contains no girls' photos. `og:image` tags follow the new heroes.
Hero scrims on index, the-squad, support-us and contact were
strengthened (plus a mobile-specific index scrim) so all hero text
stays readable over the busier real photographs.

## 7. "Rolling Pearl" page transition (assets/js/shared/page-veil.js)

Wired on all 39 content pages (after img-fallback.js): the clicked
ball blooms into a navy circle, the crest rolls to centre, the new page
opens under full navy and the ball rolls back to the click point.
Skips modified clicks, hashes, downloads and file links; disabled under
`prefers-reduced-motion`; fails safe if navigation stalls.

## 8. Files added

- `site/assets/img/hero/` — 17 optimized hero photographs
- `site/assets/img/feminin/` — 5 Féminin gallery photographs
- `site/assets/img/rs-02/04/07/08/10.jpg` — collage photographs
- `site/assets/js/shared/sp-lightbox.js`, `site/assets/js/shared/page-veil.js`

## 9. Upgrade notes

Pure static-site change — replace `site/`, no backend, database or
config impact. CSS cache-busts: about-us v24, index v26, feminin v24,
the-squad v25, support-us v24, contact v24.
