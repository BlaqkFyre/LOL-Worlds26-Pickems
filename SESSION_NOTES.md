# Pick'Em Lab — session notes

_Live state only. Rules, start/end-of-session steps and the code map are in `CLAUDE.md`. The simulator plan's master copy is `research/sim-plan.md` (link to it here, don't copy it). Keep full blocks for the last 3 sessions; older ones go to the Session index as one line each._

---

## Where we are

- **App:** v50 (14 Nov 2026 AEST): one rating scale for every role, Player of the Game to the top-rated winner. v49: champ select "denies" only players whose role is still open. v48: copy-game-data button after each game. v47: phone end-of-game table, clearer game summary. v46 (13 Nov 2026 AEST, night): the data-built sim runs every game (`js/sim-engine.js` + `js/sim-tables.js`), Player of the Game version C and percentile ratings, sim switch in the ⓘ panel (data model / simpler fights / classic). v45 (10 Nov 2026 AEST): quarter-final 4 (T1 3–1 KC) and both semi-finals (GEN 3–0 IG, BLG 3–1 T1) added from Luke's saved copy of the Oracle's Elixir rows; H2H and pro matchups rebuilt; confirmed against the full file on 11 Nov (every field matches). v44 (6 Nov 2026 AEST): player cards' Worlds records are main-event only too (KC's play-in games listed separately and still in their pools). v43 (6 Nov 2026 AEST): quarter-final 3 (BLG 3–0 DK) added; H2H and the pro matchups table rebuilt from the 6 Nov file; champion cards' Worlds numbers now main-event only (play-ins count as recent pro games). v42 (5 Nov 2026 AEST, night): card chips from pro data (pro records, real Worlds results) get a light tint of the theme accent, so solo-queue fills stand out. v41 (5 Nov, night): champion cards' counters / countered by / pairs now use pro records from patches 26.15+ and Worlds first (`js/pro-matchups.js`), meta champions only (1%+ pick/ban or played at Worlds), solo-queue data only fills gaps. v40 (5 Nov, evening): quarter-final 2 (GEN 3–0 LYON) added from the newer Oracle's Elixir file. v39 (5 Nov): quarter-final 1 (IG 3–1 TES). v38 (2 Nov): Swiss round 5. App data and code are correct as they stand.
- **Real data:** the whole Swiss stage (51 games), the quarter-finals (14 games) and the semi-finals (7 games): 72 games in `js/worlds-live.js` (data to 8 Nov US). Every game is confirmed against the Oracle's Elixir file: the 11 games of 6–8 Nov US, first added from Luke's saved copy, match the full file (11 Nov; 9,904 games to 10 Nov UTC) on every field. H2H in `js/h2h.js` and `js/pro-matchups.js` (data to 9 Nov 00:56 UTC). Final (GEN v BLG) on 14 Nov (US).
- **Time zones:** Luke's dates are AEST; Worlds game days are US dates; the Oracle's Elixir file is UTC. Check a game's UTC time against the file before saying it has been played.
- **Sim engine:** session 1 (ratings and who-wins model) **done**: report `research/sim1-report.md`. Decisions in `research/sim-plan.md`; scripts and notes in `research/sim1/` (start with its README); result tables in `research/model/sim1/`. Session 2 **done 4–5 Nov** (parts 1 and 2; v2 candidate fixed 5 Nov, knockout test running): report `research/sim2-report.md`, working files `research/sim2/` (README), tables `research/model/sim2/`. Session 3 (game-state sim) **done 5 Nov** (beats v1 on held-out games): report `research/sim3-report.md`, working files `research/sim3/` (README), tables `research/model/sim3/`. Session 4 **13 Nov**: refit on all games, JS port, fight players, early kills, first dragon (`bf6cecc`); **the new sim is in the app (v46)**. **14 Nov: redesign started** (actions driven by players, champions and teams; laning slice first; see What's next). Progress tracker (was the scorecard): https://claude.ai/artifact/J6sw8U1HziM7t8PAfKmqSL
- **Draft Game:** Tier 1 built, autosave added 26 Oct. See `Draft Game/draft-card-game-handoff.md`.
- **Where work happens:** Claude Code sessions only. The claude.ai chats that built the app no longer write to the repo.

---

## What's next

**START HERE (written 14 Nov 2026, afternoon AEST): the sim redesign, laning slice first.** App v50 (unchanged since `6cae62d`). Research committed to `d26b50f`.

**Why (Luke, 14 Nov; memory `sim-actions-from-data`):** the v46 data sim takes a few numbers at the start and then draws fitted per-minute rates. Luke wants pre-draft factors (teams, players, meta, champion pools), draft factors (synergies, damage types, comp styles, counters, player tendencies and skill, team meta awareness) and in-game events to drive each action point, so games reflect real data through actions between players, champions and teams. His rules: every behaviour proven by data (Claude sets no behaviour numbers; thin data → find more; data that only leans → ask Luke); success = actions that reflect real data, who-wins accuracy kept inside the noise band; **Worlds games and patch 16.20 first** in every test, the wider 2026 data for lasting factors; tests **day by day at Worlds**; **one slice first, end to end**: the laning phase (0–14:00), with the draft AI's lane tables and death timers for the whole game in the same slice.

**Plan:** `research/laning-plan.md` (inputs, 8 lane actions, tests, worked example IG v TES QF1 game 1, steps 1–6, Luke's answers). **Step 1 (measure the inputs): done 14 Nov**, report `research/laning/step1-report.md` (tables generated from the results):
- **Kept:** champion lane strength (biggest), player lane skill (stable, 0.57–0.73 odd v even), matchup, team strength; who wins early fights (players and champions for the roles in the fight + team strength + lane so far: Worlds log loss 0.689 → 0.661); plates (lane edge, laners just killed, plates already off, grubs); first dragon (strength and lane edges + a Worlds term: red's 2026 dragon edge didn't happen at Worlds); team grubs priority as a trait.
- **Not supported:** comfort and player x champion for lane results (pools go into the draft instead); minor leagues on 16.20; players' gank, roam and solo-kill habits; where ganks and roams go from game state (timelines only record kills; no positions); jungle champion effect on gank pace; lane kill rates barely move (who wins them is the fight model).
- **Luke to decide:** grubs taker (full model helps at Worlds, side only is better on 2026 from 1 Sep); first dragon "kills in the 60 s before" (helps 2026, hurts Worlds).

**Running / next:**
1. **Worlds feed pull** (Luke OK'd 14 Nov): lolesports live stats frames (second-by-second health, gold, CS, level, K/D/A per player; no positions), first 15 minutes of all 94 Worlds games, into `research/local/feed/` (`research/laning/feed_pull.py`; game list `worlds_games.csv` from the lolesports schedule API, which needs the website's public key; the frames feed doesn't). **Done 14 Nov:** all 94 pulled (7 re-pulled after a start-detection fix), matched to the file, clocks set from the gol.gg timelines (91 of 94; 3 have no early kill to align on); `research/laning/s5_feed_analysis.py`, report section 2e. Death timers confirmed (608 deaths, median ratio 1.00 to the wiki). About 18 no-kill lane trades a game, a jungler hit in about 10%. Who wins a single trade is near a coin flip (players and champions don't predict it; level does a little), and early trades add nothing to the lane's gold at 15: the lane model stays at lane-outcome and fight level.
2. Step 2: Luke reviews what survived and the two calls above. Step 3: build the laning module in the research sim (option, off by default, hands over at 14:00). Then test, port (with the draft AI's lane tables and death timers), Luke judges in the app.
3. The final (GEN v BLG, 14 Nov US) when a newer Oracle's Elixir file has it.

**Research system (Luke, 14 Nov: secure, accurate, maintainable, scalable): `research/lib/`** (README there). One config for paths, dates and expected sizes; loaders with checks (stale files refused); leak-checked splits; run records in `research/runs/` (+ `index.csv`); results written only when a run finishes; report tables generated from results (`research/lib/report.py`); value-by-value compare. The six laning scripts run on it (rebuilt results identical, 0 differences). New scripts use it; older ones move when next changed.

**Earlier research still open (research sim only, committed `529caf2`, off by default in `research/sim3/s3_sim.py`):** death timers (`dt`), pushes following dead players and structure timing (`dp`), damage share by player and champion (`dmg_effects`); push size by kills (`pks`/`pko`) made the spread worse. Not done: monsters following fights, games too long with the push changes, early fights too big. These become checks the redesigned sim must pass.

Older "What's next" blocks and the long task table: `SESSION_NOTES_ARCHIVE.md`.

**Local data a new session needs** (git-ignored, on this PC): `research/local/` (README there): gol.gg timelines, held-out sim games, test runs. The Oracle's Elixir CSV in `research/` is the full file to 10 Nov UTC. Sim scripts read these by path; run them from the repo root as in the README examples.

**Parked:** Custom tournament (Play → Custom). Planned feature, not being worked on yet (Luke, 29 Oct).

---

## Open decisions (Luke)

- **Session 4 plan:** OK'd 13 Nov; built into the app 13 Nov (v46).
- **Full tests for lane-level version 3 and the corrected sim,** or accept the short Worlds test? (Report 7l.)
- **Default sim for the app:** chosen 13 Nov (What's next, item 2); the switch goes to baseline + lane-level v2.
- Decided 12 Nov evening: the tower-push phase fix is the sim's default.
- **Ratings and Player of the Game changed 14 Nov (v50; Luke: support ratings too high, the award should follow in-game performance; "choose the best tested one"):** rating = percentile of the award model's full score (with its role term) among real games of every role; the award goes to the top-rated winner, no draw. Held-out award games from 1 Sep: right 52% v 41% for the draw (`research/sim4/pog_options_test.py`). Cost: supports win about 1–2% of awards in real-data replays, 7% in the sim, v 10% real.
- **Player of the Game and per-game ratings: version C built into the app (Luke, 13 Nov: "build C in this step"; v46).** Refit on every award to 10 Nov (`research/sim4/s4_pog.py`, `research/model/pog/pog_app.json`); rating = percentile among real major-league games in the role ÷ 10; the award is drawn among the winning five. Agreed in principle 6 Nov (`research/sim-plan.md`, decision 6): Player of the Game from a model fitted on LPL / LCS / First Stand per-game awards, tested and extended with series awards (LCK, LEC and the rest); per-game rating = percentile of that fitted score among real pro games in the role ÷ 10, replacing today's hand-set formula. Award data, scripts and results: `research/pog/` (README) and `research/model/pog/`. **Refit (6 Nov, sim's stats only):** both fitted models beat today's formula on every held-out check (e.g. LCS + First Stand games, never fitted: right pick 59% v 49%, log loss 1.09 v 1.21; LCK series: 48% v 42%). Adding series awards as training is a wash so far; **Luke chose version C (with series awards), 6 Nov.**
- **Lane × tier tower pushes: decided 7 Nov (Luke): keep it in the sim and keep testing it.** **Done 11 Nov (start of session 4):** it is the sim's default (`s3_sim.py`; `s3_test.py ... nolt` runs the earlier sim: checked, 0.6348 / 0.6260, all 60,800 games identical to the 6 Nov `out_t_base` run). Baseline re-run `research/local/sim3/out_s4_base`: 0.6385 from 1 Sep (304 games), 0.6173 at Worlds (80 games), all 60,800 simulated games identical to the 10 Nov `out_7g_lt` run (458 s). The 7g comparisons already used this baseline (report 7i). More realistic lane by lane and better on held-out pushes; who-wins mixed (0.639 v 0.635 from 1 Sep, 0.617 v 0.626 at Worlds); doesn't narrow the spread. Details: `research/sim3-report.md` 7f; switch `cal["seg_lane_tier"]` / `s3_test.py ... lt`, off by default.
- **Player cards and play-in games:** see What's next.

Decided 6 Nov (details in `research/sim-plan.md`, "Five decisions before session 4"): keep all three draft styles and keep validating (siege and scaling against late-game timing; champion-to-style fit from outside labels); keep the grub taker model (let the engine play it out); no "one damage type" warning — a champ-select meter for magic / physical damage (maybe tankiness, CC / utility) instead, and the draft AI judges comps; v1 is the baseline and the final model must beat it.

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
| Player of the Game: checked 6 Nov (see Open decisions). LPL per-game awards on Leaguepedia are complete for Split 3; LCK and Worlds are per series; Worlds main event has only 12 of 36 series filled | Luke chooses the source for session 4 |
| Old sim overrates BLG against TES (76–90% in all 3 games, TES won 2-1); the ceiling issue keeps showing | The new sim (sim sessions 1–4) |
| `build_from_oe.py` labels every "WLDs" row as "Worlds" in the H2H "Met at" list, including the 17–19 Sep qualifier rows its own header says aren't Worlds. Game counts aren't affected | Before the script becomes the match-day routine (sim session 5) |
| `build_from_oe.py` always overwrites `js/h2h.js` and `js/worlds-live.js`; an option to write to another folder would make test runs safer | Same as above |
| How Swiss round 4 splits across 28–30 Oct is assumed in `js/tournament.js` (`DAYS`). Leaguepedia now publishes it: 2 series a day (28: MKOI–T1, IG–LYON; 29: KC–CFO, TES–BLG; 30: TL–LOS, HLE–G2). The days in `DAYS` match; how the code assigns series to days was not checked | Check when convenient |
| Old sim quirks, left alone: odds use 300 runs (tournament), 600 (draft review) or 1500 (series); supports' CS diff is scaled by 0.3 twice in `gameStats` | If the old engine becomes a simple mode, decide with Luke whether to tidy these |

---

## Recent updates

### Session (13–14 Nov 2026, AEST) — app v47–v50, spread research, ratings and Player of the Game, then the sim redesign (laning slice, research library)
- **App, all committed and pushed:** v47 phone end-of-game table fits 375 px, clearer "This game" summary tables (`f53e4a2`); v48 "Copy game data" button beside the next-game button, text for pasting into chat (`539f14b`); v49 champ select: ban and pick reasons and the draft review's "bans hit" / "denied" count a player only while their role is open, flex champions count every open role (`f25680e`); v50 one rating scale for all roles, Player of the Game to the top-rated winner (`6cae62d`; test in Open decisions). Before: supports reached 8+ in 14% of sim games; after: 4% (480 games), the award is always the top-rated winner.
- **Spread research (research sim only, options off by default, replay checks identical with options off; uncommitted):**
  - Death timers from the League wiki Respawn and Experience pages (read 14 Nov) and Riot's patch 14.16 notes, levels from the file's XP at 10/15/20/25 (`research/sim4/s4_deathtimer.py`, `deathtimer_check.py`): real re-deaths inside the timer 0.0% of 3,849; sim 10.2% → 0.5% with timers.
  - Pushes after deaths and structure timing (parts B and C, `s4_deadpush.py`): short games 10% → 5% (real 2.6%), a structure within 60 s of an ace 39% → 65% (real 82%; earlier figure 75% in another measure), 0 s gaps between structures 61% → 8% (real 0.9%). But games got longer (median 35.8 v real 32.0 min; sd 8.3 v 5.6) and the Nexus falls with an own kill in the last 60 s only 38% (real 99.6%).
  - Push size by kills (`pks`/`pko`): worse spread, kept off. Early fights: 6+ kill fight before 10:00 real 1.3%, sim 2.4–2.8% (`early_fights_check.py`). Damage share by player and champion (`s4_dmgshare.py`, `dmgshare_check.py`): held-out error 0.00295 → 0.00212; in the research sim only.
  - Worlds who-wins (94 games, 1,000 sims): default 0.6041, + timers 0.6069, + timers, pushes, timing 0.6054, all inside the noise band, all ahead of v1 (0.6173).
- **Explained for Luke:** TSW's upset of T1 (draft gave TSW 19.4%; game turned on an 18:39 fight and Baron), and the issues in a pasted GEN v T1 game.
- **Luke's feedback at the end:** the sim should be driven by causes (see What's next, START HERE).
- **How checked:** every app change in a new browser tab, console clean, desktop and 375 px (v47 across 60+ games; v50 by measuring table widths, pane hidden so no screenshots); server stopped and `launch.json` removed. Research: replay checks with options off, held-out fits, short Worlds tests at 1,000 sims with seeds by game ID.
- **Committed:** the spread research (`529caf2`, pushed).
- **Afternoon (14 Nov): sim redesign started** (see What's next). Plan `research/laning-plan.md`; step 1 measured and reported (`research/laning/step1-report.md`); answered Luke's HLE v DK bot lane question from the lane model (close to even, HLE +130 gold at 15: Smash the stronger player, Xayah the stronger lane champion); lolesports feed found and checked (no positions; second-by-second health etc.), Worlds pull running; `research/lib/` built and the six laning scripts moved onto it (results identical); notes trimmed (old blocks to `SESSION_NOTES_ARCHIVE.md`); disk space: Claude temp files deleted, finished research run folders zipped (`research/local/README.md`). Commit `d26b50f` (pushed).
- **How checked (afternoon):** every test held out (Worlds day by day, 2026 from 1 Sep), settings chosen on training games only; rebuilt scripts compared value by value with the earlier results (0 differences in 6 files); feed checked against the gol.gg timeline for one game.

### Session (13 Nov 2026, AEST, night) — the data-built sim in the app (v46)
- **Luke OK'd the wiring plan** (switch in the ⓘ panel) and asked for Player of the Game version C in the same step.
- **Tables:** refits on all games for the app (fight players, early-window fight types, first-dragon taker; `research/local/sim4/app_params/`), both versions calibrated (default gain 1.597, simpler fights 1.571; `research/local/sim4/app_cal/`), `js/sim-tables.js` built by `research/sim4/s4_tables.py` (now with `--pog`).
- **Player of the Game version C** (`research/sim4/s4_pog.py`): the pre-1 Sep refit reproduces `pog_fit.json` (largest gap 0.0005); the app's fit uses every award to 10 Nov (977 per-game award games, 631 series); rating = percentile among 5,732 real major-league games per role ÷ 10. On real games from 1 Sep: winners 6.70, losers 3.28.
- **App (v46, 12 cache tags):** `simGame()` runs the data sim (classic kept as `simGameOld`, behind the switch, stored in `lolw26-sim`); draft review "before" = v1, "after" = 600 data-sim games; result screen: gold at 15 by lane, expected gold at 15 and pre-draft odds "on paper", "Last fight" (not "Decided") for data games, play-by-play from the sim's events with real times (every kill named, a fight's kills on one line, assists not named); `pack()` unchanged except `g15`. Engine now records each fight (no change to random draws). ⓘ text rewritten. `worlds-live.js` header fixed.
- **How checked (browser pane, new tab, console clean, server stopped, `launch.json` removed, test run and switch cleared from localhost storage):** browser inputs v the Python builder for KC v T1 (QF4 game 1): within 0.016 gold (table rounding), styles exact; GEN v IG v1 75.4%; 400 games (ratings and award shares above, 0.9 ms a game); a full simulated tournament (40 matches, 82 games, awards, saved run passes `sanitizeRun`); classic and simpler-fights games; 375 px: no sideways scroll. Not checked: screenshots (pane hidden), Worlds themes and light mode.
- **Luke, 13 Nov:** improvements from here come from his testing of the app together with the data and future tests.

### Session (13 Nov 2026, AEST) — session 4 started: refit on all games, JS port, fight players, early kills, first dragon
- **Session 4 plan OK'd (Luke).** Step 1: refit of every sim table on all games before 10 Nov UTC, two passes (pass 2 on v1 with player weights refitted on all games and the league adjustment refreshed to 10 Nov; Luke). Worlds odds move 1.3–1.7 points on average. Step 2 read (v1's parts, every field `simView` / `gameStats` / `pack` read, history inputs; history tables sized). Tables script `research/sim4/s4_tables.py` written (self-check on the worked example: 16 of 16 inputs match).
- **JS port** `js/sim-engine.js` (not loaded by the app yet): with the same random stream it plays every Python game identically (14,400 of 14,400 across all options); about 0.5 ms a game.
- **Luke's decisions:** default sim (see What's next); history tables from real games only, never updated by a run; play-by-play from the sim's events, every kill narrated, assists not named; an assist only goes to a player in the fight; his game-flow notes are a reference, data and tests decide, ask before changing code from them.
- **Built and tested (sim options, off by default in the research sim):** fight players (`research/sim4/s4_participants.py`), lane-aware early kills, early fight counts, event order, the first dragon's own taker (`s4_firstdragon.py`). Default + all of these: Worlds who-wins 0.6041 (old default 0.6022; noise band 0.6013–0.6069 measured from three seedings); early kills, lane leads at 10 and first dragon v bot lane much closer to real.
- **Checks of Luke's notes** (`research/sim4/notes_check.py`, `notes_followup.py`): most of the early-game timeline matches the data; ADC damage share rises in long games, Elder decides long games, first Baron less so; comp type doesn't set game length and a scaling score doesn't change fights at any time (`test_scaling_time.py`); first dragon follows side and bot-lane gold.
- **Slip found and fixed:** new diagnostic scripts first gave every game the same seeds (lane draws shared across games); fixed to seeds by game ID and rerun. `s3_test.py` never had this.
- No app change (v45). Commit `bf6cecc`, pushed.
- **How checked:** replay checks after every sim edit (648 of 648 with new options off); JS v Python identical on the same random stream (browser pane, new tab, console clean, server stopped and `launch.json` removed each time); held-out log loss for every fit; short Worlds tests at 1,000 sims with seeds by game ID; one full fixed test (321 games).

---

## Session index

| Session | Summary |
|---|---|
| 11–12 Nov 2026 | Both tests at 1,000 sims (7j), lane-level play version 2 and plates by lane (7k, 7l), spread diagnostics, tower-push fix made default, session 4 plan drafted (`1fe0146`, `fad5320`, `4164e4b`) |
| 10–11 Nov 2026 | Sim spread research (7g), tower context (7h), two-test rule, full Oracle's Elixir file confirms the 11 knockout games (`974b30e`) |
| 7–10 Nov 2026 | v45: quarter-final 4 and both semi-finals from Luke's saved copy (`cbc228f`); local data folder (`research/local/`); tower context research started (`574dd6a`, `49a529d`) |
| 20–27 Oct 2026 (claude.ai chats) | App built from v20 to v30 (see `git log`): player and champion cards, tournament, series mode, real Worlds data, power rankings, themes. Sim back-tested on 711 series (22 Oct). Sim plan written 27 Oct. No notes file then |
| 29 Oct 2026 | CLAUDE.md, SESSION_NOTES.md and the build script added; sim plan decisions recorded (ratings, draft AI, draft review, old engine, minor leagues, scorecard). No app change (v30) |
| 29 Oct 2026 (later) | v31: Subway and Arcade Smash themes, role-page game log hover, ticker fix, side-coloured pick/ban tags, Swiss round 4 day 1 data |
| 30 Oct 2026 | v32: Swiss round 4 day 2 (KC–CFO from the file, TES–BLG from Leaguepedia), aged subway sign (`4fe2ab1`); v33: champion card "Counters" row (`7b3c221`) |
| 31 Oct 2026 | v34: Swiss R4 day 3 data (`889b55d`); v35: header and legend tidy-up, ranked team picker (`8359d05`); v36: champ select tidy-ups (`5d53243`); v37: pick/ban board (`bd396b3`). Notes-session overlay saved (`tools/qol-notes-overlay.js`) |
| 2 Nov 2026 | v38: Swiss round 5 data, HLE–G2 confirmed (`b1ed266`); sim session 1 planned, fitted and tested (`c845ba7`, `82264c0`) |
| 3 Nov 2026 | Sim session 1 report (`research/sim1-report.md`) and scorecard artifact; app v new team ratings compared via the browser pane. Committed `0ff5d1f` |
| 4 Nov 2026 | Sim session 2 part 1: seven parts measured beyond v1 (none beats it), lolalytics read in full, tracker artifact "Sim Engine Progress". Committed `61609b0` |
| 5 Nov 2026 | Sim session 2 part 2 (role tests, comfort, time together, bans, pool depth, curves, comp profile, draft meta model), v2 candidate fixed (`fca556f`), v39 quarter-final 1 IG 3–1 TES (`128822b`) |
| 6 Nov 2026 | v43 QF3 BLG 3–0 DK (`1b6fa86`); v44, champion and player cards' Worlds data main-event only (`b385a55`); six session-4 decisions and Player of the Game research, version C (`5d160a0`, `f48ee88`); spread research 7e, 7f (`0d56f31`, `574dd6a`); rule: no hand-set numbers; local data folder |
| 5 Nov 2026 (afternoon–evening) | Sim session 3: the game-state sim built from 623 gol.gg timelines, beats v1 on held-out games (report `research/sim3-report.md`); v40 QF2 (`00de9ce`), v41 pro matchups on cards, v42 pro chip tint; research `47f379f`, `446d364` |
