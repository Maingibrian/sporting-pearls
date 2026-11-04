# Rev 28 — Squad selector carousel + Technical-team management (2026-11-05)

Two office requests landed together: the squad selector on the website
needed to be usable on phones (it side-scrolled with no visible way
forward), and the coaching team needed portal editing so profiles can be
published the moment contracts are confirmed.

## Website — squad selector that explains itself (`site/`)

- `the-squad.html`
  - The squad tabs are wrapped in a `.tabstrip` with big prev/next arrow
    buttons (`#tabPrev` / `#tabNext`), hidden on desktop (≥980px).
  - Script/cache bumps: `the-squad.js?v28`, `the-squad.css?v26`.
- `assets/css/pages/the-squad.css`
  - Arrows: navy circles with amber chevrons, flush to the strip edges,
    disabled state at either end.
  - Edge fades (`.can-left` / `.can-right`) hint that more squads wait
    on that side.
  - The strip now snap-scrolls (`x mandatory`, `scroll-snap-align:start`,
    `scroll-padding-inline`) — card-aligned like a carousel.
  - **Root cause fix:** on phones each squad card ran ~540px wide (the
    meta line never wrapped and the grid's middle column couldn't
    shrink), making the strip a ~2700px hidden side-scroll. Cards are
    now `min(78vw, 340px)` with `minmax(0,1fr)` so names/metas wrap
    inside the card.
  - Desktop is untouched: sticky vertical list, no arrows, no snapping.
- `assets/js/pages/the-squad.js` (v28)
  - Strip controller: arrows step to the adjacent squad, edge fades and
    disabled states repaint on scroll/resize (rAF-throttled).
  - `renderTeam` now centres… aligns the chosen squad into view
    (`inline:'start'`), so switching squads by tab, arrow or keyboard
    always leaves the active card visible.
  - Early-exit when the card is already fully visible (no load nudge).

## Backend — Technical team managed from the portal (`backend/`)

- `submissions/portal.py`
  - New staff endpoints mirroring the player lifecycle:
    `coach_add`, `coach_edit` (incl. `is_published`),
    `coach_toggle`, `coach_photo`, `coach_delete`.
  - `_clean_coach_fields` validation (name/role ≤120, bio ≤600,
    sort 0–99, squad code must exist).
  - Coach photos go through `CoachPhotoStorage` — every save path
    re-encodes with EXIF/GPS stripped, pixel cap, extension matched;
    failures return a friendly toast, never a 500.
  - `build_page` renders the Technical-team view: coach cards (reusing
    the player-card scaffolding), squads select options, coaches JSON,
    and empty-state/grid visibility server-side.
- `sporting_pearls_backend/urls.py` — the five `/portal/coaches/…` routes.
- `submissions/portal_assets/body-a.html` — "Technical team" nav item
  with live count badge; capability bullet added.
- `submissions/portal_assets/body-b.html` — `view-coaches` section
  (toolbar, card grid, honest empty state, photo tips), coach edit/add
  modals, `coaches-json` data block, `dash.js?v17`.
- `submissions/portal_assets/dash.js` — view title, coaches data,
  card actions (publish/edit/photo/delete), edit/add handlers, badge and
  empty-state recount on load and after changes; the photo and delete
  modals are shared with players via a mode flag.
- `README.md` §8 — run-book entry for publishing the technical team.

The website side needed no new code: `the-squad.js` already renders
published coaches from `/api/coaches/` and keeps the honest
"published once confirmed" notice until the first coach goes live.

## Verification

- `submissions/tests/test_rev28_coaches_portal.py` — 10 tests: staff
  gate, full add→edit→publish→hide→delete lifecycle, field validation,
  portal page rendering, photo hardening (valid PNG upload with metadata
  strip, renamed text file rejected, bad extension rejected, missing
  file rejected).
- Full backend suite: **173 tests, all passing**.
- `scripts/check_rev28_ux.py` (repo copy: `scripts/check_rev28_ux.py`)
  — 25 browser checks against real servers: mobile arrows visible and
  disabled at the ends, arrow navigation U12→Féminin, active card in
  view, zero console errors; desktop arrows hidden, vertical list kept,
  all five tabs visible; portal login → Technical team view → empty
  state → add coach → publish → card updates → `/api/coaches/` serves
  it → hide → draft again. **All 25 pass.**
