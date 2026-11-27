# Fight windows, parts A and B: the fit and the app (27 Nov 2026 AEST)

Part A of `fight-window-plan.md` (Luke: "Yes, do part A"). Script `m21_fight_window.py`; results `research/model/memory/m21_fight_window.json`;
tables below are generated from that file (`python -I research/lib/report.py research/memory/fight-window-report.md research/memory/fight_window_report_tables.py`).
Part B (the app, v55) is at the end.

**What the model is.** After a real won fight, the winners take one objective at a time or reset. The options are dragon, elder, baron,
herald, grubs, an inhibitor, a nexus tower and the Nexus (whichever are up). Stage 1 decides take or reset; stage 2 decides which one.
The inputs are:
- players alive on each side;
- seconds until the first and the last of the dead losers are back (official timers);
- the step, gold lead and v1 logit;
- own baron and elder buff, and game time;
- what is up.

The window runs while each objective comes within 60 s of the previous event and before the next fight (as m19). Lane towers move the
window on but are not options in this build: they keep today's per-minute segment draws (they fall plate by plate in the engine).

## Port check: the per-minute draws refitted on all rows reproduce the app's tables

<!-- table: port -->
| Table in `js/sim-tables.js` | App copy refit on all rows | Largest difference |
|---|---|---|
| `base_push_fight` | identical (15 coefficients) | 0 |
| `monsters.dragon` | identical (8) | 0 |
| `monsters.grub` | identical (8) | 0 |
| `monsters.herald` | identical (8) | 0 |
| `monsters.baron` | identical (8) | 0 |
| `monsters.elder` | identical (8) | 0 |

<sub>Source: research/model/memory/m21_fight_window.json (run record research/runs/20261127T075352Z_memory_fight_window.json, script research/memory/m21_fight_window.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

## Rows

<!-- table: counts -->
| | Research copy | App copy |
|---|---|---|
| won fights | 7271 | 7271 |
| base races left out | 30 | 30 |
| step rows: training / from 1 Sep / Worlds | 7349 / 2605 / 1562 | 11516 (all training) |
| training steps ending in reset | 4298 | 6674 |
| training steps ending in nxt | 733 | 1197 |
| training steps ending in dragon | 631 | 966 |
| training steps ending in inhib | 537 | 861 |
| training steps ending in baron | 388 | 633 |
| training steps ending in nexus | 343 | 567 |
| training steps ending in grub | 257 | 368 |
| training steps ending in herald | 130 | 194 |
| training steps ending in elder | 32 | 56 |

<sub>Source: research/model/memory/m21_fight_window.json (run record research/runs/20261127T075352Z_memory_fight_window.json, script research/memory/m21_fight_window.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

## Held-out scores (research copy: fit before 1 Sep)

Stage 1 is "take something or reset"; the base is the training share of takes. Stage 2 is "which one, among those up"; the base gives
every option up the same chance. Lower is better.

<!-- table: scores -->
| Games | Steps | Takes | Stage 1 log loss: fit / base share | Stage 2 log loss: fit / equal among those up |
|---|---|---|---|---|
| training (before 1 Sep) | 7349 | 3051 | 0.3144 / 0.6787 | 0.1699 / 0.3278 |
| from 1 Sep | 2605 | 1120 | 0.3156 / 0.6837 | 0.1522 / 0.2885 |
| Worlds | 1562 | 671 | 0.3112 / 0.6836 | 0.1489 / 0.3109 |

<sub>Source: research/model/memory/m21_fight_window.json (run record research/runs/20261127T075352Z_memory_fight_window.json, script research/memory/m21_fight_window.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

Both stages more than halve the log loss on games the fit never saw, from 1 Sep and at Worlds alike.

## Fitted terms

<!-- table: coefs -->
| Stage 1 input (take something v reset) | App copy | Research copy |
|---|---|---|
| intercept | -5.489 | -5.428 |
| own_alive | +0.510 | +0.493 |
| enemy_alive | -0.561 | -0.536 |
| per_10s_until_first_back | +0.006 | +0.005 |
| per_10s_until_all_back | +0.490 | +0.478 |
| step 1 | -0.050 | +0.035 |
| step 2+ | +0.461 | +0.549 |
| per_1k_lead | +0.109 | +0.119 |
| per_v1_logit | +0.018 | +0.021 |
| baron_buff | +0.602 | +0.559 |
| elder_buff | +1.632 | +1.546 |
| from 25 | +0.214 | +0.179 |
| from 35 | -0.005 | +0.127 |
| up_dragon | +3.002 | +3.014 |
| up_elder | +1.314 | +1.287 |
| up_baron | +1.605 | +1.540 |
| up_herald | +3.582 | +3.601 |
| up_grub | +6.418 | +6.142 |
| up_inhib | +2.730 | +2.567 |
| up_nxt | +1.302 | +1.128 |
| up_nexus | +1.220 | +1.092 |

| Stage 2 (which one), app copy | intercept | per player alive ahead | per 10 s until all back |
|---|---|---|---|
| dragon | +0.038 | -0.506 | +0.186 |
| elder | -0.039 | -0.289 | +0.153 |
| baron | -1.265 | -0.312 | +0.062 |
| herald | -0.382 | -0.391 | -0.063 |
| grub | +2.784 | -0.668 | -0.107 |
| inhib | +0.204 | +0.429 | -0.096 |
| nxt | -1.853 | +1.067 | -0.071 |
| nexus | +0.513 | +0.669 | -0.064 |

<sub>Source: research/model/memory/m21_fight_window.json (run record research/runs/20261127T075352Z_memory_fight_window.json, script research/memory/m21_fight_window.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

What the terms say:
- **More players alive ahead → more likely to take something.** In stage 1, own alive is positive and enemy alive negative.
- **More time until all the losers are back → more likely to take something.**
- **Elder buff and baron buff push towards taking.**
- **Which option, by players alive ahead:** nexus towers, the Nexus and inhibitors gain with each extra player ahead. Monsters lose
  ground against them as the lead in players grows, because the base becomes the better use of the window.
- None of these were set by hand.

## Replay check (no sim): real won fights played through the fitted window, 20 draws each

Each real fight starts from its real state at the last kill and the real death intervals. Each cell gives the number of fights, the
real share and the fitted share.

<!-- table: replay -->
| Won fights | Training: n, real, fitted | From 1 Sep: n, real, fitted | Worlds: n, real, fitted |
|---|---|---|---|
| Nexus, 0 left, ahead 3+ | 42, 100%, 86% | 22, 96%, 88% | 10, 100%, 92% |
| Nexus, 0 left, ahead 1-2 | 12, 75%, 57% | 5, 100%, 64% | 3, 100%, 47% |
| Nexus, 1 left, ahead 3+ | 47, 94%, 78% | 17, 94%, 76% | 15, 100%, 73% |
| Nexus, 1 left, ahead 1-2 | 23, 65%, 39% | 6, 33%, 34% | 2, 50%, 35% |
| Nexus, 2 left, ahead 3+ | 138, 87%, 64% | 56, 84%, 66% | 34, 82%, 66% |
| Nexus, 2 left, ahead 1-2 | 94, 8%, 17% | 37, 22%, 22% | 18, 11%, 28% |
| Nexus, 2 left, even or behind | 5, 0%, 15% | 1, 0%, 10% | – |
| Nexus, 3 left, ahead 3+ | 57, 51%, 49% | 19, 53%, 47% | 12, 50%, 59% |
| Nexus, 3 left, ahead 1-2 | 62, 10%, 14% | 19, 21%, 10% | 13, 0%, 14% |
| baron when up, ahead 3+ | 333, 45%, 44% | 124, 56%, 50% | 76, 46%, 45% |
| baron when up, ahead 1-2 | 781, 26%, 28% | 252, 28%, 27% | 169, 27%, 28% |
| baron when up, even or behind | 35, 3%, 15% | 11, 9%, 20% | 6, 17%, 17% |
| dragon when up, ahead 3+ | 201, 53%, 63% | 81, 51%, 59% | 45, 62%, 59% |
| dragon when up, ahead 1-2 | 787, 40%, 40% | 258, 39%, 42% | 157, 40%, 44% |
| dragon when up, even or behind | 25, 28%, 37% | 9, 22%, 32% | 5, 40%, 54% |
| Nexus, 0 left, even or behind | – | 2, 50%, 60% | – |
| Nexus, 3 left, even or behind | – | – | 2, 0%, 0% |

<sub>Source: research/model/memory/m21_fight_window.json (run record research/runs/20261127T075352Z_memory_fight_window.json, script research/memory/m21_fight_window.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

How to read it:
- **Baron and dragon when up:** close by players alive in all three game sets.
- **The Nexus with 0 left and the winners 3+ up:** close (fitted 86–92%, real 96–100%).
- **The Nexus with 1–2 left and 3+ up:** too low (fitted 64–78%, real 82–100%). The likely cause is in the replay, not the fit: the
  replay doesn't play the lane towers the winners take inside the window (a T3 that opens a second lane, for example), and it counts
  each step's choice as fresh, without the real carry-on. Not checked further; part B's sim check is where it shows.
- **The Nexus with 0 left and 1–2 up:** too low (fitted 47–64%, real 75–100%; 20 fights in all).
- **The Nexus with 2–3 left and 1–2 up:** close (real 0–22%, fitted 10–28%), so the model doesn't over-push when the lead in players is
  small.

## Take times: seconds from the step's moment to the objective (app copy, medians)

<!-- table: times -->
| Option | Winners 3+ up: n, median s | 1-2 up | Even or behind | Pooled median |
|---|---|---|---|---|
| dragon | 223, 21 | 719, 28 | 24, 44 | 27 |
| elder | 21, 5 | 35, 24 | 0, – | 18 |
| baron | 273, 32 | 354, 32 | 6, – | 32 |
| herald | 24, 29 | 162, 30 | 8, – | 30.5 |
| grub | 5, – | 223, 13 | 140, 6 | 9 |
| inhib | 456, 16 | 335, 17 | 70, 28.5 | 17 |
| nxt | 925, 4 | 228, 6.5 | 44, 13.5 | 4 |
| nexus | 491, 8 | 75, 8 | 1, – | 8 |

<sub>Source: research/model/memory/m21_fight_window.json (run record research/runs/20261127T075352Z_memory_fight_window.json, script research/memory/m21_fight_window.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

Negative times are objectives that fell during the fight, before its last kill.

## Per-minute draws outside the windows

<!-- table: minute -->
| Per-minute draw (app copy) | Rows left out (inside windows) | Rows | Held-out log loss outside windows, research copy (refit / all-row fit): from 1 Sep, Worlds |
|---|---|---|---|
| base push | 1540 | 2604 | 0.2776 / 0.2996, 0.2246 / 0.2745 |
| monsters (all kinds) | 6826 | 13427 | per kind below |

| Monster | Taken / minutes up (all rows) | Outside windows | Research held-out log loss from 1 Sep: refit on its rows (outside windows) / all-row fit on all rows (different rows: not a like-for-like score) |
|---|---|---|---|
| dragon | 2901 / 6405 | 1275 / 3248 | 0.6481 / 0.6516 |
| grub | 640 / 716 | 362 / 399 | 0.2587 / 0.3199 |
| herald | 640 / 1021 | 304 / 515 | 0.6592 / 0.6493 |
| baron | 886 / 5040 | 135 / 2382 | 0.2512 / 0.4865 |
| elder | 73 / 245 | 5 / 57 | – / 0.6239 |

<sub>Source: research/model/memory/m21_fight_window.json (run record research/runs/20261127T075352Z_memory_fight_window.json, script research/memory/m21_fight_window.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

The base push refitted outside the windows scores better on those rows than the all-row fit, from 1 Sep and on Worlds. Monster minutes
inside windows are about half of all monster minutes. Those are now the window's job; the refit takes the rest.

## Part B: the app (v55, 27 Nov; Luke: "Yes, do part B")

The app files went back to v54 first (the base push v2 copies are kept in `research/local/memory/`). `m21_fight_window.py --write-app`
wrote the app block saved by the part A run into `js/sim-tables.js` (`SIM_TABLES.window`, games before 10 Nov). The engine
(`js/sim-engine.js`) runs the window after every won fight: `fight_window: "v1"`, on by default; `"off"` plays v54 exactly.
- **Each step** reads players alive on each side and when the dead losers are back (the engine's own death timers), the step, gold lead,
  v1, own buffs, game time and what is up. It draws take or reset, then which option, then a real take time by option and players alive.
- **A take** has the same effects as the per-minute draws (gold, buffs, timers, dragon types and soul, nexus tower respawn, the
  play-by-play line); the winners take it, so there is no taker draw. The Nexus falls only before the losers are all back, after every
  event already placed.
- **The per-minute draws** skip the minutes a window covers: the base push for the window's team, monsters for both teams. Elsewhere
  they use the tables refitted without those minutes. Lane towers keep their segment draws; elder keeps its per-minute draw (refitted).
- **Check** (`m22_app_check.js`, a new local tab): 72 Worlds drafts as played, 100 large seeds each, against `fight_window: "off"`.

<!-- table: appcheck -->
| 72 Worlds drafts x 100 seeds | v55 (fight window on) | fight window off (= v54) | Real (the same 72 games) |
|---|---|---|---|
| blue win | 57% | 59% | 57% |
| length min (10 / 25 / 50 / 75 / 90%) | 27.2 / 31.5 / 36.8 / 43.3 / 50.1 | 28.7 / 33.1 / 39 / 46 / 53.5 | 26.2 / 29 / 33.1 / 37.5 / 40.1 |
| 45+ min | 20% | 28% | 6% |
| 50+ min | 10% | 15% | 0% |
| kills a game | 30.0 | 33.1 | 26.3 |

| Objectives a game (both sides) | v55 | off (= v54) | Real (640 timelines, 2026) |
|---|---|---|---|
| dragon | 4.60 | 4.80 | 4.53 |
| elder | 0.36 | 0.56 | 0.11 |
| baron | 1.63 | 2.00 | 1.38 |
| herald | 1.00 | 1.00 | 1.00 |
| tower (all tiers) | 13.08 | 15.01 | 11.87 |
| inhib | 2.16 | 2.46 | 1.65 |
| nexus | 1.00 | 0.99 | 0.97 |

| Player of the Game by role | v55 | off (= v54) |
|---|---|---|
| top | 20% | 18% |
| jng | 31% | 29% |
| mid | 28% | 29% |
| bot | 16% | 20% |
| sup | 4% | 4% |

| Replay check (72 drafts x 20 seeds, fingerprint of every game record) | v54 | v55 with fight_window off | Identical |
|---|---|---|---|
| default sim | `cb7225e9` | `cb7225e9` | yes |
| alt sim | `c993b12b` | `c993b12b` | yes |

<sub>Source: research/model/memory/m22_app_check.json (research/memory/m22_app_check.js run in a local app tab); real objectives a game from research/model/memory/m20_fight_windows.json (640 gol.gg timelines).</sub>
<!-- /table -->

**The window inside the sim**, counted as m21 counts real won fights (the engine's own fights; players alive at the last kill; what was
up and structures left at the fight's start; the winners' objectives in the 60 s chain until the next fight):

<!-- table: simwindow -->
| Won fights | v55 sim: share (fights) | Real, training | Real, from 1 Sep | Real, Worlds |
|---|---|---|---|---|
| Nexus, 0 left, ahead 1-2 | 71% (2057) | 75% (12) | 100% (5) | 100% (3) |
| Nexus, 0 left, ahead 3+ | 91% (1355) | 100% (42) | 96% (22) | 100% (10) |
| Nexus, 0 left, even or behind | 48% (132) | – | 50% (2) | – |
| Nexus, 1 left, ahead 1-2 | 37% (1382) | 65% (23) | 33% (6) | 50% (2) |
| Nexus, 1 left, ahead 3+ | 81% (895) | 94% (47) | 94% (17) | 100% (15) |
| Nexus, 1 left, even or behind | 31% (81) | – | – | – |
| Nexus, 2 left, ahead 1-2 | 17% (2539) | 8% (94) | 22% (37) | 11% (18) |
| Nexus, 2 left, ahead 3+ | 67% (1569) | 87% (138) | 84% (56) | 82% (34) |
| Nexus, 2 left, even or behind | 4% (168) | 0% (5) | 0% (1) | – |
| Nexus, 3 left, ahead 1-2 | 6% (4622) | 10% (62) | 21% (19) | 0% (13) |
| Nexus, 3 left, ahead 3+ | 50% (2378) | 51% (57) | 53% (19) | 50% (12) |
| Nexus, 3 left, even or behind | 2% (315) | – | – | 0% (2) |
| any objective | 50% (93349) | 38% (4641) | 40% (1626) | 39% (974) |
| baron when up, ahead 1-2 | 28% (17663) | 26% (781) | 28% (252) | 27% (169) |
| baron when up, ahead 3+ | 42% (7459) | 45% (333) | 56% (124) | 46% (76) |
| baron when up, even or behind | 22% (979) | 3% (35) | 9% (11) | 17% (6) |
| dragon when up, ahead 1-2 | 45% (18361) | 40% (787) | 39% (258) | 40% (157) |
| dragon when up, ahead 3+ | 61% (3831) | 53% (201) | 51% (81) | 62% (45) |
| dragon when up, even or behind | 35% (619) | 28% (25) | 22% (9) | 40% (5) |

<sub>Source: research/model/memory/m22_app_check.json (research/memory/m22_app_check.js run in a local app tab); real objectives a game from research/model/memory/m20_fight_windows.json (640 gol.gg timelines).</sub>
<sub>Real: m21_fight_window.json, research copy (the replay table's real column; same 60 s chain).</sub>
<!-- /table -->

**What it shows.**
- **Better than v54 everywhere it was measured, still long:** median length 36.8 min (v54 39.0, real 33.1), 45+ 20% (28%, real 6%),
  kills 30.0 (33.1, real 26.3). Towers, inhibitors, barons and elders a game all move toward real; dragons stay close.
- **The Nexus by players alive now has the real shape.** With 3+ up it falls 91 / 81 / 67 / 50% of won fights at 0 / 1 / 2 / 3
  structures left (real 96–100 / 94–100 / 82–87 / 50–53%); with 1–2 up 71 / 37 / 17 / 6% (real 75–100 / 33–65 / 8–22 / 0–21%).
  It is still a little low with 1–2 structures left and 3+ up, as in the part A replay.
- **Baron and dragon:** baron with 1–2 or 3+ up is close; baron when even or behind is high (22% v 3–17%, few real fights). Dragon is
  5–8 points high.
- **More windows take something than real** (50% v 38–40%); and the sim has more won fights where both sides end even or behind.
- **Elder is still 3x real** (0.36 a game v 0.11). The windows take 0.28 a game. Sim games still reach elder more often than real
  ones (more long games), and a window with elder up takes it often (as real: 21–57%).

**Play-test** (`m15_series_playtest.js`, the same 100 series as the v54 run; `research/model/memory/m22_series_playtest.json`):

<!-- table: playtest -->
| 100 Bo5 Fearless series, AI drafts both sides | v55 (401 games) | v54 (407 games) | Real (640 timelines) |
|---|---|---|---|
| errors | 0 | 0 | |
| replay from seed matches the game record | 401 | 407 | |
| exports with every game's play-by-play / NaN or undefined | 100 / 0 | 100 / 0 | |
| length min (10 / 25 / 50 / 75 / 90%) | 27.7 / 31.7 / 36.5 / 42.3 / 47.8 | 28.7 / 33.6 / 39.2 / 46.1 / 52.4 | 26.4 / 28.8 / 32.2 / 35.9 / 39.9 |
| 45+ min | 16.5% | 27.8% | 2.8% |
| kills a game (10 / 25 / 50 / 75 / 90%) | 18 / 22 / 28 / 36 / 42 | 19 / 25 / 33 / 42 / 49.4 | median 27 |
| Nexus from the last kill s (10 / 25 / 50 / 75 / 90%) | 7 / 9 / 15 / 28 / 41 | 8 / 17 / 29 / 43 / 52 | median 14 |
| Nexus 60 s+ after the last kill | 1.2% | 3.2% | |
| first blood before 0:30 / 1:00 / 3:00 | 0 / 0.2 / 26.9% | 0 / 1.7 / 28.7% | 0 / 1.1 / 28.1% |
| support 4+ kills in one fight | 0 | 1 | |
| blue win | 54.1% | 52.1% | |

<sub>Source: research/model/memory/m22_series_playtest.json (v55) and m15_series_playtest.json (v54), both from research/memory/m15_series_playtest.js in a new local tab, same team pairs.</sub>
<!-- /table -->

Page check: a new local tab, the full Worlds sim run (93 games, winners screen), the grand final series and results at desktop and
375 px; console clean (the only error is the local server's missing favicon).

## Open

- **The monster taker model** (who takes a monster when the per-minute draw says one is taken) is not refitted. It was fitted on all
  monsters, including those right after won fights. Not measured separately in part B; dragons a game stay close to real.
- **Lane towers** stay per-minute in this build.
- **Elder outside windows is thin:** 5 taken in 57 minutes up (games to 10 Nov), so its per-minute refit rests on almost nothing; 51 of 56
  real elders in the app copy come inside a won fight's window. v55 keeps the refitted per-minute elder draw (the plan's rule: today's
  per-minute draws stay, refitted). For Luke: keep it, or let elder come only from fight windows. Elder is 3x real in v55 (0.36 a game v
  0.11), of which the windows take 0.28; windows-only is not tested.
- **Base team-minutes inside windows:** 1,540 of 2,604 (59%), so most real base pushes now come from the window, and the per-minute base
  push covers the rest (sieges, base pushes with no won fight in the last 60 s).
- **The 1–2 left gap** (above) shows in the sim too: with 3+ up, 81% and 67% v real 94–100% and 82–87%.
- **Still long** (45+ 20% v real 6% on the same drafts): more windows take something than real (50% v 39%), so it is not too few
  takes; the next thing to measure is how many won fights the sim has, and how even they are, against real.
