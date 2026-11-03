# CHANGELOG — Kit Revision 22 (real squad roster: Excel register import)

| | |
|---|---|
| **Revision** | 22 (supersedes 21) |
| **Date** | 2026-11-03 |
| **Scope** | Owner request: "update the website with the following player info" — delivered as `SPFA_Player_Administration_System_2026-2027.xlsx` plus two player-photo zip archives (`under19-photo-download-1of1.zip`, `under13-photo-download-1of1.zip`). The demo squads on the-squad page were replaced with the real academy register (50 players, season 2026–27): squad structure changed from the placeholder U9/U13/U15/U17/U19/Féminin to the register's **U12 / U14 / U16 / U19 + Féminin**. 29 real player photos wired in; formation board now places players by their registered position line; new bench strip keeps every registered player visible; player profile QR refs point at the real register; backend `player_seed.json` regenerated from the same source. No security control, safeguarding/DSO logic, form field or policy wording touched. |
| **Test results** | `manage.py test submissions` **163/163 PASS** (one assertion in the QR wiring test updated from the old demo captain ref `'U19-10'` to the real register refs `'U12-01'`/`'U19-05'`). Static sweeps: 0 old nav squad labels (`U9 & U13` / `U15 & U17`) anywhere in `site/*.html`; 29/29 squad photos present + HTTP 200; 50 refs identical across `the-squad.js`, `sp-player.js` and `backend/player_seed.json`. Crawl through the gateway: **41/41 pages + 133/133 unique assets HTTP 200**. Browser QA (1440px + 390px): 5 tabs, U12 boot, 11 dots + 7 bench chips (U12), modal photo/QR/chips verified, U19 5-dot honest layout, Féminin honest "being finalised" panel, 0 console errors; player.html?ref=U12-02 renders Brian Karisa Samuel with photo. VLM visual QA: 5 screenshots PASS. |

---

## 1. Real register imported — DONE

Source: `upload/SPFA_Player_Administration_System_2026-2027.xlsx`
(Player Register sheet, 50 rows). Squads: **U12 (18), U14 (16), U16 (11), U19 (5)**.

- Names, shirt numbers, primary positions and DOBs → ages (as of
  2026-11-03) taken verbatim; parenthesised photo-reference notes in the
  register's name column were parsed and stripped (they are file
  references, not part of anyone's name).
- Position words mapped to pitch codes: Goalkeeper→GK, Full Back→FB,
  Wing Back→WB, Centre Back→CB, Midfielder→CM, Winger→W, Left Wing→LW,
  Right Back→RB, Forward/Striker→ST, "Left / Right Wing"→W,
  "Wing Back / Goalkeeper"→WB. `groupOf()`/`SLOT_TXT` extended so the
  new codes classify and read correctly ("at full back", "on the wing").
- What the register does NOT carry is shown honestly, never invented:
  height and preferred foot are blank (modal shows "—" and drops the
  old fabricated "Ht 1.xx m" chip); no motto → quote line hidden; no
  fabricated attribute ratings — the dossier chips now show factual
  register fields (Position, Season 2026–27) only.
- Players with no DOB keep a blank age ("—"). One register row
  (Michael Kalu Johnson, U12) has no number and no position — he stays
  on the bench strip with a "·" number badge rather than being dropped.
- Nicknames (one row: "M'English") are not displayed — no UI slot for
  them yet; noted for a future round.

## 2. Formation board: position-aware placement + bench strip — DONE

- New `BANDS` map (per formation: which coordinate slot belongs to
  GK/DF/MF/FW). `renderTeam()` now groups the register by position line
  and fills the formation slots accordingly — keepers in goal,
  defenders in the defensive line, and so on. Overflowing players fill
  remaining line gaps (never the keeper's slot); the rest move to a new
  **bench strip** below the pitch (`#bench`), one pill per player
  (number, name, position code), clickable → same dossier modal.
  **No registered player is invisible**: U12 shows 11 on the pitch +
  7 on the bench; U16's 11 fit 3-5-2 exactly; U19's 5 registered
  players show as 5 dots (the register lists no U19 goalkeeper — the
  keeper slot stays empty rather than faking one).
- `slotByPlayer` tracks placement so the dossier's mini-pitch dot and
  "tactical role" line are correct for bench players too
  ("in the extended squad").
- Formations: U12 4-4-2, U14 4-3-3, U16 3-5-2, U19 3-5-2, Féminin 4-3-3.
- CSS: `.bench/.bench-tag/.bench-row/.bench-p` added
  (the-squad.css ?v23→**v24**); mobile = horizontal scroll strip.

## 3. Squad photos wired — DONE

- The two photo archives were unpacked; the register's inline
  references (`U-16__9jpg`, `U-19__*29jpg`, …) were mapped to files by
  set + number (U-16 refs → the "under13" download, numbers ≤ 24;
  U-19 refs → the "under19" download, numbers ≤ 33 — the only mapping
  that covers every referenced number).
- **29 photos** staged as `site/assets/img/squad/u16-NN.jpg` /
  `u19-NN.jpg` (~4 MB, 1024×1317 portraits, all verified readable and
  HTTP 200; VLM spot-check: clean single-subject portraits on the club
  crest backdrop).
- 21 of 50 players have no photo reference in the register — they show
  the existing jersey-number fallback (by design, not an error).

## 4. Tabs, stats, meta, sitewide labels — DONE

- the-squad.html tabs: 6 → **5** (U12 Foundation, U14 Development,
  U16 Performance, U19 (Senior), Féminin last with "Roster TBC"),
  boot tab = U12. Squad-legend copy now cites the 2026–27 register.
- Stats band: 66→**50** Rostered Players, 6→**4** Age Divisions,
  6→**5** Official Squads (100% School Attendance unchanged).
- Captains: the register carries no captain data → `CAPTAINS = -1`
  for all squads, so the honest "named at the start of each season"
  panel shows (the fabricated demo captains are gone).
- Meta/OG descriptions updated; **sitewide nav mega-menu** relabelled
  in all 41 pages (U9 & U13 → U12 & U14; U15 & U17 → U16) including
  the preview captions; homepage pathway tiers + impact label updated
  to the real structure.
- Program pages' prose still describes the U9–U19 development pathway
  generally — left untouched this round (a content decision for the
  owner; the register defines competitive squads, not every training
  group).

## 5. Profile QR + backend seed in sync — DONE

- Tuple field 9 now carries a stable ref per player (`U12-01`…`U19-05`);
  the dossier QR scans to `player.html?ref=…` and renders from the
  regenerated `DEMO_PROFILES` in sp-player.js (rev 22) — including the
  player photo, which the demo path previously left blank.
- `backend/player_seed.json` regenerated from the same source
  (50 players, 5 squads, Féminin empty). All three artifacts verified
  to carry the identical 50 refs.
- Live mode unchanged: `/api/players/` (from the seed) still overrides
  the bundled roster when `API_BASE` is set; `applyRoster` accepts the
  new squad keys.

## 6. Féminin — honest empty state (owner decision pending)

The register contains no Féminin players. The tab remains (the program
is real and has its own page) but now shows the "Squad list being
finalised" panel instead of fabricated names. **Owner action: send the
Féminin register rows when ready and they will be imported the same way.**

---

## NOT CHANGED (this revision)

- No form fields, no backend logic beyond the seed data + one test
  assertion, no policy/safeguarding wording, no deployment or email
  configuration, no dependency changes.
- Demo/showcase ethics preserved: nothing on a live deployment is ever
  fabricated — the previous demo squads existed only in demo mode, and
  they are now replaced by real data everywhere.
