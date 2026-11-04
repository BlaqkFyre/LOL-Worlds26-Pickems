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
| POG source | Not in the file; Leaguepedia is blocked from this workspace | Find a reachable source of LCK POG winners, or Luke pastes a list; fallback keeps the current POG formula, re-weighted to the simulated stats |
| Roster changes mid-season | Team ratings mix old and new players | Rate players, build team strength from the current five |
| Patch and meta drift | Early-season champion data misleads | Weight recent games more |

Open decisions for Luke:

None open right now.

Decided:

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

- [x] **Sim session 2 foundation: champions, comps, synergies and counters** (Luke, 4 Nov 2026 AEST, "yes go ahead" to the plan shown in chat):
    - Seven parts, each measured after taking out session 1's who-wins odds (so a strong team's picks don't look good just because the team is strong), each test game predicted only from games before it: (1) champion strength, (2) power curve (gold lead at 10/15/20/25 v lane opponent; wins by game length), (3) comp profile (siege / objectives / skirmish styles learned from what teams did with each champion; a draft = its five), (4) player–champion comfort (minor leagues for history), (5) lane matchups with the bot lane as a duo and lane result kept apart from game result, (6) synergy, (7) who-wins v2 = v1 + parts 1–6 with about one fitted weight per part.
    - A part stays only if it improves log loss from 1 Sep; Worlds games reported too. v2 ships only if it beats v1 (0.646). Deliverables: `research/sim2-report.md`, small tables in `research/model/sim2/`; no app change.
    - Choices (Claude's recommendations, accepted): champion styles learned from the data, then compared with the app's `CHAMP_ARCH`; recency weighting, with a test of adding the patch; solo-queue values (METAsrc, metabot) as starting points moved only as far as pro results support; order comfort + champion strength → lanes, synergy, comp → v2.
    - **Outside sources (Luke, 4 Nov):** for each part, use three well-known, credible sites that publish supporting data, compare them with each other and with what is learned from the file, and report agreement. Pages opened directly with URL and date (no search summaries); only data up to the file's cut-off is used where a site has dates (no knockout games).
    - Worked example: LYON v GEN game 1 (25 Oct): v1 (teams only) gave LYON 20%; LYON won. Held out: a test of v2, not training.
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
