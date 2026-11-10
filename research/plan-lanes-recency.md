# Plan: lane-level play and training on recent games (draft, 10 Nov 2026, for Luke's OK)

Luke (10 Nov): (1) too much of the sim is a random draw — a strong bot duo on strong lane champions shouldn't lose its lane just by chance against a weak one; the sim should be as close as possible to real play, especially recent data, the current meta and the Worlds teams, players, champions, comps and tendencies. (2) The 1 Sep training cut-off is months old; use September–November and Worlds.

Rules that still hold: every number is fitted, never hand-set; outcomes come out of the simulation, nothing is scripted; every addition is judged on games it was not fitted to; few parameters, pulled toward averages.

## Where the sim is now (checked in `research/sim3/s3_sim.py` and `research/model/sim3/test3_results.json`)
- Each lane's farm lead to 15:00 = the fitted expectation for that matchup (team strength, the lane's player skills, champion lane values) plus noise. **But calibration shrank that expected part to 5% (`lane_mu` 0.05)**, because kills and plates also move gold and the lane part was being counted twice.
- Who wins each fight: team strength, gold lead, buffs. **Which role gets the kill and which dies: average role shares, the same in every game.** So a strong bot duo helps its team only through the team rating and a small farm edge; bot-lane kills, bot priority and dragon don't lean its way specifically.

## Part A — lane-level play

**What it shows.** In the sim, each lane's early game (to 14:00) depends on that lane's own players and champions where the data supports it: the lane's gold lead, kills and deaths of that lane's players, solo kills, which lane loses the first tower, and bot priority into first dragon. After 14:00 the game stays team-level, as now.

**What it's built from.**
- Inputs known before each game (earlier days only): session 1 lane skills per role, champion lane values (pro gold at 10 and 15), ADC champion strength and ADC + support pair synergy (the two that held up for bot in session 2 and report 7c).
- Outcomes: the file (all major games: each player's gold, XP and CS at 10 and 15; kills, assists and deaths at 10 and 15) and the gol.gg timelines (each kill's killer and victim role and time, each tower's lane, each dragon's taker).
- What the data already says: inputs passed for the bot lane only (7c); comfort and time together move no lane events; ganks and roams aren't stable player habits (7b). So bot is where to start; the other lanes get the same test and keep only what passes.

**How it's fitted.** One small model per lane and event, each with a handful of inputs, pulled toward average:
1. Lane gold lead at 15 from the lane inputs (exists, `s3_lanes.py`), with the double count fixed by fitting the farm part and the lane's kills together, so the calibration no longer has to shrink it.
2. Lane kills before 14:00: the chance a kill happens in that lane (per minute) and who gets it, from the same lane inputs plus the jungle's involvement (the timelines show the jungler in 2.3 early kills a game).
3. First tower lane, and bot lead into first dragon (the dragon taker model already reads the bot lead; it would now get a lane lead that carries the matchup).

**How it feeds the sim.** Before 14:00 the sim draws kills per lane with these fitted chances instead of average role shares. The lane leads that come out feed the existing tower, dragon and gold models. Nothing decides a lane in advance: a strong duo wins its lane as often as strong duos do in real games, and can still lose it as often as they really do.

**Worked example: semi-final 2, game 1 (8 Nov, BLG blue v T1).** Bot: Viper (Corki) + ON (Nautilus) against Peyz (Xayah) + Keria (Rakan). Real result (Oracle's Elixir rows): T1's bot lane was ahead at 15:00 (Viper −713 gold, ON −432; T1's duo about +1,145), and BLG won the game in 30:25.
- Now: the sim would give T1's duo a small farm edge (5% of its fitted size) plus whatever T1's team rating gives; bot kills fall by average role shares.
- With Part A: the bot model gives the T1 duo's expected lead from the two duos' lane skills, Xayah–Rakan v Corki–Nautilus lane values, ADC strength and pair synergy (the number to be measured, not stated here); the sim draws the lane around it with the fitted real spread; bot kills before 14:00 lean T1's way by the fitted amount; that lead feeds first dragon and bot towers. BLG can still win the game, as it did, through fights and team strength after 14:00.

**How it's judged (held out).** Per lane: error of gold at 15 and of early kill difference against the current sim; then who-wins log loss, the game-shape checks (length, kills, short games, towers, dragons), and the spreads. Kept only if better on both test sets.

## Part B — training on recent games

**What changes.**
- **Recent games weigh more.** Each training game counts with weight ½^(age / half-life). The half-life is **chosen by the data**: try a few (for example 30, 60, 120, 240 days and no fade) and keep the one that predicts unseen games best. Each model family (who-wins, lanes, fights, pushes) gets its own.
- **Tested match day by match day (walk-forward).** For each day from 1 Sep: fit on every game before that day, predict that day. All September–November and Worlds games are then used for learning and every game still gets an honest test. The game-state sim's calibration is slower, so it would refit weekly (fit on games before each week, predict that week).
- **The app's tables** are refitted on all games through the latest file.

**What it's built from.** The same data: the Oracle's Elixir file (to 9 Nov with Luke's saved rows) and the gol.gg timelines (to 5 Nov; the semi-finals need a newer pull).

**Worked example.** T1 v BLG in SF2 is predicted from every game up to 7 Nov, with recent ones (Worlds, LCK and LPL playoffs, 16.15+ patches) counting most if the chosen half-life says so. The score for SF2 is added to the walk-forward total.

**Decided (Luke, 10 Nov): both tests, for the whole of testing.** The fixed test (fit before 1 Sep, test from 1 Sep and Worlds) stays exactly as it is now, for consistency with every earlier result. The walk-forward test runs alongside it, and every version reports both scores. The half-life is chosen on July–August match days only, so games from 1 Sep stay a clean test in both.

## Part B, first result: v1 who-wins (10 Nov)
`research/sim1/v1_walkforward.py` → `research/model/sim1/v1_walkforward.json` (file to 9 Nov with Luke's saved rows).
- **v1's team ratings were already walk-forward:** refitted every match day on all earlier games, with a 90-day half-life chosen in session 1 (`exptest.py`, `teamfit.py`). So recent form already drives team strength. What stayed fixed at 1 Sep was only the final combination (how much team rating v player skills count) and the league shift.
- Walk-forward of that combination, half-life chosen on July–August: every candidate within 0.001 (no fade 0.6384, 480 days 0.6385, 240 0.6386, 120 0.6389, 60 0.6393), so "no fade" was chosen.

| Games | Fixed (as now) | Walk-forward |
|---|---|---|
| From 1 Sep (332) | 0.6382, favourite 64.5% | 0.6392, 64.5% |
| Worlds (94) | 0.6173, 64.9% | 0.6176, 67.0% |
| Worlds knockouts (21) | 0.5224, 76.2% | 0.5216, 81.0% |

- The fixed column reproduces v1's saved scores exactly. Walk-forward makes no real difference for v1: the combination is stable, and the recent-games effect is already in the daily team ratings.

## Order
1. Part B for the file-based models first (who-wins, lane gold): quick, and every later fit uses it.
2. Part A, fitted and judged under Part B, bot lane first.
3. The fight and push work from report 7g, re-judged under Part B.
4. Then sim session 4 (into the app).
