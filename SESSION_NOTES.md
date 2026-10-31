# Pick'Em Lab — session notes

_Live state only. Rules, start/end-of-session steps and the code map are in `CLAUDE.md`. The simulator plan's master copy is `research/sim-plan.md` (link to it here, don't copy it). Keep full blocks for the last 3 sessions; older ones go to the Session index as one line each._

---

## Where we are

- **App:** v36 (31 Oct 2026): champ select tidy-ups from Luke's phone notes. v35 (same day): header, legend and tournament setup tidy-ups. v34 (same day): Swiss round 4 day 3 data, TES–BLG confirmed from the Oracle's Elixir file. App data and code are correct as they stand.
- **Real data:** all of Swiss rounds 1–4, 44 games, in `js/worlds-live.js` (data to 30 Oct). H2H in `js/h2h.js` (data to 30 Oct). **HLE 2-0 G2 is from the Reddit post-match thread, Leaguepedia and pickorban, not yet the Oracle's Elixir file:** re-check it when the next file arrives.
- **Sim engine plan:** written 27 Oct, committed `0929636` (29 Oct). Status: planned, not started. See `research/sim-plan.md`.
- **Draft Game:** Tier 1 built, autosave added 26 Oct. See `Draft Game/draft-card-game-handoff.md`.
- **Where work happens:** Claude Code sessions only. The claude.ai chats that built the app no longer write to the repo.

---

## What's next

| Task | Status/blocker |
|---|---|
| **Sim session 1:** ratings and the "who wins" model | Not started. Read `research/sim-plan.md` first. Starts with planning the ratings foundation with Luke (skills per role, what each is fitted from, the overall, how they feed the sim) before any fitting or code |
| Sim sessions 2–5 | After session 1, in order (see the plan) |
| Confirm HLE–G2 (30 Oct) against the next Oracle's Elixir file | Waits for a file with data past 30 Oct 22:00 UTC. Compare both games field by field (check Hans Sama's game 2 CS: 212 Leaguepedia v 211 pickorban, and grubs), fill in CS@15, rerun `build_from_oe.py` on a scratch copy (H2H should still show HLE v G2 5-0) |
| Champ select pick/ban board redesign (Luke's note, 31 Oct) | Pick order as a top row under ban 1; ban portraits fill their slots greyed out; pick portraits fill the role box next to the player. Show Luke 3 style previews at phone size first (e.g. LOS v TL game 3), then build as its own change (`teamPanel` in `js/core.js`) |
| Add Swiss round 5 (31 Oct), then knockouts (3–14 Nov) | Round 5 is being played 31 Oct; score it with the app before adding. Steps in `research/worlds-live-2026.md` |
| Draft Game next steps | Pick one when wanted (feel tweaks, real data, Tier 2, smarter AI, Bo series); see the handoff file |

**Parked:** Custom tournament (Play → Custom). Planned feature, not being worked on yet (Luke, 29 Oct).

---

## Open decisions (Luke)

None open right now.

Decided 29 Oct (details in `research/sim-plan.md`):
- **Ratings:** fitted ratings replace what's shown on the cards. Keep the idea: readable role skills + overall that are interesting and feed the match sim. **Plan the foundation with Luke first** (sim session 1).
- **Draft AI:** rebuilt from data (comfort, team composition, meta, synergy, counters, plus whatever else the data shows).
- **Draft review:** based on the new model. **Plan the foundation with Luke first** (sim session 4).
- **Old engine:** kept. The app uses it until the new one passes its tests, then it stays as a reference, fallback and possible simple mode.
- **Minor leagues:** out of fitting for now; used for player history and pools (e.g. 369).
- **Scorecard:** not in the app for now. Show it to Luke as an artifact in the chat each session or match-day update; keep the numbers in the research notes.

---

## Watch-items

| Watch-item | Trigger |
|---|---|
| Player of the Game isn't published by any source checked so far, so real POG isn't used. **New lead (30 Oct):** Leaguepedia's Main Event page now has an "MVP" column per series and "MVP Standings" (e.g. TES–BLG: Tian; several series show "None"). Not checked: where it comes from or whether it is the official award | Luke decides whether to look into it (also needed for sim session 4) |
| Old sim overrates BLG against TES (76–90% in all 3 games, TES won 2-1); the ceiling issue keeps showing | The new sim (sim sessions 1–4) |
| `build_from_oe.py` labels every "WLDs" row as "Worlds" in the H2H "Met at" list, including the 17–19 Sep qualifier rows its own header says aren't Worlds. Game counts aren't affected | Before the script becomes the match-day routine (sim session 5) |
| `build_from_oe.py` always overwrites `js/h2h.js` and `js/worlds-live.js`; an option to write to another folder would make test runs safer | Same as above |
| How Swiss round 4 splits across 28–30 Oct is assumed in `js/tournament.js` (`DAYS`). Leaguepedia now publishes it: 2 series a day (28: MKOI–T1, IG–LYON; 29: KC–CFO, TES–BLG; 30: TL–LOS, HLE–G2). The days in `DAYS` match; how the code assigns series to days was not checked | Check when convenient |
| Old sim quirks, left alone: odds use 300 runs (tournament), 600 (draft review) or 1500 (series); supports' CS diff is scaled by 0.3 twice in `gameStats` | If the old engine becomes a simple mode, decide with Luke whether to tidy these |

---

## Recent updates

### Session (31 Oct 2026) — v34: Swiss round 4 day 3, TES–BLG confirmed
- **New Oracle's Elixir file** (9,831 games, data to 30 Oct 22:00 UTC): has TES–BLG and LOS–TL, not HLE–G2.
- **TES 2-1 BLG:** matches the file on every field; CS@15 and `fp` filled in from it.
- **LOS 2-1 TL:** added from the file, game 3 cross-checked with pickorban. Josedeodo's game 3 kill participation is 1.2 (1/3/5 on 5 team kills, same on pickorban), kept as sourced.
- **HLE 2-0 G2:** added from Luke's Reddit post-match paste, checked against Leaguepedia's scoreboards. CS from Leaguepedia, damage share from pickorban. CS@15 null; to confirm against the next file.
- **Out-of-sample (v33 before the update):** favourite 4 of 5, log loss 0.573, Brier 0.192. Running total: 27 of 44 (61%).
- `build_from_oe.py` run on a scratch copy: 42/44 OK (the 2 HLE–G2 games not in the file yet), `js/h2h.js` rebuilt to 30 Oct (new: LOS v TL 2-1), then HLE v G2 5-0 added by hand. Pick, ban and win counts for all 86 champions match Leaguepedia (44 games).
- Cache v33 → v34. How checked: local server in a new browser-pane tab, data counts, H2H and player form read in the console, jungle, top, meta, champion and power pages at desktop and 375 px (no sideways scroll), console clean. Server stopped, tabs closed, temporary `.claude/launch.json` removed.
- Committed `889b55d` and pushed.
- **Matchup grid:** a champion-v-champion grid of the Worlds games was previewed in chat; the idea (bot lane as a duo, lane result v game result) is noted under session 2 in `research/sim-plan.md`.
- **v35, display tidy-ups:** Luke left 5 notes on the running app through a temporary note overlay in the browser pane (not part of the app). Changes:
  - Intro text, legal line and the Tournament mode description now use the full page width.
  - Tournament setup team picker lists teams in power-ranking order with rank, region seed tag and team colour badge (same pieces as Power Rankings); boxes widened so names don't cut off (3 per row on desktop, 1 on a phone).
  - "Custom · soon" button: flat muted fill and muted text instead of 60% opacity, including the Subway theme.
  - Header legend: shorter Meta / In the mix / Not seen text with "!" hovers for the patch detail; hidden on Play → Worlds 2026 and Custom (those pages use neither ratings nor meta tags, and the tournament reuses the tag colours for Qualified / Alive / Eliminated).
  - Cache v34 → v35. How checked: local server in a new browser-pane tab; legend shown/hidden per page read in the console; team picker order, ticking a team, no cut-off names; all 7 Worlds mode themes plus light mode looked at; "!" hovers at desktop and 375 px (inside the screen); no sideways scroll on 6 pages at 375 px; console clean. Server stopped, tabs closed, `.claude/launch.json` removed, test theme settings and notes cleared from localhost storage. Committed `8359d05` and pushed.
- **Notes sessions saved:** the overlay is `tools/qol-notes-overlay.js` (now with a live width readout, "375 px · phone"), and the routine is the "Notes sessions" section of `CLAUDE.md`.
- **v36, champ select tidy-ups** (Luke's 9 notes at 375 px; 8 built, the pick/ban board redesign is its own task in What's next):
  - Worlds mode controls stay on one row on phones (the "Worlds mode" word is hidden there; the select keeps its label for screen readers).
  - Header legend split into labelled **Players** and **Champions** groups.
  - Champ select default matchup LYON v LOS (was TSW).
  - Setup labels (Your team, Opponent, Format, Draft style, Game 1 side) in bright small capitals (`.flabel`) instead of muted grey.
  - Champion card bars tighter: row gap 8 → 3 px, bars 16 → 14 px, value lines closer (3-bar group on a phone 145 → 124 px).
  - Suggestion reasons brighter (`fmtWhy`): meta tier in the legend's Meta / In the mix colour, player names in gold, grey separators.
  - Champion card "!" hovers shortened (Recent meta, Worlds meta, Most picked, Pairs with, Countered by, Counters); same facts and sources.
  - Cache v35 → v36. How checked: local server in a new browser-pane tab at desktop and 375 px; one-row controls, no sideways scroll, legend groups, default LOS, new labels, bar heights and all six hover texts read in the console; a Bo3 started to see suggestions and the champion sheet; text colours read in all 7 Worlds mode themes plus light mode; console clean. Server stopped, tabs closed, `.claude/launch.json` removed, test settings and notes cleared from localhost storage. Not committed yet.

### Session (30 Oct 2026) — v32: Swiss round 4 day 2, aged subway sign
- **Data:** KC 2-0 CFO from Luke's new Oracle's Elixir file (data to 29 Oct 21:00 UTC). It matches pickorban and Leaguepedia on every field checked. TES 2-1 BLG isn't in the file yet, so it came from Leaguepedia's scoreboards with pickorban for damage share (CS@15 null, `fp` left out). `js/worlds-live.js` now has 39 games. `build_from_oe.py` was run on a scratch copy: 34/34 OK, `js/h2h.js` rebuilt to 29 Oct, then TES–BLG added by hand. Details and sources in `research/worlds-live-2026.md`.
- **Pick/ban check:** the app's pick, ban and win counts for all 84 champions match Leaguepedia's Main Event champion statistics (39 games).
- **Out-of-sample (v31 before the update):** favourite 3 of 5, log loss 0.945, Brier 0.334. BLG was 76–90% in all three TES games. Running total: 23 of 39 (59%).
- **Subway band:** caption removed; the band now looks like an aged enamel station sign (grain texture, top white stripe, off-white Helvetica, faded bullets with scuffs, screw heads). CSS only, in `css/styles.css`.
- Cache v31 → v32. How checked: local server in a new browser-pane tab at desktop and 375 px, console clean, data counts and H2H read in the console, role-page game log for 369 renders with the missing CS@15 shown as a dash. The temporary `.claude/launch.json` was removed afterwards.
- Download link for the Oracle's Elixir file is now in the Sources section of `research/worlds-live-2026.md`.
- Committed `4fe2ab1` and pushed.
- **v33, Counters row:** champion page cards (`champCard`) and the hover card (`champTip`) now show "Counters": 3 champions this one beats (`beats3` in `js/core.js`). Order: same-lane METAsrc matchups at 50.5%+ (so the shown % rounds to 51%+), then other-lane matchups, then lane opponents it beat at Worlds; only champions seen in pro play (`POOL`). Example: Nocturne shows Rengar 55%, Locke 54%, Qiyana 54%. Champions with no qualifying matchup show "no matchup data" (27 of 163 before the 50.5% cut-off; not recounted after it). How checked: local server in a new browser-pane tab, every pool champion's row checked in the console (none at 50% or below), all 15 jungle cards show the row, hover card renders, a Counters chip opens that champion's hover card, 375 px with no sideways scroll, console clean. Committed `7b3c221`.

### Session (29 Oct 2026, later) — v31: themes, role-page hover, ticker fix, side colours, round 4 day 1
- **Themes:** Brooklyn · Subway now uses the same clipped buttons as the other themes: route-sign green with an enamel gloss, white selected section, N/Q/R yellow selected page and main buttons, black sign band on panels, explained station band. "Brooklyn Final" renamed **Arcade Smash** (saved value still `brooklyn`): CRT scanlines, pixel-type title (Press Start 2P), neon glow, INSERT COIN, arcade-yellow labels and note bars, dull amber "In the mix".
- **Role pages:** hovering a player name on a card shows a Worlds game log (date, opponent, champion v lane opponent, K/D/A, CS@15, W/L) plus ban risk (`playerLogTip` in `js/core.js`). Elsewhere the hover is unchanged.
- **Ticker fix:** notes scroll only when they don't fit (`fitTicks`, run after render, after fonts load and on width change via ResizeObserver); speed follows length.
- **Draft cards:** pick and ban tags use blue / red side colours (`sideCol`), never team badge colours.
- **Data:** Swiss round 4 day 1 (28 Oct: T1 2-0 MKOI, IG 2-1 LYON) added from Luke's new Oracle's Elixir file, cross-checked with pickorban. `build_from_oe.py` run on a scratch copy: 34/34 games OK, `js/h2h.js` rebuilt to 28 Oct (only new pairs changed). Out-of-sample: favourite 3 of 5, log loss 0.508.
- Previews were built and approved on a scratch copy first. How checked: browser pane at 1440 and 375 px, console clean, hover and draft cards tested.

---

## Session index

| Session | Summary |
|---|---|
| 20–27 Oct 2026 (claude.ai chats) | App built from v20 to v30 (see `git log`): player and champion cards, tournament, series mode, real Worlds data, power rankings, themes. Sim back-tested on 711 series (22 Oct). Sim plan written 27 Oct. No notes file then |
| 29 Oct 2026 | CLAUDE.md, SESSION_NOTES.md and the build script added; sim plan decisions recorded (ratings, draft AI, draft review, old engine, minor leagues, scorecard). No app change (v30) |
