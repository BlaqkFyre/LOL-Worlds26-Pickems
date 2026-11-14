# Laning slice, first build: results (14 Nov 2026 AEST)

The laning module is in the research sim (`research/sim3/s3_sim.py`, option `cal["laning"] = "actions"`, off by default). Tables:
`research/laning/s5_fit_laning.py` (one fit per Worlds day, each on games before that day). Design: `research/laning/step3-design.md`.

**Replay:** with the option off, 642 of 642 seeded games are identical to the sim before the edit (`research/laning/s5_replay_check.py`).

**Worlds, day by day** (`research/laning/s5_laning_check.py`; both versions with death timers and the same calibration; "waves" = the
measured alternation of CS minutes, lag-1 correlation −0.12 to −0.27 by role):

<!-- table: check -->
| Measure (Worlds, 94 games, 200 sims each) | Real | Current sim | Module | Module + waves |
|---|---|---|---|---|
| Lane gold edge at 15, spread: top / jng / mid / ADC / sup | 995 / 786 / 678 / 1043 / 383 | 936 / 839 / 832 / 992 / 446 | 909 / 788 / 902 / 869 / 570 | 869 / 755 / 867 / 822 / 563 |
| Lane gold edge at 10, spread | 599 / 535 / 411 / 594 / 319 | 600 / 542 / 549 / 659 / 311 | 540 / 512 / 553 / 535 / 362 | 506 / 481 / 521 / 495 / 357 |
| Team gold edge at 15: spread, gold per unit of strength | [2231, 642] | [2591, 770] | [2619, 996] | [2540, 996] |
| Kills before 14:00 a game | 6.3 | 6.69 | 6.73 | 6.71 |
| First blood time (median s) | 225.0 | 220.0 | 220.0 | 220.0 |
| First tower time (median s) | 905.5 | 889.0 | 926.0 | 927.0 |
| First tower lane: top / mid / bot | 0.436 / 0.106 / 0.457 | 0.393 / 0.252 / 0.355 | 0.414 / 0.189 / 0.397 | 0.418 / 0.189 / 0.393 |
| First dragon: blue share, median time (s) | [0.5, 394.0] | [0.367, 436.0] | [0.465, 434.0] | [0.467, 434.0] |
| Grubs to blue (of 3) | 1.87 | 1.73 | 1.87 | 1.87 |
| Lane edge at 15: correlation of the sim's average with the real game | n/a | 0.479 / 0.516 / 0.4 / 0.156 / 0.291 | 0.429 / 0.246 / 0.378 / 0.135 / 0.005 | 0.43 / 0.23 / 0.392 / 0.14 / 0.009 |
| Who wins: log loss | n/a | 0.618 | 0.6155 | 0.608 |

<sub>Source: research/model/laning/laning_check_wave.json (run record research/runs/20261114T111241Z_laning_check.json, script research/laning/s5_laning_check.py at commit 7e7e0cb with uncommitted edits).</sub>
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
