# Laning slice, first build: results (14 Nov 2026 AEST)

The laning module is in the research sim (`research/sim3/s3_sim.py`, option `cal["laning"] = "actions"`, off by default). Tables:
`research/laning/s5_fit_laning.py` (one fit per Worlds day, each on games before that day). Design: `research/laning/step3-design.md`.

**Replay:** with the option off, 642 of 642 seeded games are identical to the sim before the edit (`research/laning/s5_replay_check.py`).

**Worlds, day by day** (`research/laning/s5_laning_check.py`; both versions with death timers and the same calibration; "waves" = the
measured alternation of CS minutes, lag-1 correlation −0.12 to −0.27 by role):

<!-- table: check -->
| Measure (Worlds, 94 games, 200 sims each) | Real | Current sim | Module | Module + waves | + farm in gold |
|---|---|---|---|---|---|
| Lane gold edge at 15, spread: top / jng / mid / ADC / sup | 995 / 786 / 678 / 1043 / 383 | 936 / 839 / 832 / 992 / 446 | 909 / 788 / 902 / 869 / 570 | 869 / 755 / 867 / 822 / 563 | 979 / 880 / 916 / 1001 / 614 |
| Lane gold edge at 10, spread | 599 / 535 / 411 / 594 / 319 | 600 / 542 / 549 / 659 / 311 | 540 / 512 / 553 / 535 / 362 | 506 / 481 / 521 / 495 / 357 | 581 / 555 / 557 / 638 / 392 |
| Team gold edge at 15: spread, gold per unit of strength | [2231, 642] | [2591, 770] | [2619, 996] | [2540, 996] | [2837, 1107] |
| Kills before 14:00 a game | 6.3 | 6.69 | 6.73 | 6.71 | 6.72 |
| First blood time (median s) | 225.0 | 220.0 | 220.0 | 220.0 | 220.0 |
| First tower time (median s) | 905.5 | 889.0 | 926.0 | 927.0 | 922.0 |
| First tower lane: top / mid / bot | 0.436 / 0.106 / 0.457 | 0.393 / 0.252 / 0.355 | 0.414 / 0.189 / 0.397 | 0.418 / 0.189 / 0.393 | 0.409 / 0.186 / 0.405 |
| First dragon: blue share, median time (s) | [0.5, 394.0] | [0.367, 436.0] | [0.465, 434.0] | [0.467, 434.0] | [0.445, 433.0] |
| Grubs to blue (of 3) | 1.87 | 1.73 | 1.87 | 1.87 | 1.86 |
| Lane edge at 15: correlation of the sim's average with the real game | n/a | 0.479 / 0.516 / 0.4 / 0.156 / 0.291 | 0.429 / 0.246 / 0.378 / 0.135 / 0.005 | 0.43 / 0.23 / 0.392 / 0.14 / 0.009 | 0.466 / 0.427 / 0.427 / 0.081 / 0.24 |
| Who wins: log loss | n/a | 0.618 | 0.6155 | 0.608 | 0.6409 |

<sub>Source: research/model/laning/laning_check_wave.json (run record research/runs/20261114T210847Z_laning_check.json, script research/laning/s5_laning_check.py at commit 5894cf3).</sub>
<!-- /table -->

**What the module gets right or better:** first dragon side (the Worlds term), grubs, first tower lane, first blood time, early kills a
game, and who wins (0.608 v 0.618; 200 sims a game, so noisy: the 1,000-sim test is still to run).

**Not right yet:**
- **Team gold too tied to team strength** (about 1,000 gold per unit v real 642). Not the farm: the farm part's link (152) is below the
  real CS part (300). So it comes from the early fights and their gold.
- **Jungle and support lanes don't follow the real games** (correlation 0.23 and 0.01 v the current sim's 0.52 and 0.29), and support
  gold is too spread (563 v 383): support and jungle gold sources (support item quest gold, assist share, jungle camps, grubs) aren't
  all in yet, and plates are split evenly between ADC and support.
- **Mid too spread, ADC too narrow** (867 v 678; 822 v 1,043).

## Fixes, 15 Nov (Luke: jungle and support, then mid / ADC, then team gold)

- **Jungle and support** (`s5_lane_parts.py`, `s5_kill_roles.py`, rule gold split): in real Worlds games a role's gold beyond CS follows its
  own matchup (top, jungle, support about 1,200-1,300 per 1k of expected edge). Who scores or dies inside a fight does **not** follow the
  matchup (no gain at Worlds), so that wasn't it. For the jungler, almost all of it is farm worth more than its CS count (camps,
  scuttles, invades): 1,136 of 1,274 per 1k isn't kill or plate gold. **Fix:** the farm contest is now measured in farm gold (gold earned
  minus what kills, assists, plates, turrets, the quest and passive paid), led by the expected gold edge. Jungle and support now follow
  real games (correlation 0.43 and 0.24, from 0.23 and 0.01); the ADC's spread is right (1,001 v 1,043).
- **Team gold and strength:** across all 2,588 games of 2026, strength adds 593 gold at 15 per unit beyond the expected edges (± 76); at
  Worlds 204 ± 253 (94 games, too few to tell). The module adds 715 at equal expected edges: close. A Worlds-only strength term in the
  fight model made Worlds fights worse (0.663 → 0.712), and the other roles' expected edges don't change the strength effect.
- **Still open:** team gold leads too spread (2,837 v 2,231), mostly mid and support; and who wins (0.641) is now worse, because the module
  still runs on the current sim's calibration (gain 1.604, fitted to the old lane gold). The module needs its own calibration on training
  games, the way `research/sim3/s3_test.py` fits it for every sim version, before who-wins can be judged.

## 1,000-sim Worlds test with the module's own calibration (17 Nov)

The module calibrated on 300 training games before 1 Sep (`s5_calibrate.py`): gain 1.429 (the current sim's is 1.604); win slope on
strength 0.99, so calibration was not the cause. Worlds day by day, 1,000 sims a game, seeds by game ID
(`research/model/laning/laning_check_1000.json`):
- **Who wins: current sim 0.6063, module 0.6228**, worse by 0.017 and outside the noise band (0.6013–0.6069). At 200 sims the module
  was too confident at Worlds (real results moved 0.69 per 1.0 of its odds).
- Kept from the module: first dragon side (0.448 v real 0.50; current 0.368), grubs (1.87, exactly real), first tower lane (mid 0.185 v
  real 0.106; current 0.251).
- Still wrong: team gold at 15 too spread (2,837 v 2,231) and too tied to strength (1,103 v 642 per unit); mid and support spread too wide.
- **Not shippable as it stands.** The Worlds final write-up (`worlds-final-v-sim.md`) points the same way: lane values on their own drive
  too much, and the game state after 15:00 doesn't respond. Next: the game-memory backbone and the 16.20 full-game data.
