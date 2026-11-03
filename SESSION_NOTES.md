# Pick'Em Lab — session notes

_Live state only. Rules, start/end-of-session steps and the code map are in `CLAUDE.md`. The simulator plan's master copy is `research/sim-plan.md` (link to it here, don't copy it). Keep full blocks for the last 3 sessions; older ones go to the Session index as one line each._

---

## Where we are

- **App:** v38 (2 Nov 2026 AEST): Swiss round 5 data, HLE–G2 confirmed from the Oracle's Elixir file. v37 (31 Oct): new champ select pick/ban board and tier colours. App data and code are correct as they stand.
- **Real data:** the whole Swiss stage, 51 games, in `js/worlds-live.js` (data to 31 Oct), every game confirmed against the Oracle's Elixir file. H2H in `js/h2h.js` (data to 31 Oct). Knockouts start 3 Nov (US).
- **Time zones:** Luke's dates are AEST; Worlds game days are US dates; the Oracle's Elixir file is UTC. Check a game's UTC time against the file before saying it has been played.
- **Sim engine:** session 1 (ratings and who-wins model) **fitted and tested, report not written yet**. Decisions in `research/sim-plan.md`; scripts and notes in `research/sim1/` (start with its README); result tables in `research/model/sim1/`.
- **Draft Game:** Tier 1 built, autosave added 26 Oct. See `Draft Game/draft-card-game-handoff.md`.
- **Where work happens:** Claude Code sessions only. The claude.ai chats that built the app no longer write to the repo.

---

## What's next

| Task | Status/blocker |
|---|---|
| **Sim session 1 report (next)** | Fitting and tests done 3 Nov. Write `research/sim1-report.md` from `research/sim1/README.md`, the JSON/CSV results in `research/model/sim1/` and the decisions in `research/sim-plan.md`; show Luke the scorecard as an artifact; then propose a commit (the new folders are not committed yet). No app change |
| Sim session 1 open items | Experience re-test after the Worlds knockouts; Faker must not stay at a mid rating (S5 72) — resolve through the process (session 2 champion context, experience re-test, how "wins beyond stats" is shared); "wins beyond stats" shown as a team stat |
| Sim sessions 2–5 | After session 1, in order (see the plan) |
| Add knockouts (quarter-finals 3–6 Nov, semi-finals 7–8 Nov, final 14 Nov, US dates) | Waits for the games and the next Oracle's Elixir file. Score each match day with the app before adding. Steps in `research/worlds-live-2026.md` |
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

### Session (2 Nov 2026, AEST) — v38: Swiss round 5, HLE–G2 confirmed
- **New Oracle's Elixir file** (9,857 games, data to 1 Nov 11:42 UTC; last Worlds game 31 Oct 23:05 UTC): has HLE–G2 and all of round 5.
- **HLE 2-0 G2:** matches the file on every field (incl. Hans Sama's 212 CS and the grubs); rows replaced with the file's, adding CS@15.
- **Round 5** (31 Oct): KC 2-0 MKOI, LYON 2-1 LOS, BLG 2-0 HLE added from the file; all 7 games match Leaguepedia's Round 5 scoreboards (lengths, bans, objectives, champions, K/D/A, CS). 51 games now.
- **Out-of-sample (v37 before the update):** favourite 6 of 7, log loss 0.629, Brier 0.201. Running total: 33 of 51 (65%). KC 89% and LYON 89% / 86% above the ceiling.
- `build_from_oe.py` on a scratch copy: 51/51 OK; `js/h2h.js` rebuilt to 31 Oct (BLG v HLE 7-4, KC v MKOI 17-8, LOS v LYON 3-2); HLE v G2 5-0 now comes from the file. Pick, ban and win counts for all 90 champions match Leaguepedia (51 games).
- Cache v37 → v38. How checked: local server in a new browser-pane tab, data counts and H2H read in the console, 8 pages render at desktop, no sideways scroll on 5 pages at 375 px, console clean. Server stopped, tabs closed, `.claude/launch.json` removed.
- Also: v37 committed `bd396b3` and pushed. Luke's time zone (AEST) saved in Claude's memory and noted above.
- Committed `b1ed266` and pushed.
- **Sim session 1 (same day, later):** planned with Luke (8 decisions + role skills table, committed `c845ba7`), then fitted and tested in scratch: team ratings from results (league, side, 90-day recency), player skills with a league shift per role, S5 card scale adopted, extra Worlds weight dropped (test), experience tested (not adopted yet), sources checked against Leaguepedia and gol.gg, fixed ID lookup built, new model beats the app on the 51 Swiss games (0.639 v 0.679). Copied to `research/sim1/` and `research/model/sim1/` for the next session; `research/sim-plan.md` updated. **Not committed yet.** Report moved to a new chat because this one reached 93% context.

### Session (31 Oct 2026) — v34–v37: Swiss round 4 day 3, display tidy-ups, pick/ban board
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
  - Cache v35 → v36. How checked: local server in a new browser-pane tab at desktop and 375 px; one-row controls, no sideways scroll, legend groups, default LOS, new labels, bar heights and all six hover texts read in the console; a Bo3 started to see suggestions and the champion sheet; text colours read in all 7 Worlds mode themes plus light mode; console clean. Server stopped, tabs closed, `.claude/launch.json` removed, test settings and notes cleared from localhost storage. Committed `5d53243` and pushed.
- **v37, pick/ban board** (Luke picked "style 2" after three rounds of previews in chat; built and previewed locally before commit):
  - Order bar (`renderDraft`, `.track`/`.tk`): 20 tiles in draft order, side colour of who acts, B/P + step number (B1…P20); a done step shows its champion (bans greyed with a strike, picks framed in side colour); current step gold. Desktop: one row across the full width; phones: 2 rows of 10.
  - Bans (`teamPanel`): phase 1 (3) | divider | phase 2 (2) per team.
  - No jumping: the "Picking… open" line always keeps its space; the turn banner has fixed line boxes (1+1 lines desktop, 2+2 phone), including "Draft complete"; rows fixed height.
  - Phones: both teams side by side (`.board.pb`, so the draft review's `.board` is unchanged); 50 px rows, no splash art, no role menu; a picked champion's tap sheet has a Role bar (`setPickRole`, shared with the desktop role menu; a team-mate in that role swaps).
  - Tier text in Meta page colours (`tierCol`): S gold, A teal, B blue, C muted grey; in suggestion reasons, champion hover/tap cards, champion page cards and the draft review table.
  - Cache v36 → v37. How checked: local server, separate test tabs; full 20-step drafts with AI and by hand at 1280 px and 375 px with panel, row, banner and bar heights measured every step (no change between steps); Undo; a tournament draft (LOS v T1); role change and swap from the tap sheet; draft review layout on phone; colours in all 7 Worlds mode themes plus light mode; no sideways scroll; console clean. Test run and settings cleared from localhost storage.
  - Note: one earlier preview tab of Luke's was reloaded by mistake during testing (CLAUDE.md rule 9); later tests used separate tabs.
  - Committed `bd396b3` and pushed.

### Session (30 Oct 2026) — v32: Swiss round 4 day 2, aged subway sign
- **Data:** KC 2-0 CFO from Luke's new Oracle's Elixir file (data to 29 Oct 21:00 UTC). It matches pickorban and Leaguepedia on every field checked. TES 2-1 BLG isn't in the file yet, so it came from Leaguepedia's scoreboards with pickorban for damage share (CS@15 null, `fp` left out). `js/worlds-live.js` now has 39 games. `build_from_oe.py` was run on a scratch copy: 34/34 OK, `js/h2h.js` rebuilt to 29 Oct, then TES–BLG added by hand. Details and sources in `research/worlds-live-2026.md`.
- **Pick/ban check:** the app's pick, ban and win counts for all 84 champions match Leaguepedia's Main Event champion statistics (39 games).
- **Out-of-sample (v31 before the update):** favourite 3 of 5, log loss 0.945, Brier 0.334. BLG was 76–90% in all three TES games. Running total: 23 of 39 (59%).
- **Subway band:** caption removed; the band now looks like an aged enamel station sign (grain texture, top white stripe, off-white Helvetica, faded bullets with scuffs, screw heads). CSS only, in `css/styles.css`.
- Cache v31 → v32. How checked: local server in a new browser-pane tab at desktop and 375 px, console clean, data counts and H2H read in the console, role-page game log for 369 renders with the missing CS@15 shown as a dash. The temporary `.claude/launch.json` was removed afterwards.
- Download link for the Oracle's Elixir file is now in the Sources section of `research/worlds-live-2026.md`.
- Committed `4fe2ab1` and pushed.
- **v33, Counters row:** champion page cards (`champCard`) and the hover card (`champTip`) now show "Counters": 3 champions this one beats (`beats3` in `js/core.js`). Order: same-lane METAsrc matchups at 50.5%+ (so the shown % rounds to 51%+), then other-lane matchups, then lane opponents it beat at Worlds; only champions seen in pro play (`POOL`). Example: Nocturne shows Rengar 55%, Locke 54%, Qiyana 54%. Champions with no qualifying matchup show "no matchup data" (27 of 163 before the 50.5% cut-off; not recounted after it). How checked: local server in a new browser-pane tab, every pool champion's row checked in the console (none at 50% or below), all 15 jungle cards show the row, hover card renders, a Counters chip opens that champion's hover card, 375 px with no sideways scroll, console clean. Committed `7b3c221`.

---

## Session index

| Session | Summary |
|---|---|
| 20–27 Oct 2026 (claude.ai chats) | App built from v20 to v30 (see `git log`): player and champion cards, tournament, series mode, real Worlds data, power rankings, themes. Sim back-tested on 711 series (22 Oct). Sim plan written 27 Oct. No notes file then |
| 29 Oct 2026 | CLAUDE.md, SESSION_NOTES.md and the build script added; sim plan decisions recorded (ratings, draft AI, draft review, old engine, minor leagues, scorecard). No app change (v30) |
| 29 Oct 2026 (later) | v31: Subway and Arcade Smash themes, role-page game log hover, ticker fix, side-coloured pick/ban tags, Swiss round 4 day 1 data |
