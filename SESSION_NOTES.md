# Pick'Em Lab — session notes

_Live state only. Rules, start/end-of-session steps and the code map are in `CLAUDE.md`. The simulator plan's master copy is `research/sim-plan.md` (link to it here, don't copy it). Keep full blocks for the last 3 sessions; older ones go to the Session index as one line each._

---

## Where we are

- **App:** v41 (5 Nov 2026 AEST, night): champion cards' counters / countered by / pairs now use pro records from patches 26.15+ and Worlds first (`js/pro-matchups.js`), meta champions only (1%+ pick/ban or played at Worlds), solo-queue data only fills gaps. v40 (5 Nov, evening): quarter-final 2 (GEN 3–0 LYON) added from the newer Oracle's Elixir file. v39 (5 Nov): quarter-final 1 (IG 3–1 TES). v38 (2 Nov): Swiss round 5. App data and code are correct as they stand.
- **Real data:** the whole Swiss stage (51 games) and quarter-finals 1–2 (7 games), 58 games in `js/worlds-live.js` (data to 4 Nov US), every game confirmed against the Oracle's Elixir file. H2H in `js/h2h.js` (data to 4 Nov 23:54 UTC). Quarter-finals 3–4 on 5–6 Nov (US).
- **Time zones:** Luke's dates are AEST; Worlds game days are US dates; the Oracle's Elixir file is UTC. Check a game's UTC time against the file before saying it has been played.
- **Sim engine:** session 1 (ratings and who-wins model) **done**: report `research/sim1-report.md`. Decisions in `research/sim-plan.md`; scripts and notes in `research/sim1/` (start with its README); result tables in `research/model/sim1/`. Session 2 **done 4–5 Nov** (parts 1 and 2; v2 candidate fixed 5 Nov, knockout test running): report `research/sim2-report.md`, working files `research/sim2/` (README), tables `research/model/sim2/`. Session 3 (game-state sim) **done 5 Nov** (beats v1 on held-out games): report `research/sim3-report.md`, working files `research/sim3/` (README), tables `research/model/sim3/`. Progress tracker (was the scorecard): https://claude.ai/artifact/J6sw8U1HziM7t8PAfKmqSL
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
| Sim session 3 (done 5 Nov) | Minute-by-minute sim from 623 gol.gg timelines + the file (`research/sim3-report.md`). Held out: who-wins 0.635 v v1 0.640 from 1 Sep, 0.626 v 0.628 at Worlds; length, kills, towers, dragons, souls, gold at 15, role kill share match real averages. **Open:** game-to-game spread too wide (length sd 7.0 v 5.6, kills sd 12.4 v 7.3; next test: a per-game tempo), Barons a little low (88% of games v 97%), first-Baron team wins 78.5% v 84.4%, draft styles slightly costly in the final version. Comps options and tests: `research/comps-plan.md` (A and C tested, not kept) |
| Player choice moments (parked, Luke 5 Nov: "come back to player choices and how that may provide variety, based on data and realism") | Measured 5 Nov (`research/sim3-report.md` 7b): ganks and roams go with outcomes inside games but aren't stable player habits and don't predict held-out games; farming is a stable habit in every role (0.58–0.71) but adds nothing to who-wins or jungle objectives (tested 5 Nov, not kept; small top-lane gold-at-15 lead to test inside the lane model). Next when picked up: state-driven choice moments in the sim (chances from the timelines, depending on game state) |
| Sim sessions 4–5 | After session 3 (see the plan) |
| Add knockouts (quarter-finals 3–6 Nov, semi-finals 7–8 Nov, final 14 Nov, US dates) | QF1 IG 3–1 TES (v39) and QF2 GEN 3–0 LYON (v40) added. Next: QF3–4 when a newer file has them. Running out-of-sample total: favourite 38 of 58. Score each match day with the app before adding. Steps in `research/worlds-live-2026.md` |
| Draft Game next steps | Pick one when wanted (feel tweaks, real data, Tier 2, smarter AI, Bo series); see the handoff file |

**Parked:** Custom tournament (Play → Custom). Planned feature, not being worked on yet (Luke, 29 Oct).

---

## Open decisions (Luke)

- **Draft styles in the game sim** (session 3): now timing-only (Luke, 5 Nov). In the final version they cost a little (0.635 with v 0.632 without from 1 Sep; 0.626 v 0.617 at Worlds); only draft pace → kills per minute is clearly real in held-out games. Keep all three, or keep only pace? (`research/sim3-report.md` §4)
- **The app's "one damage type, easy to itemise against" hover-card warning** is untested (pro teams never draft one damage type; `research/comps-plan.md` option C). Remove, reword or keep, in session 4.
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

### Session (5 Nov 2026, AEST, afternoon–evening) — sim session 3: the game-state sim; v40 (QF2)
- **Plan agreed** (Luke, "yes go ahead", with realism rules: no scripted results, every event a random draw from fitted chances, timing flexible by comp, side, lane priority and jungle choices). Later decisions (sim-plan session 3 entry): draft styles timing-only for now, comps to matter by the end; no effect from AI assumptions (test first with outside labels and held-out data).
- **Data:** gol.gg game timelines (every kill, tower segment, tower, monster, inhibitor and nexus, plus per-minute gold), 627 games from 12 events since late July; 623 matched to the file by champions and date (winner and length agree in every one). No LPL timelines on gol.gg.
- **Built:** laning fits per role (file); fight, kill, monster, tower-push and base-push fits (timelines); draft styles from games before 1 Sep; the minute-by-minute engine `research/sim3/s3_sim.py` (seeded; box score has the `pack()` fields). Calibration only scales strength and lane noise.
- **Final held-out result** (304 games from 1 Sep, 80 Worlds, 200 sims each): who-wins 0.635 v v1 0.640 and 0.626 v 0.628; length 32.1 v 32.3 min, kills 27.3 v 26.9, towers, dragons, souls, gold at 15 and role kill share match. Open items: report §8.
- **Fixes on the way** (all in the sim3 README and report §7): Bo1s missing from the first pull; kill gold split; gold snapshot timing; bursty counts; base pushes defined by time (endings now real); first dragon's own input; team-lead calibration; won fights feed tower pushes; **tower pushes** (the T2 → T3 stage dragged; median game end 35:01 → 31:25, real 31:59).
- **Research:** real timing facts (first dragon to red 62%, to the bot + jungle leader 65%; half of Barons right after a won fight; 38% of T3s fall in the same push as the T2); kills and souls checked (dragons swap sides like real games); comps option A (a comp converts a lead) and option C (damage type, frontline; Riot client tags via the League wiki) tested and not supported; `research/comps-plan.md`.
- **v40 (QF2):** GEN 3–0 LYON checked against Leaguepedia, scored with the app first (favourite 3 of 3, log loss 0.147; 85% and 96% above the ceiling), added (58 games), H2H GEN v LYON 8–1, v1 re-run and knockout score (7 games: v1 0.453, candidate 0.469). How checked: new browser-pane tab, all 16 pages at desktop and 375 px, console clean. Committed `00de9ce` and pushed.
- **v41 (Luke: cards should show meta champions and lean on pro data, not solo queue):** new `research/build/build_pro_matchups.py` → `js/pro-matchups.js` (776 pro games on 26.15+ to 4 Nov: 136 champions, 736 lane matchups, 1,597 pairs; 60 KB). `counters5` / `beats3` / `pairs5` rewritten: pro records first (main roles only; short records pulled toward 50%), then Worlds, then METAsrc / metabot to fill gaps (marked "solo queue" in the hover note); a pro-recorded opponent or partner is never re-added from weaker data; meta = 1%+ pick/ban on 26.15+ or played at Worlds (109 champions). ⓘ panel, README and CLAUDE.md updated; cache v40 → v41 (10 tags). How checked: new browser-pane tab on a local server; all 163 champion cards render, 0 off-meta entries, 0 contradictions with pro records; Orianna's card v the file (Cassiopeia 6–11, −363 at 15) and Cassiopeia's mirror (Orianna 11–6); all 16 pages at 1024 px and 375 px, no sideways scroll; console clean. Server stopped, tab closed, `.claude/launch.json` removed.
- **More research (uncommitted):** player choice moments (parked), farming habit for every role (not kept), session 2 inputs v in-game events for every role and pair (only the bot lane holds up) — report 7b and 7c.
- **How checked (sim):** every report number read from the saved outputs; held-out tests as above; tracker page read back after writing (not seen rendered: the browser pane needs Luke's sign-in).

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
