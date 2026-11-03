# CHANGELOG — Revision 25 (Féminin gallery: hidden until real photos arrive)

| | |
|---|---|
| **Revision** | 25 (site + backend) |
| **Date** | 2026-11-03 |
| **Scope** | The Féminin page's "On the Pitch" gallery now ships HIDDEN and appears only when the backend serves real, published photos of the girls' programme. The five stock photos are withdrawn — the girls' team gets no stand-ins; the section renders solely from admin-uploaded images. Adds the FemininGalleryPhoto model, a public API endpoint, an admin surface and a media-gate rule on the backend; a small shared script on the site reveals and fills the section. |
| **Test results** | Django `manage.py check` + `makemigrations --check` clean (no missing migrations); submissions + parents test suites pass (163 tests). Endpoint check: `/api/gallery/feminin/` answers `{ok, count: 0, photos: []}` when nothing is published — the page keeps the section hidden. With a published photo the endpoint returns it and the section renders, lightbox opens, tiles reveal. Browser QA (Playwright, scripts/check_rev25_browser.py): no-API_BASE page keeps the section hidden with 0 console errors; wired backend + 5 published photos reveals 5 tiles, all images load, reveal animations fire, lightbox opens from a dynamic tile; zero-photo response keeps the section hidden. Static reference check: 0 missing assets (the five withdrawn stock photos were referenced only by the now-hidden markup). |

---

## 1. Why (product decision)

The gallery round (rev 24) restored the Féminin gallery with five stock
photographs as placeholders. The academy's position: the girls' programme
is presented with **real images only** — so the section comes off the
page until the office uploads actual photos from the backend. No stock
stand-ins, no "coming soon" placeholder panel: the page simply flows from
"The Target" figure straight into the Féminin Promise CTA until real
photos exist.

## 2. Site — the section ships hidden (site/feminin.html)

- `<section class="fg-sec" id="on-the-pitch" hidden>` — the `hidden`
  attribute keeps it off the page (no flash, no layout shift; the UA
  stylesheet's `display:none` wins because `.fg-sec` sets no `display`).
- The five stock tiles are gone; the `fg-grid` ships empty.
- `site/assets/img/feminin/feminin-01…05.jpg` removed from the repo
  (they remain retrievable in git history if ever needed).
- `site-config.js` is now included on the Féminin page (it was missing —
  the page had no API consumers until now, so `window.SP_CONFIG` was
  never defined there; the reveal script and any future backend wiring
  on this page need it).
- New include: `assets/js/shared/sp-feminin-gallery.js?v1`.

## 3. Site — sp-feminin-gallery.js (the reveal)

Mirrors the house pattern of `sp-fixtures.js`:

- Reads `SP_CONFIG.API_BASE`; empty (backend not wired yet) → the
  script exits and the section stays hidden. Nothing changes for the
  bundled/static deployment.
- `GET {API_BASE}/api/gallery/feminin/` → `{ok, count, photos:[…]}`
  with `{image, alt, caption}` per photo.
- Zero published photos, or any fetch/network error → stays hidden.
- With photos: builds `fg-tile` figures cycling the rev-24 collage
  rhythm (`t-hero, t-up, t-down, t-wide2, t-portrait`), sets
  `data-fb-hide="parent"` so a broken image hides its tile (the
  CSP-safe fallback listener covers dynamically inserted images),
  then removes `hidden` and reveals the fresh tiles with the same
  IntersectionObserver pattern as site-core (`.in` class, -8% bottom
  root margin, reduced-motion → immediate).

## 4. Backend — FemininGalleryPhoto (submissions/models.py)

- `FemininGalleryStorage`: re-encodes every upload on every save path
  (admin form, shell, future views) — Pillow-verified, EXIF/GPS/ICC
  stripped, extension matched to the real format, 40-megapixel bomb
  cap, fails closed with `ValueError`. Files land in
  `media/gallery/feminin/fg-<name>.<ext>`. Same contract as the
  player/coach photo storages.
- `FemininGalleryPhoto`: `caption` (tile label), `alt` (screen-reader
  text), `photo` (required), `is_published` (default False — the
  gallery appears only when at least one row is published), `sort`,
  timestamps. Ordered `['sort', 'id']`.
- Migration `0007_feminingalleryphoto`.

## 5. Backend — public endpoint + media gate + admin

- `GET /api/gallery/feminin/` (`views.feminin_gallery`): published
  photos only, absolute image URLs, `{image, alt, caption}` per row.
  Unpublished rows never leave the building; a photo row whose file
  is missing is skipped rather than shipped as a broken URL.
- `media_serve` gate: files under `gallery/feminin/` are public only
  while the referencing photo row is published — same policy as
  player/coach photos. Unpublished gallery files need a staff
  session; everything else answers the same plain 404.
- Django admin: **Féminin gallery photos** section — thumbnail
  preview, friendly upload validation (8 MB cap, JPG/PNG/WebP,
  readable-image check), `is_published`/`sort` inline-editable, and
  publish/unpublish bulk actions. Publishing the first photo puts
  the gallery on the website; unpublishing everything hides it again.

## 6. How the academy publishes the gallery

1. Deploy the backend and set `API_BASE` in
   `site/assets/js/shared/site-config.js` (already documented there).
2. Django admin → **Féminin gallery photos** → Add: upload a real
   photo, write a short caption + alt text, tick **published on
   website**.
3. Reload `feminin.html` — the "On the Pitch" section appears with
   the real photos, lightbox included. Zero photos published → the
   section stays off the page.

## 7. Files touched

| File | Change |
|---|---|
| `site/feminin.html` | gallery section `hidden`, tiles removed, `site-config.js` + script includes |
| `site/assets/js/shared/sp-feminin-gallery.js` | new — backend-driven reveal |
| `site/assets/img/feminin/*.jpg` | 5 stock photos removed |
| `backend/submissions/models.py` | + `FemininGalleryStorage`, `FemininGalleryPhoto` |
| `backend/submissions/migrations/0007_feminingalleryphoto.py` | new |
| `backend/submissions/views.py` | + `feminin_gallery` endpoint |
| `backend/submissions/urls.py` | + `gallery/feminin/` route |
| `backend/submissions/portal.py` | media gate: public-while-published for `gallery/feminin/` |
| `backend/submissions/admin.py` | + `FemininGalleryPhotoAdmin` (+ upload validation form) |
| `backend/README.md` | endpoint list updated |
| `scripts/check_rev25.py` | new — endpoint + media-gate functional check |
| `scripts/check_rev25_browser.py` | new — Playwright QA (hidden / revealed / zero-photo scenarios) |
