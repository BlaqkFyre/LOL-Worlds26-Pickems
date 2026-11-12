# Pick'Em Lab: data-built game simulator plan

Written 27 Oct 2026. Status: **session 1 done** (3 Nov 2026 AEST; report `research/sim1-report.md`); **session 2 part 1 done** (4 Nov; report `research/sim2-report.md`): no who-wins gain yet, meta and pro lane findings; part 2 (power curves, comp profile, draft meta model) next. The live copy (with a diagram) is the Claude doc of the same name; this is the repo copy.

## How we got here

- **26–27 Oct:** Luke asked whether the simulator is real maths or "a faux simulation based on guesses, estimates and manufactured randomness".
  - Honest answer: it is a probability model that rolls dice, and only part of it comes from data.
  - **Fitted:** the team strength scale (`SIMK`), fitted to 711 real 2026 series (`research/backtest-2026.md`), plus checks on game length, first-Baron and first-Elder win rates, and POG shares by role.
  - **Set by hand:** most of the inner workings — fight sizes, gold swings, kill counts, the late-game constants (`LATE`), the POG formula weights and the star bonuses — chosen and adjusted until those checks matched.
  - Randomness itself is fine (real games are uncertain, and showing one game means drawing from the odds). The weak part is that the *shape* of the randomness comes from estimates, not data.
- **Evidence from real Worlds games:**
  - Across the real Swiss games scored before their data was added, the favourite won 17 of 29 (59%).
  - On 26 Oct the favourite won 2 of 6, with log loss 0.676, roughly a coin flip.
  - The misses were rating problems: AL was rated too high; TL and LOS too low.
  - The simulator also produced about 20% too few kills: 20.4 per game against 25.6 in real games. Length, objectives and kill share by role were close.
- **Luke's direction:** build a real game simulator from data — real results, champion data, game results, MVP results, tournament and domestic results, player strengths, with champion/meta/player synergies and counters — that plays out kills, CS, objectives, turrets, momentum and comp types (siege, dive and so on).
- **Data:** Luke added `research/2026_LoL_esports_match_data_from_OraclesElixir.csv`. It is kept local via `.gitignore` because it is 79 MB.
  - It was checked against all 29 Worlds Swiss games: every champion and K/D/A matched.
  - It supplied the missing 26 Oct bans, which matched the Reddit post-match threads Luke pasted.
  - It corrected two game lengths: IG–GEN 26:01 and TSW–IG 30:20.
- **Luke chose to write the full plan before building.** Rule agreed along the way: no double counting — each game is counted once, by game ID, across this file, `js/worlds-live.js` and the NerfPlz tables.

## Goal

Replace the hand-tuned simulator with one where every chance in a game is measured from real 2026 pro games, and prove it with a scorecard after each match day.

What stays the same for the player:

- You still draft, sim games and series, and run a whole tournament.
- Games still play out minute by minute with kills, CS, towers, dragons, Barons, momentum and a Player of the Game.

What changes:

- **Where the numbers come from.** Fight odds, objective odds, gold swings, comeback chances and POG weights are fitted to real games, not chosen by hand.
- **Ratings come from results.** Team and player strength are fitted from domestic and international 2026 results, so league strength is measured. This targets misses like AL (rated too high) and TL and LOS (too low).
- **Drafts matter by a realistic amount.** Comp type (siege, dive, scaling, skirmish), synergies and counters shift the odds by what the data supports, usually a few percent.
- **It can be checked.** Every match day gets an out-of-sample scorecard, and the same seed replays the same game.

## The data

The Oracle's Elixir 2026 file matches every real Worlds Swiss game already in the app, player by player.

| What | Value |
| --- | --- |
| Games, all leagues | 9,818 (1 Jan to 26 Oct 2026) |
| Games, major leagues and internationals | 2,835 (LPL 674, LCK 502, LEC 383, CBLOL 299, LCS 283, LCP 283, EWC 232, MSI 71, Worlds 63, First Stand 45) |
| Players / teams / champions (major) | 440 / 71 / 156 |
| Per game | sides, picks, bans with order, length, result, kills, towers, plates, dragons by type, Elder, grubs, Herald, Baron, inhibitors |
| Per player | K/D/A, CS, gold, damage and damage share, vision, and gold, XP, CS, kills, deaths at 10, 15, 20 and 25 minutes |
| Completeness | 98% of rows complete; gold at 15 present in 95% of major-league games; bans in 100% |

Not in the file: Player of the Game, and minute-by-minute event timelines beyond the 10/15/20/25 snapshots. POG needs a separate source (session 4).

Note: the file's "WLDs" rows dated 17–19 Sep are not Worlds games (they look like a regional qualifier) and must be excluded. Worlds play-ins are 15–18 Oct; Swiss starts 23 Oct (UTC dates in the file run a few hours ahead).

**No double counting.** Real Worlds games now exist in two places: `js/worlds-live.js` and the file's Worlds rows. From session 1, each game is counted once, matched by its game ID, with the file as the source of record once it covers a day. The same rule applies to the NerfPlz patch tables the champion cards use, which already include Worlds play-in games.

## How the model fits together

Two fitted foundations feed both a who-wins model and a game-state simulator; the simulator must agree with the who-wins model before anything ships.

```
            2026 game data (Oracle's Elixir + real Worlds games)
                 |                                   |
     Team and player ratings              Champions and comps
     (league strength, player             (power curves, siege/dive/scaling,
      edges shrunk to average)             comfort, synergies, counters)
                 \___________________________________/
                 |                                   |
          Who-wins model  ----- calibrates ---->  Game-state simulator
     (win chance from ratings,             (each step: lane gold, fights,
      draft and side; tested on             objectives, towers, Baron,
      games it has not seen)                Elder, game end)
                 |                                   |
        Match-day scorecard                 Player of the Game model
                                                     |
                                                  The app
```

- **Team and player ratings.** Team strength with a league term (international games link the leagues). Player edges per role from gold and XP at 15, kill participation, damage share and deaths, pulled toward the role average when a player has few games.
- **Champions and comps.** Each champion's power curve (gold lead at 10/15/20/25, win rate by game length) and its profile: siege, teamfight, pick or scaling, learned from what teams actually did with it. Player–champion comfort, and synergy and counter adjustments that start from solo-queue data and move only as far as pro results support.
- **Who-wins model.** A logistic model of win chance from the rating gap, the draft adjustments and side. Small and testable; this is the yardstick.
- **Game-state simulator.** Steps through the game with a state of gold and XP lead, kills, towers per lane, dragons by type and soul point, grubs, Herald, Baron and Elder timers. Each event's chance is a fitted function of that state plus the players and comps involved, so momentum and comebacks come from the data. Its overall win odds are tuned to match the who-wins model.
- **Player of the Game.** A model that picks among the winning side's players from their simulated box score, with weights learned from real awards.
- **Randomness.** Each event is a draw from its fitted chance, from a seeded generator, so the same seed replays the same game.

## Sessions

Five sessions, each ending with something you can check before the next starts; the app only changes in session 4.

1. **Ratings and the "who wins" model**
    - Clean the file: map team and player names to the app's IDs, keep major leagues and internationals, flag roster changes.
    - Fit team ratings with a league-strength term, using international games (First Stand, MSI, EWC, Worlds) to link the leagues.
    - Fit player ratings per role from lane gold/XP at 15, kill participation, damage share and deaths, pulled toward the role average for players with few games.
    - Build the win-probability model (ratings + side), train on games before 1 Sep, test on games after.
    - Deliverable: a research report with the test scorecard and a table of new vs current team ratings.
2. **Champions, comps, synergies and counters**
    - Champion power curves: average gold lead at 10/15/20/25 and win rate by game length.
    - Comp profile per draft: early vs late, siege (early towers and plates) vs teamfight (objective fights) vs pick (kills), learned from what teams with each champion actually did.
    - Player–champion comfort from games played and results on that champion.
    - Synergy and counter adjustments: solo-queue (METAsrc) values as the starting point, adjusted only as far as pro results support.
    - **Matchup grid (Luke, 31 Oct):** a champion-by-champion grid (row champion's record against column champion), per role plus "any role", was previewed in chat from the 44 Worlds Swiss games as an entry point to this data. Ideas to carry into session 2:
        - Bot lane should be judged as a duo (ADC + support against ADC + support), not only ADC v ADC and support v support.
        - Separate lane result from game result ("win lane, lose game"): use gold/XP/CS difference at 10 and 15 from the Oracle's Elixir file for the lane, and the result for the game.
        - Samples are thin at Worlds (44 games: 139 lane pairings, 47 seen 2+ times), so the grid should be built from the full major-league file, with Worlds games as the test set.
        - Team strength leaks into a champion's record (the stronger team's pick looks better), so matchup effects should be measured after the session 1 ratings are taken out.
        - Today the app uses Worlds lane records only as a fallback when METAsrc has no number (`matchup()` in `js/core.js`, 2+ games, shrunk as (w+1)/(g+2)), and on champion cards ("Countered by" and "Counters").
    - Deliverable: a report on how much each part moves win odds, tested the same way.
3. **The game-state simulator**
    - State per step: gold and XP lead, kills, towers per lane, dragons by type and soul point, grubs, Herald, Baron and Elder timers.
    - Event chances fitted to the 10/15/20/25 snapshots and end-of-game totals: lane gold per player, skirmishes, objective fights, tower falls, Baron and Elder, game end.
    - Calibrate so its win odds match the session 1 model.
    - Deliverable: a side-by-side of simulated vs real distributions (length, kills, gold at 15, objectives).
4. **Player of the Game, and wiring into the app**
    - POG model trained on real LCK POG awards against those games' box scores (source to confirm, see Risks).
    - Replace `simGame` and the POG rating in the app with the new engine; keep the draft, series and tournament screens.
    - Ship the fitted tables as small JS files; bump the cache version.
    - Deliverable: the app running on the new sim, plus the first match-day scorecard.
5. **Polish and match-day routine**
    - A repeatable update: drop in a newer Oracle's Elixir file, re-run one script, refresh the tables and the scorecard.
    - Remove the old hand-set constants and update the ⓘ panel and README to describe the new model.

## How we test it

Every model is judged on games it was not fitted to, and the new sim ships only if it beats the current one on those games.

| Check | How measured | Target to ship |
| --- | --- | --- |
| Win odds | Log loss and Brier on games after 1 Sep, plus all Worlds games as they're played | Better than the current sim (current Worlds log loss 0.68–0.70) and better than a coin flip (0.693) |
| Calibration | When the model says X%, how often does that team win, in bands of 10% | Each band within about 5 points of its stated odds |
| Accuracy (for reference) | Share of games the favourite wins | About 60–65% at Worlds level; higher is unlikely |
| Game length, kills, gold at 15 | Simulated vs real spread (average and spread, not just average) | Averages within 5%; spreads visibly matching |
| Objectives | Dragons, Barons, towers per game; first-Baron and first-Elder team win rate | Within 5% of real |
| Kill share by role | Simulated vs real share of kills per role | Within 2 points per role |
| POG by role | Share of POG awards per role vs LCK | Within 3 points per role |

After launch, each match day adds a scorecard row: games, the app's pre-game odds, the result, and the running log loss.

## Risks and open decisions

The biggest risk is overfitting: about 2,800 major-league games is enough for a simple model, not for hundreds of free parameters.

| Risk | Effect | Mitigation |
| --- | --- | --- |
| Overfitting | Looks great on past games, worse on new ones | Few parameters, shrink toward averages, judge only on held-out games |
| Small samples for synergies and counters | Noisy pair and matchup effects | Start from solo-queue values; let pro data move them only slightly |
| Time resolution | Only 10/15/20/25-minute snapshots, not every event | Fit the step model to snapshots and end totals; check the live feed for minute frames as an upgrade |
| POG source | Not in the file | Checked 6 Nov in the browser pane (Leaguepedia, readable as a normal visitor): **LPL names a Player of the Game for every game** (2026 Split 3: 167 of 167 games); LCK and Worlds name one per series only (LCK Rounds 3–4: 40 of 40 series; Worlds main event: 12 of 36 played series, the rest "None"). Where Leaguepedia takes them from (broadcast or league site) not checked. Fallback: a box-score rule, labelled as a rule |
| Roster changes mid-season | Team ratings mix old and new players | Rate players, build team strength from the current five |
| Patch and meta drift | Early-season champion data misleads | Weight recent games more |

Open decisions for Luke:

- [ ] **Session 4 plan, first build** (drafted 12 Nov, below): Luke to OK it, starting with steps 1 and 2 (research only).
- [ ] **Which sim is the app's default** (the other sits behind the switch): waits for the corrected-sim re-runs (`research/sim3-report.md` 7l).
- [ ] **Full tests for lane-level version 3 and the corrected sim:** only the short Worlds-only test has been run. Run the fixed test on all 321 games and the walk-forward before the app ships, or accept the short test?

### Session 4 plan, first build: the new sim plus draft review (drafted 12 Nov 2026 AEST, not yet OK'd)

**Worked example: Gen.G (blue) v Invictus Gaming, Worlds semi-final game 1, 7 Nov** (file game `LOLTMNT02_487213`; a played game, so the app's numbers can be checked against what the research scripts saved). Kiin Olaf, Canyon Qiyana, Chovy Cassiopeia, Ruler Jhin, Duro Leona v TheShy Kled, Wei Vi, Rookie Syndra, JiaQi Xayah, Meiko Rakan. Real: Gen.G won in 33:38, 29 kills to 9, +2,948 gold at 15. What the research sim was given (tables fitted before 1 Sep; the all-games refit will shift them a little):

| Input | Value |
|---|---|
| Team strength (v1) | z 1.026, Gen.G 73.6% |
| Lane skill gap (top, jng, mid, bot, sup) | +0.07, −0.10, +0.17, −0.40, −0.09 |
| Champion lane value at 15 | −183, +495, +74, −121, −78 gold |
| Draft styles, both teams together | pace +0.07, siege +0.11, objectives +0.13 |
| Lane-level part from each lane's skill and champion inputs (`m0`, from the version 3 fit; version 2's values differ and are the ones in use; before team strength, kills and plates) | −144, +544, −12, −100, −42 gold |
| Lane-level expected lead before the game (`e0` plus its team-strength term × z) | −64, +763, +355, −92, +4 gold |

**The draft through each file**
1. New `js/sim-tables.js`, built by a script from the fitted results (never hand-edited): event parameters (`params3.json`), fight types, the lane-level fit, team ratings, the 80 Worlds players' lane skills, champion lane values, champion styles. The fitted pieces are under about 100 KB by file size; the player-history tables (a player's earlier games on a champion, champion-role strength, bot-duo synergy and time together) are not sized yet.
2. New `js/sim-engine.js`: (a) an input builder that turns the two teams and ten picks into the table above (check: it reproduces those numbers for the example); (b) the game sim, a port of `research/sim3/s3_sim.py` (397 lines), with its own seeded random generator (the app uses `Math.random()` today).
3. `js/core.js`: `simGame()` (called from draft review at 600 runs, `runGame` at 1,500, and `js/tournament.js` at 300 plus AI games) calls the new sim and returns the same fields as now; the old sim stays behind a switch. `analysis()`: "before draft" from team strength, "after draft" from runs of the new sim.
4. `js/tournament.js`: `pack()` unchanged. `gameStats()` gets Player of the Game version C and the percentile rating (Luke's final confirmation first).
5. `index.html`: two new script tags, cache v45 → v46 on every tag (12 after the change; the header comment in `js/worlds-live.js` gets its fix in the same bump).

**Order of work**
1. Refit on all games, side by side with the pre-1 Sep tables (Luke: refit first). About 30–40 min: fit chain about 10 min (measured: 520 s a round, lane-level 52 s, fight types 25 s), Worlds runs about 10 min per sim. No held-out games remain after this refit, so the side-by-side shows how much tables and odds move, not whether they are better.
2. Read what the plan still depends on, then fill the gaps with Luke: how v1 is built from team and player ratings (not read yet); every field `simView` and `gameStats` read from a game; the history inputs lane-level play needs and how to freeze them into small tables. About 15–20 min.
3. Tables script and `js/sim-tables.js`.
4. Port the sim.
5. Wire `simGame()` and draft review, with the switch.
6. Browser check in a new tab (desktop and 375 px, console clean), cache bump.

**How the port is checked:** JS and Python random generators differ, so games cannot match one for one. For the example and a set of other games, 1,000 JS runs against 1,000 Python runs must agree on win rate, length, kills, towers and gold at 15 within sampling error; the same seed replays the same game in the app; every tournament run still starts 0–0 and the new sim ignores the app's "form" adjustments.

**Not yet known:** the new sim's speed in the browser at 300–1,500 runs; the size of the player-history tables; which sim is the default.

Decided:

- [x] **12 Nov 2026 AEST, later in the session (Luke):**
    - **Tower-push phase bug: fix it.** The corrected reading is the sim's default (`cal["seg_phase"]`, default `"own"`); `s3_test.py ... oldsp` replays earlier runs. Every earlier score is from the sim before the fix.
    - **Lane-level version 3 (plates by lane) is used if reasonably level with version 2.** Its first fit was level on the short test, but on the corrected sim the corrected fit is worse than version 2 (0.6103 v 0.6068; 0.6109 v 0.6022; `research/sim3-report.md` 7l), so **version 2 stays in use** and version 3 is re-tested after the gold-lead work.
    - **Shorter testing:** the 94 Worlds games at 1,000 sims (`S3_TEST_LEAGUE=WLDs`), about 10 min a version. A screen, not the two-test rule; see the open decision above.
    - **App work starts alongside the research** (the plan above).
    - **No patch data from after 16.20 for now** (the 3 LCP games on 16.22 stay out of `js/pro-matchups.js`).
    - **Explore the gold lead at 15** (too wide and too tied to team strength in every sim; 7l).

- [x] **How session 4 starts** (Luke, 12 Nov 2026 AEST, four answers):
    1. **First build: the sim plus the draft review.** Other screens follow.
    2. **Two sims: one default with a switch** to the other.
    3. **Tables: refit on all games first**, shown side by side with the tables fitted before 1 Sep, before the app build. Luke: learning from all the Worlds games is very valuable even with fewer matches.
    4. **Player of the Game: version C** (final confirmation still comes before session 4's final commit).
    Before that, Luke wanted the spread of game length and kills worked on further ("it seems that making the app will just show that is still an issue"). Changed later the same day: app work starts alongside the research (entry above).
- [x] **Lane-level play and the spread: keep every input** (Luke, 12 Nov 2026 AEST). Every lane and input stays in the model even when its effect is small ("do not throw out data"). A version that is marginally better or worse is acceptable if it adds depth to the sim's results. Values are formed from the data and checked against outside sites, never hand-picked. Result: lane-level play version 2 is in the sim as an option and improves who-wins on both sims in both tests (`research/sim3-report.md` 7k); the spread is still open.

- [x] **Two sims go into session 4** (Luke, 12 Nov 2026 AEST). The baseline (the default game-state sim, lane × tier pushes on) and the baseline plus the extras (fight types and won-fight pushes with the fitted cutoff; `s3_test.py ... typed,pf`). The app's final sim is one of them, or both with an option to choose. Luke cares most about accuracy on Worlds games; the baseline is the simpler, better planned sim. Both are the same code with two settings, and the extras need their fitted tables shipped too. On both tests at 1,000 sims the two are level with each other and with v1 on Worlds, and both are ahead of v1 from 1 Sep (`research/sim3-report.md` 7j).
- [x] **The sim tests use seeds by game ID and 1,000 sims per game** (Luke, 12 Nov 2026 AEST). This changes the fixed test, which until now stayed exactly as it was. Why: at 200 sims the score moved by chance more than the gaps being judged (the same version on the same 94 Worlds games scored 0.6168 to 0.6287 across four seedings), and seeds came from a game's place in the list, so adding games changed other games' draws. Now each held-out game's seeds come from its game ID, the same for every sim version. Calibration is unchanged. `s3_test.py ... oldseeds` at 200 sims reproduces every earlier run. Scores from before 12 Nov (200 sims) are not comparable with later ones.
- [x] **Session 4 does not wait for the final** (Luke, 11 Nov 2026 AEST). If the pre-work (default sim, walk-forward test, re-test over the Worlds results so far) is ready before the final on 14 Nov (US), session 4 starts. The final's games join the tests when a newer Oracle's Elixir file has them.
- [x] **Recent games count more, where the data can show it** (Luke, 11 Nov 2026 AEST). The parts fitted from the file alone (laning, champion draft styles) weight recent games by a half-life chosen by test on July–August match weeks (candidates 30, 60, 120, 240 days and no fade; Luke expects about 60 days, 2–4 patches, "if data supports this enough"). The timeline-fitted parts (fights, pushes, objectives) use no fade, because the timelines only start in late July. Script: `research/sim3/s3_halflife.py`. **Result and choice (11 Nov; 664 July–August games, nine weeks):** draft styles: every fade beats no fade, 60 days best (match with what the game showed: no fade 0.142, 30 days 0.156, 60 days 0.158, 120 days 0.153, 240 days 0.149); laning: 120 and 240 days tie for best but barely differ from no fade (error share 0.9076 v 0.9080; 60 days 0.9088, 30 days 0.9153; the week-to-week range is 0.87–0.99). **Luke chose 60 days for draft styles and 120 days for laning**, the test's picks. Numbers: `research/local/sim3/hl/halflife.json`.
- [x] **Testing rules for the rest of the sim work** (Luke, 10–11 Nov 2026 AEST):
    - Two tests, always both: the fixed test (fit before 1 Sep, test from 1 Sep and Worlds) keeps its split, and a walk-forward test runs alongside it (`research/plan-lanes-recency.md`; weekly refits, `research/sim3/s3_walkforward.py`). From 12 Nov both run at 1,000 sims per game with seeds by game ID (decision above).
    - **Every tested sim version and its data is kept**, including ones "not kept" on a first test (fight types, won-fight pushes with each cutoff, lane × tier). **All of them are tested again over the Worlds results in session 4** before the app's version is chosen.
    - No random-only lane results: lane-level play from each lane's players and champions where test games support it (the plan file above, Part A).
- [x] **Five decisions before session 4** (Luke, 6 Nov 2026 AEST, answering the options shown in chat):
    1. **Player of the Game source: check first.** Claude reads Leaguepedia's per-series "MVP" column and looks for official per-game awards (read-only), reports where they come from and how complete they are, then Luke chooses. Fallback if neither holds up: a box-score rule, labelled as a rule, not as learned.
    2. **Draft styles: keep all three** (pace, siege, objectives) and keep validating them with results and research. Luke: siege should show itself in later games — late game is generally siege or scaling comps — so the sim needs to know which champions fit each style and which comps use them. Next research: champion-to-style fit (outside labels, not assumptions) and tests of siege and scaling against late-game timing (towers after 25 min, length), not only first-tower time. Pace → kills per minute is the only style effect confirmed so far. **Validation run 6 Nov (`research/comps-plan.md`):** measured siege (champions' real share of tower damage) passes on held-out games — more towers, first tower about 30 s earlier per standard deviation — but not more towers after 25:00; Riot classes (Artillery included) and lolalytics scaling don't hold up on held-out games yet.
    3. **Grubs: keep the taker model.** Luke: the sim's job is to let the engine play the game out from data-supported tendencies; if blue ends up with grubs about 63% of the time, that should come out of the simulation, not be a set rate. Grubs are a minor objective, more useful in some comps than others.
    4. **No "one damage type" warning.** In champ select, show a meter that builds as picks are added: magic and physical damage sources, and possibly tankiness and CC / utility. The draft AI (rebuilt in session 4) should know a good comp from a bad one, with damage sources one element among others. Meter values from data (sources to settle when planned).
    5. **Who-wins: v1 is the baseline for comparison; the final model must beat it regardless.** The v2 candidate's knockout test keeps running as evidence; there is no early choice between v1 and the candidate.
    6. **Player of the Game and per-game ratings (Luke, 6 Nov; bring back to Luke for a final confirmation before session 4's final commit):**
        - **Award data (Leaguepedia's Cargo export, 2026, matched to the Oracle's Elixir file):** per-game awards for 977 games (LPL 672, LCS 260, First Stand 45; every winner found among the game's players); per-series awards for 916 series (LCK 188, LPL 246, LEC 186, CBLOL 117, LCP 97, LCS 26, Worlds 15, EWC 15, First Stand 13, MSI 13). LCK 2026 has no per-game award in any source checked (Leaguepedia's per-game field is empty; LCK's own awards list "Most POMs"; Sheep Esports match pages show none). The award went to the winning side in every game and every series. Per-game role shares: jungle 32%, mid 25%, ADC 18%, top 15%, support 10%. LPL series MVP v per-game awards: the series MVP won at least one game award in 95% of series.
        - **Model:** a choice among the winning side's five, from the box-score stats the new sim produces (kills, deaths, assists, kill participation, damage share, lead at 15, vision, role); damage taken is left out (the sim doesn't make it). Fitted on per-game awards; series awards (LCK, LEC and the rest) used to test it and as extra training data (series MVP = the player with the highest chances over the games his team won). Quick check (not final): right pick 65% on later LPL games and 61% on LCS + First Stand (never fitted), against 52% for "most kills"; series MVP named in 51% of 883 series (chance about 20%). In the app, Player of the Game is a random draw from those chances.
        - **Model version C chosen (Luke, 6 Nov):** fitted on per-game awards (LPL, LCS, First Stand) plus series awards (LCK, LEC, CBLOL, LCP, MSI, EWC, Worlds), using only the stats the new sim produces. Refit results (`research/pog/README.md` step 6): beats today's formula on every held-out check (e.g. LCS + First Stand games, never fitted: right pick 57% v 49%, log loss 1.086 v 1.214; LCK series: 47% v 42%, 1.372 v 1.520); against per-game awards only (B) it is a wash.
        - **Per-game rating = the percentile of that fitted score among real major-league player-games in the same role, ÷ 10** (no hand-made scale). Today's formula (`gameStats`, hand-set weights) is kept only for comparison. Measured: today's app rates winners 6.6 and losers 2.9 on average over 400 simulated games (6% of losers reach 5); the percentile of the quick model's score on real games from 1 Sep gives winners 6.4 and losers 3.3 (25% of losers reach 5). Example, BLG 3–0 DK game 1: Xun 9.2, Knight 8.9, Viper 5.8, ON 5.4, Bin 3.4; Lucid 3.6, Siwoo 3.6, Career 2.6, Smash 1.8, ShowMaker 1.1.

- [x] **Sim session 1 foundation: ratings and the who-wins model** (Luke, 2 Nov 2026 AEST, 8 decisions):
    1. **Team strength is fitted from game results**: a team rating with a league-strength term (linked through First Stand, MSI, EWC and Worlds meetings), a side term and recency weighting. Player ratings explain it role by role; a team's strength uses its current five, so stand-ins (e.g. 369) are handled. Luke's note: judge bot lane as a duo (ADC + support against ADC + support), not only ADC v ADC and support v support; there is more nuance across the map and roles, but start from here.
    2. **Role skills**: 3 per role, today's names (`ATTR` in `js/core.js`) kept where the data measures them, measurable replacements proposed for the rest. Claude drafts a role-by-role table (skill, stats used, why) for Luke to approve before fitting.
       Draft table (Luke, 2 Nov; data columns checked in the Oracle's Elixir file: 2,845 major-league games). Values per game, against the lane opponent or role average, adjusted for game length, weighted for recency and Worlds:
       | Role | Skill | Stats |
       | --- | --- | --- |
       | Top | Laning | gold, XP, CS lead at 15 (10 as a check) |
       | Top | Teamfight | kill participation, damage share |
       | Top | Consistency | Luke: covers the different jobs a top laner is given. Three parts: steadiness (game-to-game spread of laning, damage and KDA), side pressure (damage to towers, lead at 20–25) and durability (damage taken and mitigated per minute, few deaths). Judged against top laners on similar champion types (tank v carry). Overlap to watch: durability's frontline stats were first drafted under Teamfight, so they move here and Teamfight keeps kill participation and damage share |
       | Jungle | Early game | kills + assists by 15, first blood involvement, XP lead at 15 v enemy jungler |
       | Jungle | Objectives | team's share of dragons, Heralds, grubs, Barons (team rows) |
       | Jungle | Teamfight | kill participation, damage share, deaths |
       | Mid | Laning | gold, XP, CS lead at 15 |
       | Mid | Map impact (was Roaming) | share of the team's kills by 15 the mid took part in, first blood involvement |
       | Mid | Damage | damage share, damage per minute |
       | ADC | Laning | the ADC's own gold, XP, CS lead at 15, informed by the bot duo's combined lead (ADC + support v enemy duo); the support's skills don't include the duo score |
       | ADC | Damage | damage share, damage per minute |
       | ADC | Positioning or Late game | test both and keep the one that adds more (predicts winning beyond Damage): Positioning = deaths per game and damage per death; Late game = gold/XP lead at 20–25 and damage share in long games |
       | Support | Playmaking | kill participation, assists, first blood involvement, kills + assists by 15 |
       | Support | Map presence | vision score per minute, wards placed and cleared, control wards |
       | Support | Reliability | deaths per game, deaths before 15 |
       Not in the file: pick order (pick1–5 empty), player-row objectives, enemy-jungle CS (5%). Timeline stats at 10–25 min are about 95% complete (which leagues are missing: not checked).
       **Follow-up (Luke, 3 Nov):** look at Faker in more depth in later passes whenever more relevant data is available. 2026 file stats (155 major games): behind in lane at 15 on average (−129 gold, 9th of 10 LCK mids with 30+ games), lowest damage share and kill participation of those 10, T1 won 63%; ahead in May and in his 5 Worlds games. Champion pool, role within T1 and anything the file can't show (calls, utility picks) not yet checked.
       **Flagged for later sessions (Luke, 3 Nov):**
       - **Champion pools as a player-rating factor** (session 2): judge players against others on similar champions (e.g. a mid on utility mages), and test whether pool breadth/depth adds to winning.
       - **Title holders noted on cards**: Worlds champions (and similar honours) shown as a factual line.
       - **Multi-title "special bump"**: rare, and only where the player's current win share backs it up. How it is calculated is not decided; it must come out of the experience test below, not be set by hand.
       - **Experience test, first run (3 Nov):** career facts before 2026 from Leaguepedia (all 442 players matched; Faker 6 Worlds + 2 MSI titles, 10 Worlds appearances, 319 Worlds/MSI games). Added to team ratings + league-adjusted player skills, every version (titles, Worlds titles, international games, veterans) points the right way (about +0.6 win-% per title difference, +2.6 per veteran) but all made the Jul–Aug tuning games worse and gains on later sets were small and inconsistent. Decision (Luke): not in win odds for now; **re-test after the Worlds knockouts**.
       - **Open requirement (Luke, 3 Nov): Faker cannot be left with a mid rating** (S5 overall 72 on 2026 stats). Resolve through the process (champion-pool context in session 2, the knockout re-test of experience, how team "wins beyond stats" is shared), not by hand-setting a number.
    3. **Card scale — S5 adopted (Luke, 3 Nov)**, replacing the percentile idea below: card = 70 + 10 × (standard deviations above the role average, league-adjusted), clipped 40–99, over all major-league players (442; 10+ games for the reference pool). 70 = average major-league player, about 83 = top 10%, world's best about 93–99. One scale for Worlds and non-Worlds players (e.g. Scout 92, Effort 96 sit among the Worlds best). Rejected: S0 all-player percentile (bunches 22 of 80 Worlds players at 95+), S1 rank within the Worlds field (implies everyone else is below 50), S2 win-impact (supports look weak), S3/S4 team share (swamps support differences; "wins beyond stats" to be a team stat instead).
       Original wording: each skill is a role percentile among major-league players, shrunk toward the role average for small samples, shown on today's 50–99 scale. Luke's note: be smart about it so the numbers don't end up like today's (not accurate). Agreed approach: the card number is display only; the sim uses the underlying fitted effect in game terms (e.g. gold at 15 v role average, and what it is worth in win chance), never the percentile. The report shows both side by side.
    4. **Overall**: weighted by how much each skill predicts winning (a handful of fitted weights per role, shown in the report), not a plain average.
    5. **Recency**: chosen by the held-out test (compare half-lives such as 60, 90 and 180 days) and reported.
    6. **Worlds games get no extra weight** (changed by Luke on 3 Nov AEST, "follow the test"; first choice was extra weight). Tested on First Stand, MSI and EWC before 1 Sep: counting the same event's earlier games more made predictions worse at every setting (log loss ×1 0.659, ×1.5 0.666, ×2 0.672, ×3 0.683, ×5 0.700). Recency already favours Worlds games. The ±1 per game / ±3 total form rule is not part of the new model.
    7. **No hand cap on odds**: the model sets its own confidence, a calibration table checks it, and one fitted "temperature" softens it if it is still too sure.
    8. **Testing: all three kinds**: (a) train on major leagues and internationals before 1 Sep, test on games from 1 Sep; (b) Worlds games only (22 play-in + 51 Swiss so far, then knockouts as played; small and noisy, reported as such); (c) a rolling test that refits month by month and predicts the next month. The new model ships only if it beats the current app on the same games.

- [x] **Sim session 3 foundation: the game-state sim** (Luke, 5 Nov 2026 AEST, "yes go ahead" to the plan shown in chat):
    - One-minute steps, seeded random generator. State per team: gold and XP per lane, kills, towers and plates, dragons by type (soul at 4), grubs, Herald, Baron, Elder (real spawn timers), inhibitors.
    - Laning from players' laning skills (session 1), pro lane records (session 2) and champion gold curves; jungle and roaming as measured effects (no position data); kills per minute by phase, gold lead and draft pace; objective contests by gold lead, jungle/support skills and draft style; towers and plates faster for the team ahead and siege drafts; game end once an inhibitor is down, by gold lead, Baron and Elder.
    - Calibrated so each matchup's simulated win rate matches the who-wins model (v1 now; v2 only if it passes the knockouts). Box score fills the app's `pack()` record in the same shape.
    - Targets: length, kills, gold at 15 within 5% (spreads matching); objectives and first-Baron / first-Elder win rates within 5%; kill share by role within 2 points; calibration. Fitted before 1 Sep, checked from 1 Sep and on Worlds. Output `research/sim3-report.md`.
    - **Realism rules (Luke, 5 Nov):** no sim action runs with a premeditated or fabricated result to suit the data: every event is a random draw from chances fitted to the data, so the same draft plays out differently each time while following the tendencies. Calibration may only tune how strongly team strength turns into event chances overall; it never sets an outcome. Timing must be flexible within the data: comp, side (blue/red), lane priority and the jungler's choices (a risky path, an early dragon to catch the other team out) can make an objective earlier or later. Be flexible within the data for each champion, player and match.
    - **Draft styles as timing only (Luke, 5 Nov: "use timing for now - we want draft styles/comps to matter etc by the end"):** both drafts' pace, siege and objective focus change when things happen, not who gets them. Ways for comps to matter are listed and tested in `research/comps-plan.md`.
    - **No effect from AI assumptions (Luke, 5 Nov: "the sim engine shouldnt have or not have data based on ai assumptions"):** every proposed effect is checked first, with labels from an outside source, published evidence opened directly, and a held-out test. Example: "no magic damage / no frontline fights worse" was tested and not supported, so it stays out.
    - **Done 5 Nov (report `research/sim3-report.md`):** on held-out games the sim beats v1 (0.635 v 0.640 from 1 Sep; 0.626 v 0.628 at Worlds), and length, kills, towers, dragons, souls, gold at 15 and role kill share match real averages. Open: game-to-game spread too wide, Barons a little low, first-Baron team win rate low, draft styles slightly costly in the final version.
- [x] **Sim session 2 foundation: champions, comps, synergies and counters** (Luke, 4 Nov 2026 AEST, "yes go ahead" to the plan shown in chat):
    - Seven parts, each measured after taking out session 1's who-wins odds (so a strong team's picks don't look good just because the team is strong), each test game predicted only from games before it: (1) champion strength, (2) power curve (gold lead at 10/15/20/25 v lane opponent; wins by game length), (3) comp profile (siege / objectives / skirmish styles learned from what teams did with each champion; a draft = its five), (4) player–champion comfort (minor leagues for history), (5) lane matchups with the bot lane as a duo and lane result kept apart from game result, (6) synergy, (7) who-wins v2 = v1 + parts 1–6 with about one fitted weight per part.
    - A part stays only if it improves log loss from 1 Sep; Worlds games reported too. v2 ships only if it beats v1 (0.646). Deliverables: `research/sim2-report.md`, small tables in `research/model/sim2/`; no app change.
    - Choices (Claude's recommendations, accepted): champion styles learned from the data, then compared with the app's `CHAMP_ARCH`; recency weighting, with a test of adding the patch; solo-queue values (METAsrc, metabot) as starting points moved only as far as pro results support; order comfort + champion strength → lanes, synergy, comp → v2.
    - **Outside sources (Luke, 4 Nov):** for each part, use three well-known, credible sites that publish supporting data, compare them with each other and with what is learned from the file, and report agreement. Pages opened directly with URL and date (no search summaries); only data up to the file's cut-off is used where a site has dates (no knockout games).
    - Worked example: LYON v GEN game 1 (25 Oct): v1 (teams only) gave LYON 20%; LYON won. Held out: a test of v2, not training.
    - **Who-wins v2 candidate fixed before the knockouts (Luke, 5 Nov, "Yes, fix it"):** `research/model/sim2/v2_candidate.json`, made by `research/sim2/s2_v2candidate.py` from games up to 1 Nov 11:42 UTC (no knockout game in the file). logit = v1 + four features (blue minus red, earlier days only): jungle comfort (log 1 + the jungler's earlier games on that champion), jungle pool (champions with 3+ games in 180 days), jungler–mid time together, jungler–ADC time together (log 1 + games on the same team). Weights per standard deviation (SD from games before 1 Sep): 0.0351, 0.0839, 0.0552, 0.0013. **Not to be changed** (file SHA-256 at fixing: 73547478dcad443f9ab5d76869e23255d0e7d2094e2c5d057eb9d73b9dc3f3e6; the commit that adds it is the timestamp). Reference only (features chosen on these games): from 1 Sep 0.6419 v v1 0.6461; Worlds 0.6399 v 0.6446. **Knockout test:** when a newer file has the knockouts, compute the features the same way and score log loss and favourite record against v1 on the knockout games only; the candidate ships only if it beats v1 there.
    - **"Pool" added as a player card skill (Luke, 5 Nov):** every role gets a fourth card skill, Pool, from (a) champions with 3+ games in the last 180 days and (b) current-meta champions played (2+ games, the role's top 10 by pro picks in the previous 30 days), all leagues; card = S5 scale on the mean of the two z-scores (`research/sim2/s2_pool_cards.py`). Reasons (step 10, `research/sim2/README.md`): pool only loosely follows skill (correlation 0.07–0.22), all 2026 play is Fearless, jungle pool beats v1 on every test set, and it shows Faker's strength (pool 89, deepest of the 80 Worlds players) where his laning numbers don't. Uses: on the card and in the draft AI (Fearless series use up comfort picks game by game). In who-wins only jungle pool is a candidate (to be merged with jungle comfort, then tested on the knockouts). Stand-ins with few recent games read low (369: 43); the card should say how many recent games it's based on. Not in the Overall until it is tested as part of it.
    - **Keep testing who-wins inputs (Luke, 4 Nov, end of part 1):** v1 is not accepted as final for pre-game odds yet. Part 2 keeps testing, and **each role is tested on its own** (top, jungle, mid, ADC, support; bot lane also as a duo), not only as one combined feature.
    - **Current-meta principle (Luke, 4 Nov):** the current patch and recent patches are what matter for current pro play and tournaments. Each tournament in the app (Worlds 2026 now, the only one) must follow that event's meta tendencies closely, and the inputs roll forward as new patches, events and metas arrive. Evidence so far (step 3c, `research/sim2/README.md`): Worlds pick + ban presence matches 16.17 at 0.91 and 16.01 at 0.60; lolalytics win rates match 16.20 more closely the nearer the patch. Not shown yet: that champion or meta inputs improve **who wins** (patch-aware champion strength and lolalytics win rate gave no measurable gain, steps 2–3); the meta clearly drives **what gets picked and banned**. Each remaining part is tested with the latest patches weighted most.
- [x] **Data cut-off: only games in the Oracle's Elixir file** (Luke, 4 Nov 2026 AEST). Sessions 2 onward are built and tested on the games the current file holds (now to 1 Nov 11:42 UTC: no knockouts), even though knockout games are being played. Work does not wait for real knockout results, and results Claude doesn't have are never assumed or looked up to fill the gap. Knockout games join the tests (and the experience re-test) only when a newer file with them is added.
- [x] **Minor leagues stay out of fitting for now** (Luke, 29 Oct). Ratings, the who-wins model and event chances are fitted on the major leagues and internationals only. Minor-league games are used for player history and champion pools, e.g. a player with few major-league games such as TES's stand-in 369.
- [x] **The scorecard is not shown in the app for now** (Luke, 29 Oct). Each session or match-day update shows it to Luke as an artifact in the Claude Code chat, and the running numbers are kept in the research notes.
- [x] **The old engine stays** (Luke, 29 Oct). The app keeps using it until the new one passes its tests, and afterwards it's kept as a reference, a fallback, and possibly a simple-mode simulator. So session 5's "remove the old hand-set constants" doesn't apply: the old engine's code stays, and only the screens that use the new engine describe it.
- [x] **Fitted ratings replace the ratings shown** on player cards, power rankings and tier lists (Luke, 29 Oct). What stays is the idea behind them: each player has role skills and an overall rating that are easy to read, mean something, are interesting to compare, and feed the match sim. **The foundation is planned with Luke before anything is built** (sim session 1): which skills each role has, what each is fitted from, how the overall is made, and how they feed the sim. Today's skills per role are in `ATTR` in `js/core.js`.
- [x] **The draft review is based on the new model** (Luke, 29 Oct). Both "Before draft" and "After draft" move off the current formulas (`winP` on the rating gap; 600 runs of the old `simGame`). **The foundation is planned with Luke before anything is built** (sim session 4, once sessions 1–3 have produced the who-wins model and the simulator): what the review shows, how the draft changes the odds, and how each part is explained.
- [x] **Draft AI is rebuilt from data** (Luke, 29 Oct). The hand-weighted `scoreFor()` in `js/core.js` is replaced. The new draft AI weighs comfort, team composition, meta, synergy and counters, plus anything else the data shows matters. Measuring each part's effect belongs with session 2; wiring it into the app belongs with session 4. Candidates to test in the data (not yet checked): pick and ban order (what pro teams take first, flex picks early, counter-picks late), side, target bans on a player's comfort picks, champion pool depth, damage mix, and Fearless locks in Bo3/Bo5.

## Related files

- `research/backtest-2026.md`: the 711-series back-test and the `SIMK` calibration.
- `research/worlds-live-2026.md`: real Worlds games, the out-of-sample checks and the real-vs-simulator comparison.
- `research/model/h2h_2026.json` and `js/h2h.js`: real 2026 head-to-head built from the Oracle's Elixir file.
