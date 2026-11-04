# Rev 26 — All squads switch to 4-2-3-1 (2026-11-04)

The academy moves every team to a 4-2-3-1 base shape for the 2026-27 season.
This revision makes 4-2-3-1 the default everywhere: website pitch, register
data, backend model, seed and staff portal. The other presets (4-3-3, 4-4-2,
3-5-2) remain available so the office can still switch a squad's shape from
the Management Portal at any time.

## Website (`site/`)

- `the-squad.html`
  - All five team tabs now read `4-2-3-1 · …` in their meta line
    (U12 Foundation, U14 Development, U16 Performance, U19 Senior, Féminin).
  - Pitch header chip `#pmForm` and player dossier `#mFormTxt` start on 4-2-3-1.
  - Script include bumped `the-squad.js?v26` → `?v27` (cache-bust).
- `assets/js/pages/the-squad.js` (v27)
  - All five `TEAMS[*].form` values set to `'4-2-3-1'`
    (U12 was 4-4-2, U14 was 4-3-3, U16/U19 were 3-5-2, Féminin was 4-3-3).
  - All four fallback sites now fall back to 4-2-3-1 instead of 4-3-3:
    `renderTeam`'s `formKey`, its `BANDS` lookup, `openModal`'s slot lookup,
    and `applyRoster`'s guard when the API sends an unknown formation.
  - The 4-2-3-1 coordinate preset (GK 50/91 · back four · double pivot ·
    attacking three · lone striker) was already present in `FORM`/`BANDS`
    and is unchanged; the other presets are kept for the portal switcher.
  - U19 still has only 5 registered players, so its board honestly shows a
    subset of the 4-2-3-1 slots (no invented players). Féminin remains empty
    until the office sends the girls' register.

## Backend (`backend/`)

- `submissions/models.py` — `Squad.formation` default `'4-3-3'` → `'4-2-3-1'`.
- `submissions/migrations/0008_alter_squad_formation.py` — AlterField migration.
- `player_seed.json` — all five squads seeded with `"form": "4-2-3-1"`.
- `submissions/management/commands/import_roster.py` — seed fallback is now
  4-2-3-1.
- `submissions/portal_assets/body-a.html` — portal feature bullet mentions
  4-2-3-1 first.
- `README.md` / `templates/POST-INSTALL-README.txt` — run-book texts updated.

## Deployment docs

- `DEPLOY-BACKEND-RENDER.md` — rewritten after the first live Render deploy:
  `migrate` now runs in the **Start Command** (the pre-deploy instance has no
  access to the `/data` disk — pre-deploy migrations caused
  `no such table` errors), collectstatic moved into the Build Command, and
  the troubleshooting table records the E014 trailing-slash and 403 PAT
  issues we actually hit.

## Verification

- `scripts/check_rev26_formation.py` — fresh DB: migrate + `import_roster`,
  then seed JSON, ORM and public API (`/api/players/`, `/api/health/`) all
  report 5 squads / 50 players / formation 4-2-3-1 with no legacy values:
  **all checks pass**.
- `node --check` on the modified JS passes.
