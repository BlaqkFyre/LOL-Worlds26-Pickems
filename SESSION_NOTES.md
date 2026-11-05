# Pick'Em Lab — session notes

_Live state only. Rules, start/end-of-session steps and the code map are in `CLAUDE.md`. The simulator plan's master copy is `research/sim-plan.md` (link to it here, don't copy it). Keep full blocks for the last 3 sessions; older ones go to the Session index as one line each._

---

## Where we are

- **App:** v40 (5 Nov 2026 AEST, evening): quarter-final 2 (GEN 3–0 LYON) added from the newer Oracle's Elixir file. v39 (5 Nov): quarter-final 1 (IG 3–1 TES). v38 (2 Nov): Swiss round 5. App data and code are correct as they stand.
- **Real data:** the whole Swiss stage (51 games) and quarter-finals 1–2 (7 games), 58 games in `js/worlds-live.js` (data to 4 Nov US), every game confirmed against the Oracle's Elixir file. H2H in `js/h2h.js` (data to 4 Nov 23:54 UTC). Quarter-finals 3–4 on 5–6 Nov (US).
- **Time zones:** Luke's dates are AEST; Worlds game days are US dates; the Oracle's Elixir file is UTC. Check a game's UTC time against the file before saying it has been played.
- **Sim engine:** session 1 (ratings and who-wins model) **done**: report `research/sim1-report.md`. Decisions in `research/sim-plan.md`; scripts and notes in `research/sim1/` (start with its README); result tables in `research/model/sim1/`. Session 2 **done 4–5 Nov** (parts 1 and 2; v2 candidate fixed 5 Nov, knockout test running): report `research/sim2-report.md`, working files `research/sim2/` (README), tables `research/model/sim2/`. Session 3 (game-state sim) **built and tested 5 Nov, not committed yet**: report `research/sim3-report.md`, working files `research/sim3/` (README), tables `research/model/sim3/`. Progress tracker (was the scorecard): https://claude.ai/artifact/J6sw8U1HziM7t8PAfKmqSL
- **Draft Game:** Tier 1 built, autosave added 26 Oct. See `Draft Game/draft-card-game-handoff.md`.
- **Where work happens:** Claude Code sessions only. The claude.ai chats that built the app no longer write to the repo.

---

## What's next

| Task | Status/blocker |
|---|---|
| Sim session 1 open items | Experience re-test after the Worlds knockouts; Faker must not stay at a mid rating (S5 72) — resolve through the process (session 2 champion context, experience re-test, how "wins beyond stats" is shared); "wins beyond stats" shown as a team stat; four skills with ~0 weight (top Teamfight, top steadiness, mid Map impact, ADC Damage): keep or swap; S5 card step has no saved script (add to `scales.py` before session 4). Report section 9 |
| Sim session 2 (done 5 Nov) | Done: role-by-role tests, comfort by event, time together, bans and pools, pool depth study (`research/sim2/README.md` steps 7–10). Candidates for who-wins: jungle comfort (big events), time together (jungle–mid, jungle–ADC), jungle pool, ADC champion strength. **Pool added as a card skill** (sim-plan). Then (same day) power curves, comp profile and the draft meta model: done (steps 11–13). Part 2 written up in `research/sim2-report.md` (Part 2 section). v2 candidate fixed 5 Nov (jungle comfort, jungle pool, jungler–mid and jungler–ADC time together; sim-plan). **Next:** session 3 (game-state sim) |
| Knockout test of the v2 candidate (running) | 7 games (IG 3–1 TES, GEN 3–0 LYON): v1 0.453 v candidate 0.469, favourite 5/7 each. Too few to judge; add each new knockout series with `research/sim2/s2_score_candidate.py` |
| When a newer file has the knockouts | **Score the fixed v2 candidate** (`research/model/sim2/v2_candidate.json`, fixed 5 Nov, not to be changed) against v1 on the knockout games only. Also re-test lolalytics synergy at half strength (chosen after seeing the test games, so not yet fair), the experience test, and every session 2 part on the new games |
| Sim session 3 (built 5 Nov, uncommitted) | Prototype sim from 623 gol.gg timelines + the file; held-out scorecard in `research/sim3-report.md` §3. Matches: gold at 15, towers, dragons, side, first-Baron/first-tower team wins, role kill share, first-dragon and Baron timing, endings. Still off: kills +11% (too spread), Barons +8%, souls too often, length +5.5% from 1 Sep. Who-wins 0.650 v v1 0.644 (Worlds 0.675 v 0.646; 0.642 with draft styles off). **Needs Luke:** review, the draft-style decision (open decisions), then a commit |
| Sim sessions 4–5 | After session 3 (see the plan) |
| Add knockouts (quarter-finals 3–6 Nov, semi-finals 7–8 Nov, final 14 Nov, US dates) | QF1 IG 3–1 TES (v39) and QF2 GEN 3–0 LYON (v40) added. Next: QF3–4 when a newer file has them. Running out-of-sample total: favourite 38 of 58. Score each match day with the app before adding. Steps in `research/worlds-live-2026.md` |
| Draft Game next steps | Pick one when wanted (feel tweaks, real data, Tier 2, smarter AI, Bo series); see the handoff file |

**Parked:** Custom tournament (Play → Custom). Planned feature, not being worked on yet (Luke, 29 Oct).

---

## Open decisions (Luke)

- **Draft styles in the game sim** (session 3): they shape timing (pace, siege, who takes objectives) but cost who-wins at Worlds (0.675 with, 0.642 without; v1 0.646). Keep them, drop them, or keep them only for timing that doesn't decide who takes what. Details: `research/sim3-report.md` §3 and §7.
- **Grub taker model** (session 3): doesn't hold from 1 Sep (worse than side only). Simplify to side only, or keep?

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

### Session (5 Nov 2026, AEST, afternoon) — sim session 3: the game-state sim (research only)
- **Plan agreed** (Luke, "yes go ahead", with realism rules: no scripted results, every event a random draw from fitted chances, timing flexible by comp, side, lane priority and jungle choices). Recorded in `research/sim-plan.md` (session 3 entry; uncommitted).
- **Data:** gol.gg game timelines (every kill, tower segment, tower, monster, inhibitor and nexus, plus per-minute gold), 627 games from 12 events since late July; 623 matched to the file by champions and date (winner and length agree in every one). No LPL timelines on gol.gg. The 3 Gen.G v LYON games are after the file's cut-off, so they are not used.
- **Built:** laning fits per role (file), fight / kill / monster / tower-segment / base-push rate fits (timelines), draft styles from games before 1 Sep, and the minute-by-minute engine `research/sim3/s3_sim.py` (seeded; the box score has the `pack()` fields). Calibration only scales strength and lane noise.
- **Held-out results:** see `research/sim3-report.md` (scorecard §3, ablation, real timing §4, open items §7). Tracker: new "Session 3" card (database page version 37).
- **Fixes during the session** (all in the sim3 README): the first pull skipped Bo1s; kill gold split; gold snapshot timing; segments and fights now as bursty as real; base pushes defined by time, which made endings real (37 s from first inhibitor to end v 42 s); first dragon given its own fitted input; calibration on the team gold lead.
- **How checked:** held-out tests on 301 games from 1 Sep and 77 Worlds games (200 sims each); timeline v file match counts; every report number read from the saved outputs. Tracker: stored page read back and its markup checked; not seen rendered (the browser pane needs Luke's sign-in).
- **Draft styles timing-only** (Luke: "use timing for now"; comps should matter by the end): a draft now changes when things happen (both drafts' pace, siege and objective focus), not who gets them. Held-out: sim 0.646 from 1 Sep (v1 0.644), **0.635 at Worlds (v1 0.646)**; styles now help at Worlds (0.642 without). Report and tracker not yet updated with this.
- **Kills and souls checked** (real timelines v sim): extra kills come from slow games running long (real towers fall after won fights: 0.99 segments per minute at even kills, 2.65 at +3); a "net kills this minute" input for towers is fitted and staged (`research/sim3/` patch, not yet run). Dragons swap sides like real games (58.8% v 57.7–60.7% next to the last taker); the like-for-like soul gap is 6 points (50.7% v 44.5%), not 10.
- **v40 (QF2):** GEN 3–0 LYON checked against Leaguepedia (lengths, kills, all champions and bans), scored with the app first (favourite 3 of 3, log loss 0.147; 85% and 96% above the ceiling), added to `js/worlds-live.js` (58 games), `build_from_oe.py` on a scratch copy 58/58 OK, H2H GEN v LYON 8–1, cache v39 → v40. v1 re-run (earlier odds unchanged) and the v2 candidate's knockout score updated (7 games: v1 0.453, candidate 0.469). How checked: local server in a new browser-pane tab; 58 games, H2H and as-of read in the console; all 16 pages render at desktop (1024 px) and 375 px with no sideways scroll; console clean. Server stopped, tabs closed, `.claude/launch.json` removed.
- **Uncommitted:** the v40 files (`index.html`, `js/h2h.js`, `js/worlds-live.js`, `research/model/h2h_2026.json`, `research/model/oe_check.txt`, `research/model/sim2/v1_games.csv`, `research/model/sim2/knockout_score_2026-11-05_qf2.txt`, `research/sim2/README.md`, `research/worlds-live-2026.md`) and the session 3 files (`research/sim-plan.md`, `research/sim3-report.md`, `research/sim3/`, `research/model/sim3/`), `CLAUDE.md`, this file.

### Session (5 Nov 2026, AEST) — sim session 2 part 2, v2 candidate, v39 (QF1)
- **Sim session 2 part 2:** role-by-role tests (41), comfort at big events, player time together, bans, pool depth (Pool added as a card skill), power curves, comp profile, draft meta model (60% of picks/bans in its top 20). Report: `research/sim2-report.md` Part 2; steps 7–15 in `research/sim2/README.md`. Committed `c1eac68`, `5dd1fe7`, pushed.
- **v2 candidate fixed** before any knockout game was in the file (sim-plan; `research/model/sim2/v2_candidate.json`, SHA-256 recorded). Committed `fca556f`, pushed.
- **New Oracle's Elixir file** (to 4 Nov 02:20 UTC): IG 3–1 TES checked against Leaguepedia. v1 re-run: earlier games' odds unchanged. Knockout score so far: v1 0.669, candidate 0.694 (4 games).
- Committed `128822b` (v39) and pushed.
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
| 3 Nov 2026 | Sim session 1 report (`research/sim1-report.md`) and scorecard artifact; app v new team ratings compared via the browser pane. Committed `0ff5d1f` |
