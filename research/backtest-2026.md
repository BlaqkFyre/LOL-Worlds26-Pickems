# Back-test: the game sim against real 2026 pro results

Run 22 Oct 2026. These results are used **only** to test and calibrate the simulator's win odds. They don't feed the meta tier list, presence, draft suggestions or any Worlds stats.

## Data

- **711 series (about 1,900 games)** from 2026, in `backtest/*.csv`, each row with a source URL:
  - LCK (Cup, Rounds 1–4, Road to MSI, play-in, playoffs)
  - LPL (Splits 1–3 and Regional Finals)
  - LEC (Versus, Spring, Summer)
  - LCS (Lock-In, Spring, Summer)
  - LCP and CBLOL (Worlds teams' splits)
  - First Stand, MSI, Esports World Cup and the Worlds play-in
- Collected from rdy.gg, Liquipedia, gol.gg, Sheep Esports, esports.gg, GosuGamers, Strafe, Dot Esports and Wikipedia (standings cross-checks). Disagreements between sources are noted in the collection notes; the majority result was kept.
- Only series scores are used (not the real drafts), so each prediction runs the app's own AI draft.

## Method

1. For every pair of Worlds teams, `sim_matrix.js` runs 6 AI drafts × 150 games on each side and averages blue and red. That gives the sim's chance of each team winning one game.
2. The 43 other teams (league opponents) get a strength fitted from their 2026 results, with the Worlds teams held at the sim's values. Those games are a secondary check, because the opponent strengths come from the same results.
3. `analyse.py` scores each game and each series (series odds from the game odds and the best-of length):
   - Favourite win rate.
   - Brier score: 0.25 is a coin flip; lower is better.
   - Log loss: 0.693 is a coin flip; lower is better.
   - A calibration table: when the sim says X%, how often did the favourite really win?

## Results — Worlds team vs Worlds team (main test: 143 series, 416 games)

| | Before calibration | After calibration |
|---|---|---|
| Favourite won (games) | 62% | 60% |
| Favourite won (series) | 65% | 64% |
| Brier (games) | 0.248 | **0.234** |
| Log loss (games) | 0.717 (worse than a coin flip) | **0.660** |

Calibration table (games):

| Sim said | Before: games | Before: favourite won | After: games | After: favourite won |
|---|---|---|---|---|
| 50–60% | 57 | 47% | 167 | 50% |
| 60–70% | 105 | 56% | 145 | 68% |
| 70–80% | 135 | 70% | 92 | 60% |
| 80–90% | 51 | 63% | 12 | 100% |
| 90%+ | 68 | **68%** (sim said 93%) | 0 | — |

**Finding:** the sim was far too sure of itself. It made the favourite a 90%+ shot in 68 games, but that team won only 68% of them. Real top-level games are much closer than the player ratings implied: the median Worlds matchup was about 81/19 in the sim. The best fit was to shrink the gaps between teams to about 40% of their old size (temperature ≈ 2.5 on the log-odds).

**Fix applied:** the strength scale (`SIMK` in `js/core.js`) went from 0.3 to 0.15. After the change:

- The sim rarely calls any Worlds matchup above 80%.
- Its 50–70% calls land close to reality.
- The late-game targets still hold:
  - Average game: about 33 minutes.
  - Team taking the first Baron wins 83% (LCK 2026: about 85%).
  - Team taking the first Elder wins 74% (LCK 2026: about 76%).

Worlds team vs other teams (404 series, 1,056 games) is now well calibrated at every level, e.g. "sim said 84%" → 84% won. That set is partly fitted to itself, so it's a sanity check, not proof.

## Biggest misses (where the ratings, not the sim rules, look off)

| Series | Sim's call | Real result |
|---|---|---|
| DK vs GEN, four 2026 series | GEN about 83% | DK won all four |
| TES vs BLG, three LPL series | BLG about 86% | TES won all three |
| G2 vs GEN, First Stand | GEN 84% | G2 won 3-0 |
| TSW vs TES, MSI | TES 89% | TSW won 3-1 |

These suggest DK and TES are underrated relative to GEN and BLG in `js/data.js`. That's a ratings question for a later pass, not changed here.

## Limits

- **In-sample:** the player ratings were partly built from 2026 form, so this isn't a clean out-of-sample test.
- **Real drafts not used:** each prediction uses the app's own AI draft, not the picks that were actually played.
- **Rosters:** a few teams changed rosters during the year.
- **Ongoing check:** the plan is to keep adding real Worlds 2026 games as they're played and re-run the test.

## Re-running

```
node research/backtest/sim_matrix.js research/backtest/matrix.json   # needs Playwright + Chromium
python3 research/backtest/analyse.py research/backtest/matrix.json
```
