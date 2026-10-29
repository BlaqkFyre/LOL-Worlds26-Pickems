# Pick'Em Lab: data-built game simulator plan

Written 27 Oct 2026. Status: **planned, not started.** The live copy (with a diagram) is the Claude doc of the same name; this is the repo copy.

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

- [ ] Keep the old engine as a "Classic" mode, or remove it once the new one passes its tests?
- [ ] Should the app show the scorecard (a small "how accurate is this" panel), or keep it in the research notes?
- [ ] Confirm the minor leagues stay out of fitting (they're useful for player history only).

## Related files

- `research/backtest-2026.md`: the 711-series back-test and the `SIMK` calibration.
- `research/worlds-live-2026.md`: real Worlds games, the out-of-sample checks and the real-vs-simulator comparison.
- `research/model/h2h_2026.json` and `js/h2h.js`: real 2026 head-to-head built from the Oracle's Elixir file.
