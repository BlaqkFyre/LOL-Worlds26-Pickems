# Laning slice, step 1: what the data supports (14 Nov 2026 AEST)

Plan: `research/laning-plan.md`. Scripts: `s5_lane_edges.py` (lane edges at 10 and 15), `s5_early_habits.py` (habits before 14:00 and team
early priority). Results: `research/model/laning/lane_edges.json`, `lane_edges_minor.json`, `early_habits.json`. Logs in `research/local/`.
Every shrink and half-life was chosen on training games only (fit before 1 Aug, judged on August). Tests: Worlds day by day (fit on every
game before each Worlds day), then 2026 non-Worlds games from 1 Sep (fit before 1 Sep).

## 1. Lane edges: who wins the lane (gold edge at 15 and 10, every role)

2,736 major-league games with gold at 15, 94 at Worlds. Error = mean squared error of the gold edge (lower is better); "right" = share of
lanes whose winner the model calls correctly.

<!-- table: lane_edges -->
| Version (each adds one input) | Worlds error at 15 | Worlds right | 2026 error at 15 | 2026 right | Worlds error at 10 |
|---|---|---|---|---|---|
| role + side only | 665k | 54.0% | 744k | 52.6% | 255k |
| + player lane skill | 661k | 56.6% | 715k | 57.7% | 250k |
| + champion | 585k | 61.7% | 659k | 61.3% | 218k |
| + matchup | 583k | 62.8% | 657k | 61.6% | 218k |
| + comfort (games on champ) | 582k | 63.4% | 658k | 61.7% | 219k |
| + player x champion | 582k | 63.4% | 658k | 61.7% | 218k |
| + team strength (v1, as the current sim) | 581k | 63.0% | 650k | 61.9% | 217k |
| Current sim's lane inputs (skill gap, champion gold, team strength) | 579k | 63.4% | 642k | 59.7% | 225k |

<sub>Source: research/model/laning/lane_edges.json (run record research/runs/20261114T041920Z_lane_edges.json, script research\laning\s5_lane_edges.py at commit 529caf2 with uncommitted edits).</sub>
<!-- /table -->

- **Champion lane strength is by far the biggest input** (the shrink chosen on training is small, so champion effects are strong). The best
  champion fit uses no fade by date: the whole 2026 record, not only recent patches, predicts Worlds lanes best.
- **Player lane skill is a real, stable trait**: a player's effect on odd games agrees with his effect on even games (correlation 0.73 top,
  0.57 jungle, 0.67 mid, 0.67 ADC, 0.59 support, 46–55 players per role). Its effect is smaller than the champion's.
- **Matchup**: a small gain in both tests at 15.
- **Team strength** adds a clear gain on 2026 (659k → 650k) and a little at Worlds: teammates (jungle help) shape lanes too.
- **Comfort and player x champion**: no gain on lane results in either test. Comfort doesn't make a player lane better in this data; it
  still matters for what gets picked (draft).
- **Against the current sim's inputs**: about level. The full model is a little worse at 15 (581k v 579k Worlds, 650k v 642k 2026) and
  better at 10 on Worlds (217k v 225k). The current inputs had a head start (their skill table was built on the full file, test games
  included). The difference: the new model says *why* a lane is won (who, on what, against what).
- **Minor leagues on 16.20** (207 games, champion and matchup data only): worse at 15 on Worlds (581k → 584k), slightly better at 10
  (217k → 216k). Not kept.

## 2. Habits before 14:00 (gol.gg timelines: 640 games; LCK 153, LEC 137, LCS 103, CBLOL 102, Worlds 94, EWC 51; no LPL)

4,263 of 4,288 early kills matched to roles. "Own habit" = the player's or team's own value pulled toward the average.

| Habit | Stable from game to game? (odd v even games) | Predicts held-out games? |
|---|---|---|
| Jungler: which lane his early kills are in (bot 38%, jungle 25%, mid 19%, top 19% overall) | No (−0.31, 24 junglers) | No (Worlds 1.375 v average 1.372) |
| Jungler: how many early kills he's in (2.3 a game) | Weak (0.38, 23 junglers) | No (Worlds worse; 2026 level) |
| Mid roams (0.8 a game) | Weak (0.33) | No at Worlds; tiny gain 2026 |
| Support roams (1.0 a game) | Weak (0.41) | No (worse in both) |
| Solo kills by lane (top 0.12, mid 0.06, bot 0.03 a game) | No (−0.10 to 0.17) | No |
| **Team: grubs (2+ of the first 3)** | **Yes (0.60, 54 teams)** | **Yes: Worlds log loss 0.670 → 0.634; 2026 0.669 → 0.657** |
| Team: first dragon | Weak (0.27) | No |

- **Players' early habits don't hold up as player traits** in this data: about 25 timeline games per player before September, LPL players
  only from internationals, and failed ganks leave no trace. So where ganks and roams go should come from game state and champions, which
  is the next test (below), not from the player.
- **Grubs priority is a real team trait** and predicts Worlds games.
- **First dragon at Worlds:** the 2026 model (side, strength, bot and mid edges at 10) scores worse than a coin flip on Worlds games
  (0.767 v 0.693). Through 2026, red side took first dragon far more often (intercept −0.65 for blue); at Worlds it didn't. A patch or
  Worlds-specific pattern, so for the slice, side effects on objectives come from Worlds and 16.20 first.

## 2b. Do ganks and roams follow the game state? (`s5_gank_state.py`, `research/model/laning/gank_state.json`)

State at the start of the kill's minute: each lane's gold edge (timeline gold per role per minute), dragon up or within 60 s, grubs up or
within 60 s (spawn times read from the timelines: first dragon never before 5:22, dragons at least 306 s apart, first grub 8:04), the
side's total edge, and the jungle champion's own early-kill rate. Log loss for the lane (lower is better), Poisson deviance for pace.

<!-- table: gank_state -->
| Question | Constants only (Worlds / 2026) | With game state (Worlds / 2026) |
|---|---|---|
| Which lane the jungler's early kills are in (2,902 kills) | 1.3719 / 1.3502 | 1.3720 / 1.3491 |
| Which lane the mid's early kills are in (2,282 kills) | 1.3499 / 1.3318 | 1.3532 / 1.3345 |
| Which lane the support's early kills are in (2,750 kills) | 1.1458 / 1.1751 | 1.1466 / 1.1758 |
| Jungler early kills per minute (15,360 side-minutes) | 0.6853 / 0.7084 | 0.6882 / 0.7029 |

<sub>Source: research/model/laning/gank_state.json (run record research/runs/20261114T042444Z_gank_state.json, script research\laning\s5_gank_state.py at commit 529caf2 with uncommitted edits).</sub>
<!-- /table -->

- **The lane of early kills doesn't follow lane states, objectives or the jungle champion** in this data. The shares are steady: jungler
  kills bot 38%, jungle 25%, mid 19%, top 19%; mid's kills mid 31%, bot 31%, jungle 26%, top 12%; support's bot 52%, jungle 22%, mid 15%,
  top 11%.
- **Pace** rises through the early game (more jungler kills each 2-minute window to 14:00) and a little when dragon or grubs are up; that
  holds on 2026 but not on Worlds.
- **Why this may be the data, not the game:** a timeline only records kills. Ganks that fail, lanes that are pressured without a kill,
  and where the jungler was are invisible. Answering "where does the jungler go" needs positions or jungle camp data. The Oracle's
  Elixir file and gol.gg don't have them; whether any other source does is not checked.

## 2c. Who wins early fights? (`s5_fight_winner.py`, `research/model/laning/fight_winner.json`)

2,314 fights before 14:00 that weren't even trades (kills 20 s+ apart start a new fight), from timeline games. Inputs, blue minus red, for
the roles that took part: the step 1 lane model's expected edge at 10 (players, champions, matchup; never fitted on the game itself),
team strength, and those roles' gold edge at the start of the fight's minute. Log loss (lower is better).

<!-- table: fight_winner -->
| Version | Worlds day by day (301 fights) | 2026 from 1 Sep (511) |
|---|---|---|
| side only | 0.6894 | 0.6918 |
| + pre-game players and champions | 0.6772 | 0.6932 |
| + team strength | 0.6675 | 0.6845 |
| + lane state at the time | 0.6608 | 0.6792 |
| lane state only | 0.6730 | 0.6849 |

<sub>Source: research/model/laning/fight_winner.json (run record research/runs/20261114T042455Z_fight_winner.json, script research\laning\s5_fight_winner.py at commit 529caf2 with uncommitted edits).</sub>
<!-- /table -->

- **Yes, at Worlds the stronger players and champions for the roles in a fight win it more often**, and team strength and the lane so
  far add to it. On 2026 games players and champions alone don't help, but the full version is best on both.
- Fights split into fifths by the pre-game edge: the blue side wins 47% when weakest, 50%, 56%, 52%, and 62% when strongest.
- All three inputs come out positive when fitted on every fight: players and champions 0.18 per 1k of expected edge, team strength 0.30,
  lane state 0.31 per 1k.

## 2d. The other laning actions (`s5_lane_actions.py`, `research/model/laning/lane_actions.json`)

Timeline games, state at the time. Lower is better (Poisson deviance or log loss). Worlds day by day / 2026 non-Worlds from 1 Sep.

**A. Plates** (42,014 side-lane-minutes from 3:00 to 13:59 while the outer tower stands; 0.16 plates a side-lane-minute):

<!-- table: plates -->
| Version | Worlds (6159) | 2026 (9907) |
|---|---|---|
| minute and lane | 0.6159 | 0.6156 |
| + lane gold edge | 0.6061 | 0.6118 |
| + laners dead | 0.6064 | 0.6085 |
| + plates already off | 0.6031 | 0.6045 |
| + own grubs | 0.6028 | 0.6031 |

<sub>Source: research/model/laning/lane_actions.json (run record research/runs/20261114T042655Z_lane_actions.json, script research\laning\s5_lane_actions.py at commit 529caf2 with uncommitted edits).</sub>
<!-- /table -->

Kept, all of it. Fitted on all games: per 1k of lane edge +0.39 (log rate), each enemy laner just killed +0.45, own laner killed −0.11,
each plate already off −0.23, each own grub +0.07.

**B. First dragon taker** (639 games; blue took it 39% through 2026, 50% at Worlds):

<!-- table: first_dragon -->
| Version | Worlds (94) | 2026 (150) |
|---|---|---|
| side only | 0.7246 | 0.6444 |
| + strength and lanes at the time | 0.7181 | 0.5319 |
| + kills in the 60 s before | 0.7316 | 0.5303 |
| + Worlds term | 0.6972 | 0.5303 |

<sub>Source: research/model/laning/lane_actions.json (run record research/runs/20261114T042655Z_lane_actions.json, script research\laning\s5_lane_actions.py at commit 529caf2 with uncommitted edits).</sub>
<!-- /table -->

Kept: strength and lane edges (bot edge strongest: +1.52 per 1k), and the Worlds term (red side's 2026 dragon edge didn't happen at
Worlds). Kills just before: helps 2026, hurts Worlds: **Luke, 14 Nov: keep for now.**

**C. Grub taker** (1,920 grubs; blue took 62%):

<!-- table: grubs -->
| Version | Worlds (282) | 2026 (453) |
|---|---|---|
| side only | 0.6625 | 0.6535 |
| + strength and lanes at the time | 0.6612 | 0.6991 |
| + kills in the 60 s before | 0.6501 | 0.6910 |
| + team grubs priority | 0.6458 | 0.6757 |
| + Worlds term | 0.6495 | 0.6757 |

<sub>Source: research/model/laning/lane_actions.json (run record research/runs/20261114T042655Z_lane_actions.json, script research\laning\s5_lane_actions.py at commit 529caf2 with uncommitted edits).</sub>
<!-- /table -->

Mixed: each input helps at Worlds, but on 2026 games from 1 Sep side alone is best. **Luke, 14 Nov: use the full model** (strength, lane edges, kills in the 60 s before, team grubs priority); Worlds term not kept.

**D. Lane kills** (61,440 side-lane-minutes, 2:00–13:59) and solo kills: barely move from minute-and-lane rates (Worlds 0.3580 → 0.3571 with
pre-game players and champions; solo kills no gain). How often kills happen in a lane is close to a steady rate; who wins them is
step 1d (fights).

## 2e. What the lolesports feed adds (`s5_feed_analysis.py`, `research/model/laning/feed_analysis.json`)

Second-by-second health, gold, CS, level and K/D/A for every player, first 15 minutes of all 94 Worlds games (no map positions). Each
game's clock is set from the gol.gg timeline (the feed's own start time isn't reliable; 7 games were re-pulled with a fixed start rule,
one still has a 105 s gap in the feed itself). Trades: both sides' laners lose 10%+ of max health within 5 s and nobody in the lane dies in
the next 15 s; Worlds day by day.

<!-- table: feed -->
| Check or test | Result |
|---|---|
| Feed games matched to the file / clock set from the timeline | 94 / 91 of 94 (kills on the timeline's second: median game 100.0%) |
| At 10:00 v the file (mean gap) | gold 9.01, CS 0.24, kills / deaths / assists 0 |
| Respawn wait v the wiki timer (608 deaths) | median ratio 1.0, 89.6% within 2 s |
| Lane trades with no kill before 14:00 | 1,601; per game top 5.9, mid 5.02, bot 6.67; a jungler hit in 10.5% |
| Who wins a trade (1,500, log loss) | side 0.6952; + players and champions 0.6951; + level and gold at the time 0.6904 |
| Lane gold edge at 15 (255 lanes, error) | pre-game 0.9243; + trades before 10:00 0.9296 |

<sub>Source: research/model/laning/feed_analysis.json (run record research/runs/20261114T091254Z_feed_analysis.json, script research/laning/s5_feed_analysis.py at commit 8e5773c with uncommitted edits).</sub>
<!-- /table -->

- **The data is sound,** and the wiki death timers are right at Worlds (the research sim's timers can be used as they are).
- **Trades are frequent** (about 18 a game before 14:00) **and a jungler takes damage in about 1 in 10** (bot and mid more than top):
  jungle pressure the timelines never showed.
- **Who wins a single trade is close to a coin flip:** players and champions don't predict it; being ahead in level does a little
  (+0.44 log-odds per level). Trades before 10:00 add nothing to the lane's gold at 15 beyond the pre-game expectation. So the lane
  model works at the level of the lane's outcome and the fights (sections 1 and 2c), not trade by trade.

## 3. What this means for the laning slice

- **Lane contests** (1v1 top and mid, 2v2 bot, jungle): driven by player lane skill, champion lane strength, the matchup and team strength.
  All measured; no number set by hand.
- **Ganks and roams**: not from player habits (not supported). To test next: do ganks and roams follow game state (which lanes are
  winning or losing at the time, which side the next objective is on, the jungle champion's early power)?
- **Grubs**: team priority kept. **First dragon**: side and lane edges, with the side effect from Worlds / 16.20 first.
- **Champion pools**: comfort doesn't change lane results; pools go into the draft step (what each player can and will pick, and what bans
  deny).
