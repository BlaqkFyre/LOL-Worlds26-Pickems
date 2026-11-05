# Pick'Em Lab — session notes

_Live state only. Rules, start/end-of-session steps and the code map are in `CLAUDE.md`. The simulator plan's master copy is `research/sim-plan.md` (link to it here, don't copy it). Keep full blocks for the last 3 sessions; older ones go to the Session index as one line each._

---

## Where we are

- **App:** v39 (5 Nov 2026 AEST): quarter-final 1 (IG 3–1 TES) added from the Oracle's Elixir file. v38 (2 Nov): Swiss round 5. App data and code are correct as they stand.
- **Real data:** the whole Swiss stage (51 games) and quarter-final 1 (4 games), 55 games in `js/worlds-live.js` (data to 3 Nov US), every game confirmed against the Oracle's Elixir file. H2H in `js/h2h.js` (data to 4 Nov UTC). Quarter-finals 2–4 on 4–6 Nov (US).
- **Time zones:** Luke's dates are AEST; Worlds game days are US dates; the Oracle's Elixir file is UTC. Check a game's UTC time against the file before saying it has been played.
- **Sim engine:** session 1 (ratings and who-wins model) **done**: report `research/sim1-report.md`. Decisions in `research/sim-plan.md`; scripts and notes in `research/sim1/` (start with its README); result tables in `research/model/sim1/`. Session 2 **done 4–5 Nov** (parts 1 and 2; v2 candidate fixed 5 Nov, knockout test running): report `research/sim2-report.md`, working files `research/sim2/` (README), tables `research/model/sim2/`. Progress tracker (was the scorecard): https://claude.ai/artifact/J6sw8U1HziM7t8PAfKmqSL
- **Draft Game:** Tier 1 built, autosave added 26 Oct. See `Draft Game/draft-card-game-handoff.md`.
- **Where work happens:** Claude Code sessions only. The claude.ai chats that built the app no longer write to the repo.

---

## What's next

| Task | Status/blocker |
|---|---|
| Sim session 1 open items | Experience re-test after the Worlds knockouts; Faker must not stay at a mid rating (S5 72) — resolve through the process (session 2 champion context, experience re-test, how "wins beyond stats" is shared); "wins beyond stats" shown as a team stat; four skills with ~0 weight (top Teamfight, top steadiness, mid Map impact, ADC Damage): keep or swap; S5 card step has no saved script (add to `scales.py` before session 4). Report section 9 |
| Sim session 2 (done 5 Nov) | Done: role-by-role tests, comfort by event, time together, bans and pools, pool depth study (`research/sim2/README.md` steps 7–10). Candidates for who-wins: jungle comfort (big events), time together (jungle–mid, jungle–ADC), jungle pool, ADC champion strength. **Pool added as a card skill** (sim-plan). Then (same day) power curves, comp profile and the draft meta model: done (steps 11–13). Part 2 written up in `research/sim2-report.md` (Part 2 section). v2 candidate fixed 5 Nov (jungle comfort, jungle pool, jungler–mid and jungler–ADC time together; sim-plan). **Next:** session 3 (game-state sim) |
| Knockout test of the v2 candidate (running) | 5 Nov file: IG 3–1 TES (4 games, checked against Leaguepedia). v1 0.6692 v candidate 0.6935, favourite 2/4 each. Too few to judge; add each new knockout series with `research/sim2/s2_score_candidate.py` |
| When a newer file has the knockouts | **Score the fixed v2 candidate** (`research/model/sim2/v2_candidate.json`, fixed 5 Nov, not to be changed) against v1 on the knockout games only. Also re-test lolalytics synergy at half strength (chosen after seeing the test games, so not yet fair), the experience test, and every session 2 part on the new games |
| Sim sessions 3–5 | After session 2, in order (see the plan) |
| Add knockouts (quarter-finals 3–6 Nov, semi-finals 7–8 Nov, final 14 Nov, US dates) | QF1 IG 3–1 TES added (v39). Next: QF2–4 when a newer file has them. Score each match day with the app before adding. Steps in `research/worlds-live-2026.md` |
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

### Session (5 Nov 2026, AEST) — sim session 2 part 2, v2 candidate, v39 (QF1)
- **Sim session 2 part 2:** role-by-role tests (41), comfort at big events, player time together, bans, pool depth (Pool added as a card skill), power curves, comp profile, draft meta model (60% of picks/bans in its top 20). Report: `research/sim2-report.md` Part 2; steps 7–15 in `research/sim2/README.md`. Committed `c1eac68`, `5dd1fe7`, pushed.
- **v2 candidate fixed** before any knockout game was in the file (sim-plan; `research/model/sim2/v2_candidate.json`, SHA-256 recorded). Committed `fca556f`, pushed.
- **New Oracle's Elixir file** (to 4 Nov 02:20 UTC): IG 3–1 TES checked against Leaguepedia. v1 re-run: earlier games' odds unchanged. Knockout score so far: v1 0.669, candidate 0.694 (4 games).
- **v39:** QF1 scored with the app first (v38: favourite 2 of 4, log loss 0.773; running total 35 of 55), then added to `js/worlds-live.js` (55 games); `build_from_oe.py` on a scratch copy: 55/55 OK, `js/h2h.js` rebuilt (IG v TES 11–11); "Swiss games" wording now "Swiss and knockout games" (ⓘ panel, champion pages, player game log, README). Cache v38 → v39. How checked: local server in a new browser-pane tab; data counts, H2H, Wei/Tian logs and Qiyana's counts read in the console; all 16 pages render at desktop and none scrolls sideways at 375 px; console clean. Server stopped, tabs closed, `.claude/launch.json` removed.

### Session (4 Nov 2026, AEST) — sim session 2, part 1
- **Plan agreed** (Luke, "yes go ahead"): seven parts measured beyond v1, three outside sources per part, data cut-off at the file (no knockouts); Luke's current-meta principle recorded. All in `research/sim-plan.md`.
- **Report:** `research/sim2-report.md`; working files and every number's source: `research/sim2/README.md`; tables in `research/model/sim2/`.
- **Results:** no part beats v1 for who wins (v1 0.6461 from 1 Sep). The meta clearly follows the latest patches (Worlds presence v 16.17 0.91, v 16.01 0.60). Pro lane records on 16.15–16.20 predict the later lane (top 0.30, jungle 0.27); solo-queue counters don't. Sources agree with each other (Leaguepedia = file; METAsrc v lolalytics 0.80).
- **lolalytics read in full:** tier lists (16.11–16.20, from each page's embedded data), lane counters (4 patches, 648 pages) and synergy (88 pages in the browser pane, one real click each; saved by file download with Luke's OK).
- **Mistakes and fixes:** a scaling fault in my patch-test script (fixed, re-run); synergy reading failed until I found it needs a real click.
- **Tracker:** the scorecard artifact is now "Sim Engine Progress" (parts map, progress chart, meta-by-patch chart, lanes and sources tables): https://claude.ai/artifact/J6sw8U1HziM7t8PAfKmqSL. Its own page check did not report back after most updates.
- How checked: session 1 scripts re-run on a scratch copy reproduce every saved result exactly; lolalytics values checked against the page (Yone top 16.20); outside-source comparisons as listed in the report. No app change (v38). Browser tabs closed, temporary lolalytics storage cleared.
- Committed `61609b0` and pushed. Decision at the end (Luke): keep testing who-wins inputs next session, each role tested on its own.

### Session (3 Nov 2026, AEST) — sim session 1 report
- **Report written:** `research/sim1-report.md`, from the saved results in `research/model/sim1/`, `research/sim1/README.md` and `research/sim-plan.md`. Nothing was re-run. Headline: new model 0.639 v app 0.679 log loss on the 51 Swiss games (no drafts); 0.646 from 1 Sep (coin flip 0.693); calibration within 5 points from 1 Sep, 10–12 points off in two Worlds bands (small samples).
- **Scorecard artifact:** https://claude.ai/artifact/J6sw8U1HziM7t8PAfKmqSL (tests, calibration, league strength, 16 team ratings, 80 S5 player cards, open items), built from small CSVs of the same numbers.
- **Found:** the session 1 working files were already committed (`82264c0`), though these notes said otherwise. `research/sim1/experience_progress.md` still says player matching is "not done"; the CSV has all 442 (left as a mid-session note). Several outputs were printed, not saved (per-game app comparison, experience test numbers, `deeper.py`, gol.gg comparison); the report says so.
- **App v new team ratings** (Luke OK'd the read-out): each team's `t.ov` read from the running app (v38) on a temporary local server in a new browser-pane tab, console clean; server stopped, tab closed, `.claude/launch.json` removed. Ranks are close (15 of 16 within 2 places); AL is the exception (app 5th, new 8th). Added to the report (section 3) and the scorecard. Node.js isn't installed, so the planned script couldn't run and the app was used instead.
- `research/sim1/README.md` and the `research/sim-plan.md` status line updated. No app change (v38).
- Committed `0ff5d1f` and pushed.
- Tidy at end of session: `research/sim1/experience_progress.md` marked as a superseded mid-session note; `CLAUDE.md` Files table lists `research/sim1/`, `research/model/sim1/` and the report. Node.js is not installed on this PC, so app values are read through the browser pane (noted in Claude's memory).

---

## Session index

| Session | Summary |
|---|---|
| 20–27 Oct 2026 (claude.ai chats) | App built from v20 to v30 (see `git log`): player and champion cards, tournament, series mode, real Worlds data, power rankings, themes. Sim back-tested on 711 series (22 Oct). Sim plan written 27 Oct. No notes file then |
| 29 Oct 2026 | CLAUDE.md, SESSION_NOTES.md and the build script added; sim plan decisions recorded (ratings, draft AI, draft review, old engine, minor leagues, scorecard). No app change (v30) |
| 29 Oct 2026 (later) | v31: Subway and Arcade Smash themes, role-page game log hover, ticker fix, side-coloured pick/ban tags, Swiss round 4 day 1 data |
| 30 Oct 2026 | v32: Swiss round 4 day 2 (KC–CFO from the file, TES–BLG from Leaguepedia), aged subway sign (`4fe2ab1`); v33: champion card "Counters" row (`7b3c221`) |
| 31 Oct 2026 | v34: Swiss R4 day 3 data (`889b55d`); v35: header and legend tidy-up, ranked team picker (`8359d05`); v36: champ select tidy-ups (`5d53243`); v37: pick/ban board (`bd396b3`). Notes-session overlay saved (`tools/qol-notes-overlay.js`) |
| 2 Nov 2026 | v38: Swiss round 5 data, HLE–G2 confirmed (`b1ed266`); sim session 1 planned, fitted and tested (`c845ba7`, `82264c0`) |
