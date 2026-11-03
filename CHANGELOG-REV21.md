# CHANGELOG — Kit Revision 21 (owner UI round: no carousel, no black, hero parallax, squad QR cards)

| | |
|---|---|
| **Revision** | 21 (supersedes 20) |
| **Date** | 2026-10-27 |
| **Scope** | Owner request with a screenshot of the support-us hero stat band: "for pages with this style under the footer, kindly remove the carousel and ensure there is no black color and it has a parallax effect." Applied site-wide to every page in that style family. Plus the owner's standing squad-page request: every player card carries the player's unique QR profile code. Plus one backend test-suite portability fix. No deployment, no email, no personal data, no security/safeguarding logic changes, no form fields, no policy wording, no build step. |
| **Test results** | `manage.py test` **163/163 PASS** (162 prior + 1 new QR wiring test) and phase-0 guard **12/12 PASS** re-run 2026-10-27 after the changes (venv rebuilt from the pinned requirements). Static sweeps: 0 marquee HTML / 0 `.mq-` CSS / 0 `mqTrack` JS; 16 `heroBg` photo heroes; 11 `hero-parallax.js` includes; 0 `navy-3` footer rules; wave selectors fixed in 9 CSS + 3 inline-style pages; QR wiring present on the squad page (vendor include, `mQr`/`mQrLink` targets, ref plumbing). Browser QA (12 representative pages, 1440px + 390px): 0 console errors, marquee gone, footer computed `rgb(26,50,96)`, waves sand/pearl + blue tints, parallax exactly 0.25× scroll. VLM visual QA: 5 screenshots PASS. |

---

## 1. Carousel removed — DONE

- The auto-scrolling marquee strip ("the carousel") existed on **14 pages**
  (12 sand variants, `the-squad` + `leadership-governance` navy
  "institutional band" variants, `player-development` amber-tape variant).
  The strip's HTML was removed from all 14 via a balanced-div walk
  (`scripts/rev21_marquee_black_parallax.py`).
- Dead code swept: marquee CSS blocks (11 page CSS + 3 inline-style HTML),
  the `mqTrack` JS in `site-core.js`, `our-story.js`, `core-values.js`,
  `vision-mission.js`, `partners.js`.
- Seam fixes so the hero wave blends with the section that replaced the
  strip: partners `w1` → pearl, leadership `w1` → sand, the-squad inline
  fill `#0c1a33` → sand.

## 2. No black — DONE (real bug found and fixed)

- **Pre-existing bug, present since the original build:** the hero "tide"
  waves rendered **pure black** (`rgb(0,0,0)`) because the CSS wrote
  `.tide .w1 path { fill: … }` but `.w1` **is** the `<path>`, so the rule
  never matched and the SVG default black fill applied. Fixed the selectors
  to `.tide path.w1` / `.tide path.w2` in 9 page CSS + 3 inline-style HTML
  (the remaining tide pages used inline `fill` attributes and were always
  correct). Verified via `getComputedStyle` in the browser. This was almost
  certainly the black the owner saw.
- Near-black recolors in the 14 affected style files: solid stat-band
  gradient stop `rgba(12,26,51,1)` → `rgba(26,50,96,1)` (navy-4); all
  `rgba(12,26,51,*)` tints → `rgba(20,40,75,*)` (navy family); hero
  fallback navy-2 → navy; chairman/leadership hero gradient endpoints and
  player-development hero gradient hexes → navy family; `theme-color`
  metas → `#14284b`; `sp-fig-media` placeholder gradients de-blacked.
- **Footer unified site-wide:** `var(--navy-3)` → `var(--navy-4)` in
  29 page CSS + `index.css` + 3 inline-style HTML, so every page's footer
  is the same readable brand navy (computed `rgb(26,50,96)`).
- Deliberately untouched dark areas (different hero family / intentional
  dark sections, flagged for the owner as optional follow-ups):
  homepage/academy/join-us/coaching-philosophy hero scrims (navy-2 based),
  `.train-sec` / `.path-beyond-sec` on the goalkeeper/education pages,
  the index media-tile placeholder. All are brand navy, none is black.

## 3. Parallax on every photo hero — DONE

- New `site/assets/js/shared/hero-parallax.js` (same pattern as the
  leadership page's existing implementation: reduced-motion-safe,
  `requestAnimationFrame`-throttled, 0.25× translate).
- Wired on all **16 photo heroes**: `id="heroBg"` on `.hero-bg` plus the
  include before `</body>` (11 new wirings; 5 pages already had their own
  parallax: the-squad, leadership-governance, boys-programme,
  goalkeeper-development, education-life-skills).
- Verified in-browser: `translateY` tracks scroll at exactly 0.25×
  (the-squad's own implementation at its 0.22×).

## 4. Cache busting — DONE

- Asset versions bumped `?v22` site-wide, then `?v23` on the 9
  wave-fixed CSS files, so no visitor receives stale CSS/JS
  (39 pages touched).

## 5. Backend test-suite portability — DONE

- `backend/submissions/tests/test_phase7.py` (SiteWiringTests) hardcoded
  the build machine's absolute path to the shipped `site/` folder. Now
  resolved relative to the test file (`parents[3] / 'site'`), so the
  shipped suite runs on any install path. No backend behaviour changed —
  the full suite and the phase-0 guard were re-run green after the fix.

## 6. Squad player cards carry the player's unique QR — DONE

- Owner request (with a sample card for James Karanja): the player
  cards on the squad pages should each carry the player's **unique**
  QR code. Implemented in the player dossier modal on `the-squad.html`:
  every player's modal now shows a framed QR that encodes that
  player's public profile URL (`player.html?ref=…` — public fields
  only, fail-closed, `noindex`).
- QR generation is **self-hosted** (`site/assets/js/vendor/qr.min.js`,
  the `qrcode-generator` library, MIT): no CDN, so the site's CSP
  stays strict; verified `eval`-free (CSP-safe).
- Refs are per-player and unique: on the live roster they come from
  the API (`p.ref`, e.g. `U19-01`); in demo mode they are derived
  from the squad code + shirt order to match `player_seed.json`, so
  no two players share a code.
- Fail-closed: if the QR library is unavailable or rendering throws,
  the QR card is hidden entirely — never a dead link or empty frame.
- `sp-player.js` gained a demo-profile fallback dataset (captain
  `U19-10` seeded) so scanning a demo-mode code lands on a real
  profile page instead of the not-available panel.
- New backend test `test_squad_player_cards_carry_unique_qr` locks
  the wiring (vendor include, render targets, ref plumbing, MIT
  attribution, `eval`-free, demo fallback) — the suite is now
  **163** tests.

---

### NOT CHANGED (by instruction and standing constraints)

- No deployment, no email, no personal data, no CSP/rate-limit/media-gate/
  audit changes, no safeguarding/DSO logic, no form fields or validation,
  no policy wording, no design redesign beyond the requested items.

### Still queued (user-agreed order, not in this revision)

- Owner facts confirmation (contact "8 Development Programmes" count,
  partners "4 Active Squads" vs 6, response-time wording, attribution
  reading — see CHANGELOG-REV20.md owner decisions).
- Join Us hero refresh; contact stats strip; residual sub-12px label
  sweep; mobile headline orphan fix.

### EVIDENCE

- Backend: venv rebuilt from pinned requirements (Django 6.1.2);
  `manage.py test submissions` **163/163 PASS**; `phase0_guard_tests.py`
  **ALL PASS** (re-run 2026-10-27).
- Static sweeps (re-run 2026-10-27): 0 `marquee` in HTML, 0 `.mq-` in
  CSS, 0 `mqTrack` in JS, 16 `heroBg`, 11 parallax includes, 0 navy-3
  footer rules, `path.w1` fix present in 12 files; QR wiring present
  (`qr.min.js?v1` include before `the-squad.js?v25`, `id="mQr"` +
  `id="mQrLink"` in the modal, `.m-qr` CSS block present).
- Browser QA: 12 pages (support-us, leadership-governance, the-squad,
  partners, our-story, player-development, contact, index, academy,
  join-us, form-10, policy-player-parent-code) — marquee 0, footer
  `rgb(26,50,96)`, computed wave fills sand/pearl + blue tints,
  parallax 0.25×, 0 console errors; all 41 pages 200 via the gateway.
- VLM visual QA: hero-wave + footer + mobile 390 + leadership + squad
  hero shots — all PASS (one mid-animation capture investigated and
  re-shot clean).
