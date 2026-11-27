# Base push learns the game state: part A, the fit (27 Nov 2026 AEST)

The plan is in `base-push-plan.md` (Luke OK'd part A on 27 Nov). The script is `m17_base_push_state.py` and the results are in
`research/model/memory/m17_base_push_state.json`. Every table below is generated from that file (`base_push_report_tables.py`). Nothing in
the app was changed: the app table block is kept in the result file and is written to `js/sim-tables.js` only by `--app` (part B).

## Port check

<!-- table: port -->
| Check | Result |
|---|---|
| App copy's refit of today's inputs v `base_push_fight` in `js/sim-tables.js` | identical (15 coefficients, largest difference 0) |

<sub>Source: research/model/memory/m17_base_push_state.json (run record research/runs/20261127T015744Z_memory_base_push_state.json, script research/memory/m17_base_push_state.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

## Held-out scores (log loss of "a base push starts this minute", lower is better)

The team-minutes are those with a lane open, from the gol.gg timelines. The research copy was fitted before 1 Sep. "From 1 Sep" and "Worlds"
are held-out games. The app copy is fitted on every game to 10 Nov, so its score is in-sample.

<!-- table: scores -->
| Version | Research: training | Research: from 1 Sep | Research: Worlds | App copy: games to 10 Nov (in-sample) |
|---|---|---|---|---|
| today's inputs | 0.4125 | 0.4220 | 0.3845 | 0.4113 |
| + structures left | 0.4066 | 0.4219 | 0.3833 | 0.4078 |
| + dead | 0.4041 | 0.4160 | 0.3751 | 0.4003 |
| + base under attack | 0.4118 | 0.4217 | 0.3838 | 0.4108 |
| all (chosen) | 0.3951 | 0.4129 | 0.3699 | 0.3949 |
| team-minutes | 1636 | 578 | 390 | 2604 |

<sub>Source: research/model/memory/m17_base_push_state.json (run record research/runs/20261127T015744Z_memory_base_push_state.json, script research/memory/m17_base_push_state.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

- **All three new input groups help on held-out games, and together most of all:** from 1 Sep 0.4220 → 0.4129, Worlds 0.3845 → 0.3699.
- **Dead players carry most of the gain**, as the 14 Nov fit found. Structures left and base under attack add a little on their own.
- **The form of "structures left" was chosen on training games only** (fit on the earlier half of the training dates, judge the later half).
  The two copies chose differently (research: dummies; app: one slope). Both kept the "0 left × enemies dead" term.

<!-- table: choice -->
| Version | Research copy | App copy |
|---|---|---|
| linear | 0.4188 | 0.3992 |
| linear + interaction | 0.4154 | 0.3978 |
| dummies | 0.4143 | 0.4014 |
| dummies + interaction | 0.4113 | 0.3990 |
| today's inputs | 0.4272 | 0.4113 |
| **chosen** | dummies, interaction kept | linear, interaction kept |
| fit / check minutes (split 2026-08-09) | 769 / 867 | 1536 / 1068 |

<sub>Source: research/model/memory/m17_base_push_state.json (run record research/runs/20261127T015744Z_memory_base_push_state.json, script research/memory/m17_base_push_state.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

## Coefficients

<!-- table: coefs -->
| Input | Today (app) | New fit, app copy | New fit, research copy |
|---|---|---|---|
| intercept | -3.644 | -4.407 | -3.809 |
| from 25 | +0.475 | +0.393 | +0.398 |
| from 35 | +0.153 | +0.117 | +0.235 |
| per_1k_lead | +0.008 | +0.012 | +0.013 |
| per_v1_logit | -0.008 | +0.004 | -0.018 |
| baron | +0.667 | +0.723 | +0.636 |
| elder | +0.909 | +1.073 | +0.845 |
| enemy_inhibs_down | -0.034 | +0.121 | +0.475 |
| open_lanes | +0.824 | +0.827 | +0.874 |
| siege_style_sum | -0.276 | -0.250 | -0.192 |
| lane_just_opened | +1.541 | +1.483 | +1.343 |
| base_take_last_minute | -3.312 | -3.237 | -3.089 |
| net_kills_this_minute | +0.563 | +0.064 | +0.042 |
| net_kills_last_minute | +0.407 | +0.006 | +0.011 |
| clear_fight_win | -0.177 | -0.320 | +0.177 |
| structures_left | – | +0.179 | – |
| enemies_dead_max | – | +0.603 | +0.522 |
| own_dead_max | – | -0.270 | -0.193 |
| own_base_under_attack | – | -0.593 | -0.556 |
| left 0 x enemies_dead | – | -0.327 | -0.586 |
| left 0 | – | – | -0.514 |
| left 1 | – | – | -1.288 |
| left 2 | – | – | -0.900 |

<sub>Source: research/model/memory/m17_base_push_state.json (run record research/runs/20261127T015744Z_memory_base_push_state.json, script research/memory/m17_base_push_state.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

- **Enemies dead** pushes the chance up and **own dead** pulls it down. **Own base under attack** pulls it down: the side being pushed
  doesn't push back. This is Luke's 21 Nov example, now coming out of the fit.
- With the dead counts in, **this minute's and last minute's kills edge** fall to about zero, and the app copy's **clear fight win** turns
  negative. The dead counts carry what those terms used to. All are kept (Luke, 12 Nov: keep every input).

## What the real minutes show, and the catch

<!-- table: descriptive -->
**push start share by structures left** (games to 10 Nov)

| Value | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Share of minutes a push starts | 9% | 15% | 26% | 53% |
| Team-minutes | 157 | 176 | 931 | 1340 |

**push start share by enemies dead** (games to 10 Nov)

| Value | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Share of minutes a push starts | 15% | 32% | 38% | 49% | 61% |
| Team-minutes | 793 | 460 | 242 | 295 | 814 |

**push start share, 0 left, by enemies dead** (games to 10 Nov)

| Value | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Share of minutes a push starts | 0% | 26% | 8% | 11% | 6% |
| Team-minutes | 12 | 19 | 13 | 28 | 85 |

**push start share by own base under attack** (games to 10 Nov)

| Value | 0 | 1 |
|---|---|---|
| Share of minutes a push starts | 39% | 16% |
| Team-minutes | 2542 | 62 |

<sub>Source: research/model/memory/m17_base_push_state.json (run record research/runs/20261127T015744Z_memory_base_push_state.json, script research/memory/m17_base_push_state.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

- **A new push rarely starts in a minute that begins with the Nexus exposed** (0 left: 9% of minutes, against 53% with 3 left). The
  structures-left terms are negative, not positive.
- **This is selection, not reluctance:**
  - in real games, the push that takes the nexus towers usually goes straight on to the Nexus within 30 s;
  - so a minute that *starts* with 0 left is a minute where that push stopped (the defenders held or respawned);
  - a push counts as starting only in its first minute (one side's base structures under 30 s apart, as `s3_rates.py`), so the minute
    the Nexus falls in a push begun the minute before counts as "no start". The engine matches this: it draws a whole push, with its
    size, in one minute, and its "base take last minute" term (−3.2) holds back a second push straight after;
  - real won fights with 0 left at the fight's start still end in the Nexus 94% of the time (table below).
- **What this means for the plan:**
  - the per-minute push draw won't, on its own, make the sim end games from an exposed Nexus;
  - the sim reaches that state far more often than real games (0.76 won 0-left fights a game against 0.15, `m16_nexus_sim.json`);
  - real games end in the push that opens the base, so the part that matters is **the push going on to the Nexus**: push sizes by
    structures left, real base gaps, and the Nexus time.
- **Not checked until part B:** whether the fitted draw, the size tables and the gaps together shorten the sim's games. The fitted terms
  could even lengthen them slightly at 0 left, though by the minute those rows describe, real games have mostly ended already.

## Push sizes by structures left at the push's start

<!-- table: sizes -->
| Structures left at the push's start | Pushes (to 1 Sep / to 10 Nov) | Size shares (to 10 Nov) | Push ends in the Nexus (to 10 Nov) |
|---|---|---|---|
| 0 | 10 / 16 | 1: 88%, 2: 12% | 100% |
| 1 | 20 / 29 | 1: 17%, 2: 55%, 3: 28% | 76% |
| 2 | 148 / 240 | 1: 20%, 2: 5%, 3: 38%, 4: 33%, 5: 5% | 72% |
| 3 | 447 / 726 | 1: 29%, 2: 11%, 3: 3%, 4: 45%, 5: 11%, 6: 1% | 56% |

<sub>Source: research/model/memory/m17_base_push_state.json (run record research/runs/20261127T015744Z_memory_base_push_state.json, script research/memory/m17_base_push_state.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

- **Pushes from 0 or 1 left are rare:** 16 and 29 to 10 Nov. The app block keeps size tables only where there are 30+ pushes (2 and 3
  left). For 0 and 1 left the engine would fall back to today's table (by inhibitor down).
- **From 3 left, size 4 (inhibitor, both nexus towers, the Nexus) is the most common push (45%),** and 56% of these pushes end in the Nexus.

## Gaps between base structures

All of one side's consecutive structures where the later one is an inhibitor or nexus tower, under 60 s. m16 measured inside won-fight
pushes only, so its medians differ a little.

<!-- table: gaps -->
| Previous > this structure | Gap s, 10/25/50/75/90% (to 10 Nov) | Gaps (to 1 Sep / to 10 Nov) |
|---|---|---|
| T3>inhib | 3 / 3 / 5 / 7 / 13 | 498 / 813 |
| T3>nxt | 2 / 2 / 6 / 12 / 25 | 27 / 45 |
| inhib>inhib | 1 / 3 / 5 / 10 / 21 | 55 / 85 |
| inhib>nxt | 5 / 7 / 9 / 13 / 21 | 360 / 576 |
| nxt>inhib | 0 / 2 / 4 / 8 / 13.8 | 32 / 43 |
| nxt>nxt | 1 / 3 / 4 / 6 / 13 | 355 / 581 |
| outer>inhib | 3.2 / 5.5 / 8 / 21 / 28 | 16 / 23 |
| outer>nxt | 4.6 / 7 / 30 / 46 / 51 | 10 / 17 |
| all base gaps pooled | 2 / 3 / 6 / 9 / 17 | 1353 / 2183 |

<sub>Source: research/model/memory/m17_base_push_state.json (run record research/runs/20261127T015744Z_memory_base_push_state.json, script research/memory/m17_base_push_state.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

## The Nexus after a won fight, by structures left at the fight's start

<!-- table: nexus -->
| Structures left at the fight's start | Won fights (to 10 Nov) | Nexus in the push | Nexus from the last kill s, 10/25/50/75/90% (to 10 Nov) |
|---|---|---|---|
| 0 | 97 | 91 (94%) | 5 / 6 / 7 / 9 / 12 |
| 1 | 111 | 93 (84%) | 6 / 8 / 9 / 12 / 16.8 |
| 2 | 383 | 213 (56%) | 6 / 9 / 15 / 22 / 30.8 |
| 3 | 186 | 55 (30%) | 10.4 / 21 / 28 / 36 / 39.6 |

<sub>Source: research/model/memory/m17_base_push_state.json (run record research/runs/20261127T015744Z_memory_base_push_state.json, script research/memory/m17_base_push_state.py at commit 0df8bfd with uncommitted edits).</sub>
<!-- /table -->

## For part B (not built)

- **The engine's push draw needs three state counts:**
  - structures left at the minute's start: `nxTowers` plus 1 if no inhibitor is down;
  - the most enemy and own players dead at once in the minute: the engine knows each death and respawn, but doesn't yet keep the
    death times, so it needs a small list per side;
  - own base structures lost in the minute before.
- **The tables (app block):**
  - push size by structures left, for 2 and 3 left;
  - gaps by pair (the pooled table where a pair has under 20 gaps);
  - the Nexus from the last kill by structures left at the fight's start (all four have 55+ fights).
- **Where the sim's pushes stop short:** a push drawn with enough size reaches the Nexus step and stops there when the last fight wasn't won
  by the pusher or the losers are back first (the v51 check). The 27 Nov trace counted 785 of those stops ("Nexus draw later than the
  losers' respawn"). The real Nexus timing by structures left (median 7 s from the last kill with 0 left) is the fitted answer to that;
  the check itself stays (real: never 60 s+ after the last kill).
- **The main question for part B** is whether the sizes and the Nexus timing end games inside the push that opens the base. I'd measure it
  the same way as `m16_nexus_sim.js` (open-base phase, structures-left table, length), with `base_push: "off"` replaying v54.
