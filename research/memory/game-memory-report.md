# Game memory: what real games do after a fight (17 Nov 2026 AEST)

Luke's direction (17 Nov): the redesign's backbone is **game memory**, one game state carried all game that every action reads and writes
back to, with every response measured from real data. This report measures those responses. Plan agreed with Luke on 17 Nov: fights
tested over several windows with the data choosing; the winner by gold swing, with kills as the backup; responses counted until the
losers respawn; gol.gg timelines as a second check. Research only, no app change.

**Data.** The whole-game lolesports feed of all 98 Worlds 2026 games (16.20; pulled 17 Nov, `research/laning/feed_pull.py ... full`,
checked against the Oracle's Elixir file by `research/laning/feed_check.py`: 98 of 98 matched, 91 exact on final kills, towers,
inhibitors, Barons and dragons, 7 off by 1–2 kills). Per second it has each player's gold earned, level, kills, deaths, assists, CS and
health, and each team's gold, towers, inhibitors, Barons, kills and dragons. It has no map positions, plates, grubs or Herald. The second
check uses the 640 gol.gg timelines matched to the file: 94 Worlds games and 546 others from 2026.

Tables between the `table` markers are generated from the result files (`python -I research/lib/report.py
research/memory/game-memory-report.md research/memory/report_tables.py`). Scripts are in `research/memory/` (start with its README).

## 1. The game clock: cutting pauses

Feed seconds are real clock time, so pauses are counted in them. A rule turns them into game seconds: any gap of more than a few seconds
between frames counts as 1 second, and a stretch of 30 seconds or more where nobody's gold changes counts as 0.

<!-- table: clock -->
| Rule | Length v file (median) | Games 30 s+ off | Most over | Kills within 3 s of gol.gg | After 25:00 |
|---|---|---|---|---|---|
| no cutting | -1 s | 8 | +2149 s | 87.9% | 86.8% |
| gap 2 s, frozen 30 s | -1 s | 2 | +0 s | 91.1% | 90.4% |
| gap 5 s, frozen 30 s (used) | -1 s | 2 | +0 s | 91.1% | 90.4% |
| gap 10 s, frozen 30 s | -1 s | 2 | +0 s | 91.1% | 90.4% |
| gap 5 s, frozen 60 s | -1 s | 2 | +1 s | 91.0% | 90.3% |
| gap 5 s, frozen never | -1 s | 2 | +12 s | 90.2% | 88.8% |
| gap 5 s, frozen 1 s | -310 s | 98 | -114 s | 0.4% | 0.0% |

<sub>Source: research/model/memory/m0_clock.json (run record research/runs/20261117T123613Z_memory_clock.json, script research/memory/m0_clock.py at commit 46a92e7 with uncommitted edits).</sub>
<!-- /table -->

Any gap of 2–10 seconds and any frozen stretch of 30–60 seconds give the same result, so the choice doesn't matter. The two games 36–43
seconds short have no gaps at all; the feed for them ends early. The feed's `totalGold` is gold earned (in 2 million player-seconds it
fell 6 times, by about 200–260 gold each), so buying items doesn't move it. Deaths: 2,578, exactly the feed's own kill total. Respawns
are read from health when they come within 5 seconds of the official timer (League wiki, Respawn page, with the feed's level): 1,875
deaths. 331 use the official timer (the feed's health didn't read 0 at the death), and 372 came too late in the game to respawn.

## 2. Fights

Deaths closer together than G seconds are one fight. How the gaps between deaths spread out shows where fights separate:

<!-- table: gaps -->
| Seconds between deaths | 0-2 | 2-4 | 4-6 | 6-8 | 8-10 | 10-12 | 12-15 | 15-20 | 20-25 | 25-30 | 30-40 | 40-50 | 50-60 | 60-90 | 90-120 | 120-180 | 180-300 | 300-1e+09 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Count | 351 | 384 | 259 | 151 | 89 | 55 | 58 | 71 | 40 | 39 | 89 | 50 | 48 | 129 | 155 | 210 | 181 | 121 |
| Per second of gap | 175.5 | 192.0 | 129.5 | 75.5 | 44.5 | 27.5 | 19.3 | 14.2 | 8.0 | 7.8 | 8.9 | 5.0 | 4.8 | 4.3 | 5.2 | 3.5 | 1.5 | 0.4 |

<sub>Source: research/model/memory/m1_fights.json (run record research/runs/20261117T122612Z_memory_fights.json, script research/memory/m1_fights.py at commit 46a92e7 with uncommitted edits).</sub>
<!-- /table -->

The count per second of gap falls steeply up to about 20 seconds, then levels off at about 8 from 20 to 40 seconds: **fights end about
20 seconds after the last death**, so G = 20 s from here on. The results hardly depend on the choice:

<!-- table: by_gap -->
| Gap (s) | fights per game | deaths per fight | share with 1 death | share with 4+ deaths | trades by kills (equal kills) | gold and kills agree (kills not a trade) | gold winner of a trade = side with the higher swing; median |swing| of trades | winner wins the next fight (gold) | gold winner of the fight wins the game |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 16.16 | 1.63 | 0.661 | 0.08 | 0.088 | 0.978 | 203 | 0.592 | 0.679 |
| 10 | 13.41 | 1.96 | 0.559 | 0.148 | 0.089 | 0.971 | 195 | 0.568 | 0.683 |
| 15 | 12.36 | 2.13 | 0.511 | 0.187 | 0.103 | 0.961 | 227 | 0.587 | 0.685 |
| 20 | 11.71 | 2.25 | 0.479 | 0.22 | 0.11 | 0.965 | 222 | 0.589 | 0.685 |
| 30 | 10.97 | 2.4 | 0.442 | 0.252 | 0.117 | 0.952 | 250 | 0.585 | 0.688 |
| 45 | 9.8 | 2.69 | 0.379 | 0.307 | 0.126 | 0.944 | 292 | 0.594 | 0.696 |

<sub>Source: research/model/memory/m1_fights.json (run record research/runs/20261117T122612Z_memory_fights.json, script research/memory/m1_fights.py at commit 46a92e7 with uncommitted edits).</sub>
<!-- /table -->

Fights with no death (2 or more players on each side losing 5%+ health in the same second, with no death within G seconds) add about
one a game at G = 20 (`m1_fights.json`). They aren't used below.

## 3. Who won: gold swing, with kills as the backup

Gold swing = the change in team gold difference from 20 seconds before the first death to 5 seconds after the last. It agrees with the
kill count in 96.5% of fights that aren't trades. It disagrees where bounties make the difference: in the final's game 4 at 33:05, BLG
won the kills 3–2 but lost 1,227 gold, because GEN's kills collected bounties on BLG's fed players.

**Traced example, the real Worlds final game 4 (BLG v GEN, 43:04):** its fights add up to 21 BLG kills and 11 GEN kills, the real score.

<!-- table: game4 -->
| Fight | BLG deaths | GEN deaths | Gold swing (BLG) | Winner by gold | by kills | Players in (BLG v GEN) | BLG lead before |
|---|---|---|---|---|---|---|---|
| 2:43–2:43 | 1 | 0 | -484 | GEN | GEN | 3 v 3 | -133 |
| 4:06–4:06 | 1 | 0 | -559 | GEN | GEN | 3 v 3 | -155 |
| 4:41–4:41 | 0 | 1 | +240 | BLG | BLG | 2 v 3 | -862 |
| 5:14–5:14 | 0 | 1 | +576 | BLG | BLG | 2 v 3 | -566 |
| 11:39–11:39 | 1 | 0 | -807 | GEN | GEN | 2 v 3 | -509 |
| 16:07–16:11 | 1 | 1 | +365 | BLG | trade | 5 v 5 | -493 |
| 18:05–18:24 | 1 | 2 | +144 | BLG | BLG | 5 v 4 | +1,616 |
| 26:23–26:33 | 1 | 3 | +1,543 | BLG | BLG | 5 v 5 | +2,199 |
| 27:42–27:56 | 1 | 3 | +1,244 | BLG | BLG | 5 v 5 | +4,821 |
| 33:05–33:21 | 2 | 3 | -1,227 | GEN | BLG | 5 v 5 | +7,172 |
| 34:37–34:37 | 0 | 1 | +368 | BLG | BLG | 2 v 1 | +5,650 |
| 39:26–39:35 | 2 | 2 | -837 | GEN | trade | 5 v 5 | +6,088 |
| 41:56–42:04 | 0 | 2 | +2,097 | BLG | BLG | 5 v 5 | +4,662 |
| 42:53–42:54 | 0 | 2 | +2,252 | BLG | BLG | 5 v 3 | +7,644 |

<sub>Source: research/model/memory/fights_G20.csv (run record research/runs/20261117T122612Z_memory_fights.json, script research/memory/m1_fights.py at commit 46a92e7 with uncommitted edits).</sub>
<!-- /table -->

The same draft in the app's sim (v50), the game the fork traced:

<!-- table: app_trace -->
App sim v50, seed 2650763346037409: BLG won in 28:44, kills 22–13, towers 8–3.

| Fights (kills 20 s apart) | Objectives |
|---|---|
| 2:49-2:49 BLG 0 GEN 1<br>8:14-8:20 BLG 2 GEN 1<br>10:38-10:38 BLG 1 GEN 0<br>12:07-12:07 BLG 0 GEN 1<br>13:18-13:18 BLG 1 GEN 0<br>15:37-16:13 BLG 10 GEN 5<br>19:52-19:52 BLG 0 GEN 2<br>22:53-23:02 BLG 4 GEN 0<br>24:22-24:28 BLG 1 GEN 2<br>25:20-25:29 BLG 3 GEN 1 | 5:10 GEN dragon<br>8:45 GEN grubs<br>10:38 GEN dragon<br>13:44 BLG tower T1 BOT<br>14:11 GEN tower T1 MID<br>16:28 BLG herald<br>17:07 BLG dragon<br>17:19 BLG tower T1 MID<br>18:11 BLG tower T1 TOP<br>18:11 GEN tower T1 BOT<br>20:36 BLG tower T2 MID<br>20:36 GEN tower T1 TOP<br>23:02 BLG dragon<br>25:32 BLG tower T2 BOT<br>26:45 BLG baron<br>27:39 BLG tower T3 MID<br>28:14 BLG dragon<br>28:14 BLG inhib<br>28:44 BLG tower nexus tower<br>28:44 BLG tower nexus tower<br>28:44 BLG nexus |

<sub>Source: research/model/memory/app_sim_check.json (browser run of research/memory/app_sim_check.js; no run record).</sub>
<!-- /table -->

The real game had no fight with more than 5 deaths. It went through three short fights at 26–28 minutes with BLG 2–5k ahead, and ended
with two won fights straight before the Nexus at 43:04. The sim's 15:37–16:13 "fight" holds 15 kills in 36 seconds, and its Nexus falls
3 minutes after its last kill.

## 4. What follows a won fight, until the losers respawn

The window runs from the fight's last death to the moment the losing side's last fallen player is back (measured respawns). Each fight
counts what each side took in that window.

<!-- table: responses -->
| Group | Fights | Window (median s) | Winner takes anything | Towers W | Towers L | Inhibs W | Dragons W | Dragons L | Barons W | Nexus | First objective (median s) | Loser contests | Loser wins a fight |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| All fights | 1147 | 35 | 38% | 0.42 | 0.08 | 0.10 | 0.10 | 0.02 | 0.07 | 11% | 18 | 12% | 3% |
| before 14:00 | 365 | 17 | 4% | 0.02 | 0.01 | 0.00 | 0.02 | 0.03 | 0.00 | 0% | 16 | 4% | 0% |
| 14:00-25:00 | 420 | 39 | 46% | 0.31 | 0.14 | 0.02 | 0.13 | 0.01 | 0.10 | 1% | 20 | 18% | 4% |
| after 25:00 | 362 | 47 | 64% | 0.96 | 0.08 | 0.28 | 0.13 | 0.03 | 0.12 | 33% | 17 | 14% | 4% |
| Losers lost 1 | 628 | 33 | 28% | 0.24 | 0.10 | 0.05 | 0.08 | 0.03 | 0.04 | 4% | 20 | 15% | 3% |
| Losers lost 2 | 214 | 34 | 40% | 0.40 | 0.08 | 0.08 | 0.12 | 0.02 | 0.06 | 12% | 18 | 12% | 3% |
| Losers lost 3 | 126 | 41 | 51% | 0.58 | 0.03 | 0.14 | 0.12 | 0.01 | 0.15 | 12% | 18 | 8% | 3% |
| Losers lost 4+ | 154 | 41 | 73% | 1.15 | 0.03 | 0.30 | 0.13 | 0.00 | 0.17 | 40% | 17 | 5% | 3% |
| After 25:00, losers lost 1 | 137 | 50 | 53% | 0.59 | 0.17 | 0.17 | 0.12 | 0.05 | 0.11 | 15% | 24 | 25% | 7% |
| After 25:00, losers lost 2 | 67 | 47 | 66% | 0.87 | 0.04 | 0.27 | 0.19 | 0.03 | 0.09 | 37% | 16 | 10% | 3% |
| After 25:00, losers lost 3 | 56 | 50 | 77% | 1.11 | 0.02 | 0.32 | 0.14 | 0.00 | 0.23 | 27% | 18 | 11% | 5% |
| After 25:00, losers lost 4+ | 93 | 40 | 77% | 1.58 | 0.01 | 0.46 | 0.10 | 0.00 | 0.11 | 64% | 16 | 2% | 1% |

Outside every window (both sides together, per minute): towers 0.233, inhibitors 0.016, Barons 0.021, dragons 0.132. In the windows the winner alone takes towers at 0.79 a minute and Barons at 0.14.

<sub>Source: research/model/memory/m2_responses.json (run record research/runs/20261117T122613Z_memory_responses.json, script research/memory/m2_responses.py at commit 46a92e7 with uncommitted edits).</sub>
<!-- /table -->

- **Before 14:00 a won fight almost never leads to a structure** (4%); the feed doesn't show plates, grubs or Herald, the early prizes.
- **From 14:00 the winner takes something in about half of fights,** in a median 17–20 seconds. After 25:00, the more the losers lost,
  the more the winner takes: with 4 or more of the losers dead after 25:00 the Nexus falls in the window 65% of the time.
- **Losers rarely answer:** they take anything or win the next fight inside the window in only 12% of fights.

## 5. Snowballing, dead time, closeness

**Snowball.** Does the winner of a fight win the next one beyond what the gold lead explains?

<!-- table: snowball -->
Fit on 1048 fights: per 1,000 gold lead +0.153 (90% range +0.124 to +0.186); won the last fight +0.109 (+0.004 to +0.219); at even gold the last fight's winner wins the next 55%, the loser 49%.

| Last fight's winner, gold lead going into the next | Fights | Wins the next |
|---|---|---|
| behind 3k+ | 87 | 41% |
| behind 1-3k | 89 | 33% |
| within 1k | 285 | 54% |
| ahead 1-3k | 259 | 60% |
| ahead 3k+ | 328 | 74% |
| before 14:00 (any lead) | 274 | 50% |
| 14:00-25:00 (any lead) | 417 | 61% |
| after 25:00 (any lead) | 357 | 64% |

Seconds from one fight to the next: median 118, middle half 61–198.

<sub>Source: research/model/memory/m3_state.json (run record research/runs/20261117T122711Z_memory_state.json, script research/memory/m3_state.py at commit 46a92e7 with uncommitted edits).</sub>
<!-- /table -->

Most of the snowball is gold. "Won the last fight" adds a little (about 5 points at even gold, and its 90% range only just stays above
zero); it's kept under the keep-every-input rule, and should be fitted, not set.

**Dead time** (share of game time each role spends dead):

<!-- table: dead -->
| Role | before 14:00 | 14:00-25:00 | after 25:00 |
|---|---|---|---|
| top | 1.8% | 6.9% | 9.2% |
| jng | 1.3% | 5.9% | 9.2% |
| mid | 1.3% | 5.4% | 8.9% |
| bot | 1.2% | 4.6% | 8.2% |
| sup | 1.1% | 4.3% | 7.2% |

<sub>Source: research/model/memory/m3_state.json (run record research/runs/20261117T122711Z_memory_state.json, script research/memory/m3_state.py at commit 46a92e7 with uncommitted edits).</sub>
<!-- /table -->

**Closeness.** Health and numbers going into a fight (20 seconds before the first death):

<!-- table: closeness -->
| Health gap going in (full health bars) | Fights | Side with more health wins | Median gold swing |
|---|---|---|---|
| under 0.5 | 469 | 49% | 753 |
| 0.5-1 | 350 | 48% | 600 |
| 1-2 | 278 | 60% | 586 |
| 2+ | 50 | 64% | 816 |

| More players alive going in | Fights | That side wins |
|---|---|---|
| +1 | 145 | 68% |
| +2 | 27 | 82% |
| +3+ | 26 | 85% |

Fit (blue wins): per extra full health bar +0.338, per 1,000 gold +0.166, per extra player counted in the fight -0.182 (biased: players are counted by losing health, which losing sides do more).

<sub>Source: research/model/memory/m3_state.json (run record research/runs/20261117T122711Z_memory_state.json, script research/memory/m3_state.py at commit 46a92e7 with uncommitted edits).</sub>
<!-- /table -->

Numbers matter a lot: a side going in one player up wins 68% of fights. Health matters only past a gap of about one full health bar.
Without map positions, the feed can't show who could reach a fight.

## 6. Second check: gol.gg timelines

Timelines give each event's second but no health or gold by second, so fights there use the kills winner (trades left out). Respawns
use the feed's median death time at that minute.

<!-- table: timelines -->
| Group | Fights | Window (median s) | Winner takes anything | Towers W | Towers L | Inhibs W | Dragons W | Dragons L | Barons W | Nexus | Loser contests | Wins the next fight | Wins the game |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Worlds (same games as the feed): all (94 games) | 976 | 35 | 42% | 0.47 | 0.07 | 0.11 | 0.10 | 0.02 | 0.09 | 12% | 11% | 61% | 71% |
| Worlds (same games as the feed): before 14:00 | 302 | 20 | 4% | 0.02 | 0.01 | 0.00 | 0.01 | 0.02 | 0.00 | 0% | 4% | 52% | 61% |
| Worlds (same games as the feed): 14:00-25:00 | 368 | 39 | 49% | 0.34 | 0.13 | 0.02 | 0.14 | 0.01 | 0.11 | 1% | 17% | 63% | 69% |
| Worlds (same games as the feed): after 25:00 | 306 | 47 | 71% | 1.08 | 0.07 | 0.32 | 0.15 | 0.02 | 0.14 | 36% | 12% | 69% | 82% |
| Worlds (same games as the feed): after 25:00, losers lost 1 | 113 | 48 | 61% | 0.69 | 0.16 | 0.20 | 0.16 | 0.05 | 0.13 | 15% | 23% | 60% | 68% |
| Worlds (same games as the feed): after 25:00, losers lost 2 | 58 | 47 | 71% | 0.95 | 0.02 | 0.26 | 0.21 | 0.02 | 0.12 | 40% | 5% | 82% | 90% |
| Worlds (same games as the feed): after 25:00, losers lost 3 | 49 | 50 | 80% | 1.16 | 0.02 | 0.35 | 0.12 | 0.00 | 0.22 | 24% | 8% | 76% | 86% |
| Worlds (same games as the feed): after 25:00, losers lost 4+ | 86 | 41 | 80% | 1.64 | 0.01 | 0.50 | 0.10 | 0.00 | 0.10 | 66% | 4% | 74% | 94% |
| other 2026 timelines: all (546 games) | 6295 | 35 | 39% | 0.45 | 0.07 | 0.10 | 0.09 | 0.01 | 0.08 | 10% | 12% | 61% | 69% |
| other 2026 timelines: before 14:00 | 2016 | 20 | 4% | 0.01 | 0.01 | 0.00 | 0.03 | 0.02 | 0.00 | 0% | 4% | 55% | 60% |
| other 2026 timelines: 14:00-25:00 | 2338 | 39 | 47% | 0.37 | 0.12 | 0.03 | 0.12 | 0.02 | 0.10 | 1% | 18% | 60% | 68% |
| other 2026 timelines: after 25:00 | 1941 | 48 | 66% | 1.00 | 0.08 | 0.28 | 0.10 | 0.01 | 0.14 | 31% | 13% | 70% | 80% |
| other 2026 timelines: after 25:00, losers lost 1 | 743 | 48 | 55% | 0.60 | 0.12 | 0.17 | 0.10 | 0.02 | 0.13 | 13% | 20% | 63% | 67% |
| other 2026 timelines: after 25:00, losers lost 2 | 334 | 48 | 63% | 0.79 | 0.12 | 0.22 | 0.10 | 0.01 | 0.16 | 25% | 15% | 71% | 79% |
| other 2026 timelines: after 25:00, losers lost 3 | 320 | 47 | 71% | 0.97 | 0.04 | 0.26 | 0.13 | 0.01 | 0.17 | 35% | 8% | 75% | 86% |
| other 2026 timelines: after 25:00, losers lost 4+ | 544 | 44 | 82% | 1.69 | 0.03 | 0.46 | 0.09 | 0.00 | 0.11 | 58% | 5% | 78% | 94% |

<sub>Source: research/model/memory/m4_timelines.json (run record research/runs/20261117T123227Z_memory_timelines.json, script research/memory/m4_timelines.py at commit 46a92e7 with uncommitted edits).</sub>
<!-- /table -->

The Worlds games read from gol.gg give nearly the same numbers as the feed (same games, a different source and a different winner rule),
and the 546 other 2026 games are close to Worlds. So the responses aren't a Worlds or 16.20 quirk, and the timelines (15 Jul to 8 Nov 2026;
411 games before 1 Sep) can be used to fit them.

## 7. The current sim against the real games

The current research sim (`research/sim3/s3_sim.py`, the default with death timers, 1,000 sims a game, seeds by game ID) on the same 94
Worlds games, its event log read exactly like a timeline. It runs minute by minute, so timing within a minute isn't compared.

<!-- table: sim_compare -->
| Per game | Real (94 Worlds games) | Current research sim (94,000 sims) |
|---|---|---|
| kills | 26.138 | 26.802 |
| minutes | 33.266 | 33.884 |
| fights with a kills winner | 10.383 | 9.963 |
| 45+ min | 0.043 | 0.078 |
| 50+ min | 0 | 0.027 |
| loser on a third of the winner's kills or fewer | 0.255 | 0.228 |
| kills before 14:00 | 6.298 | 6.692 |
| fights (kills 20 s apart) with 6+ deaths on one side | 0.002 | 0.001 |
| objectives in the same second as the one before, per game | 0.096 | 5.54 |
| Nexus: seconds after the last kill, median | 12 | 49 |
| Nexus more than 60 s after the last kill | 0 | 0.447 |

| Group | Fights | Window (median s) | Winner takes anything | Towers W | Towers L | Inhibs W | Dragons W | Dragons L | Barons W | Nexus | Loser contests | Wins the next fight | Wins the game |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Real: all | 976 | 35 | 42% | 0.47 | 0.07 | 0.11 | 0.10 | 0.02 | 0.09 | 12% | 11% | 61% | 71% |
| Sim: all | 936515 | 35 | 21% | 0.22 | 0.08 | 0.04 | 0.06 | 0.02 | 0.03 | 3% | 12% | 57% | 66% |
| Real: before 14:00 | 302 | 20 | 4% | 0.02 | 0.01 | 0.00 | 0.01 | 0.02 | 0.00 | 0% | 4% | 52% | 61% |
| Sim: before 14:00 | 311229 | 20 | 4% | 0.01 | 0.01 | 0.00 | 0.03 | 0.01 | 0.00 | 0% | 2% | 54% | 62% |
| Real: 14:00-25:00 | 368 | 39 | 49% | 0.34 | 0.13 | 0.02 | 0.14 | 0.01 | 0.11 | 1% | 17% | 63% | 69% |
| Sim: 14:00-25:00 | 322539 | 39 | 24% | 0.23 | 0.11 | 0.02 | 0.07 | 0.02 | 0.03 | 1% | 15% | 58% | 66% |
| Real: after 25:00 | 306 | 47 | 71% | 1.08 | 0.07 | 0.32 | 0.15 | 0.02 | 0.14 | 36% | 12% | 69% | 82% |
| Sim: after 25:00 | 302747 | 51 | 35% | 0.41 | 0.13 | 0.11 | 0.08 | 0.03 | 0.06 | 9% | 17% | 61% | 71% |
| Real: after 25:00, losers lost 1 | 113 | 48 | 61% | 0.69 | 0.16 | 0.20 | 0.16 | 0.05 | 0.13 | 15% | 23% | 60% | 68% |
| Sim: after 25:00, losers lost 1 | 108121 | 51 | 31% | 0.32 | 0.16 | 0.08 | 0.08 | 0.03 | 0.06 | 6% | 20% | 58% | 64% |
| Real: after 25:00, losers lost 2 | 58 | 47 | 71% | 0.95 | 0.02 | 0.26 | 0.21 | 0.02 | 0.12 | 40% | 5% | 82% | 90% |
| Sim: after 25:00, losers lost 2 | 51805 | 51 | 35% | 0.41 | 0.13 | 0.11 | 0.08 | 0.03 | 0.06 | 9% | 18% | 60% | 69% |
| Real: after 25:00, losers lost 3 | 49 | 50 | 80% | 1.16 | 0.02 | 0.35 | 0.12 | 0.00 | 0.22 | 24% | 8% | 76% | 86% |
| Sim: after 25:00, losers lost 3 | 56487 | 51 | 36% | 0.44 | 0.12 | 0.12 | 0.08 | 0.03 | 0.06 | 10% | 17% | 61% | 72% |
| Real: after 25:00, losers lost 4+ | 86 | 41 | 80% | 1.64 | 0.01 | 0.50 | 0.10 | 0.00 | 0.10 | 66% | 4% | 74% | 94% |
| Sim: after 25:00, losers lost 4+ | 86334 | 51 | 40% | 0.52 | 0.10 | 0.15 | 0.09 | 0.02 | 0.07 | 13% | 13% | 67% | 80% |

<sub>Source: research/model/memory/m5_sim_compare.json (run record research/runs/20261117T125949Z_memory_sim_compare.json, script research/memory/m5_sim_compare.py at commit 46a92e7 with uncommitted edits).</sub>
<!-- /table -->

**The sim's games look right in total but its fights don't drive the map.** Kills, length, fight count and the early game match.
After 14:00 the sim's fight winners take about half of what real winners take: something in 24% of fights against 49%, and after 25:00
35% against 71%. In the sim it barely matters how many of the losers died (31–40% after 25:00, real 61–80%). The Nexus falls inside a
window 9% of the time after 25:00, against 36%. The sim gets its towers and Nexus mostly outside fights, so its games run long more
often (45+ minutes 7.8% against 4.3%, 50+ 2.7% against none). The research sim keeps fights to real sizes (6+ deaths on one side 0.1%);
the app sim on the game 4 draft doesn't (2.6%), so the app port differs there (only one draft checked).

Shape checks the real games never break:

<!-- table: app_shape -->
| Measure | Real Worlds (gol.gg) | Research sim (94 Worlds games) | App sim v50 (final game 4 draft, 1,000 seeds) |
|---|---|---|---|
| Fights with 6+ deaths on one side | 0.2% | 0.1% | 2.6% |
| Objectives in the same second as the one before, per game | 0.096 | 5.54 | 5.62 |
| Nexus: seconds after the last kill (median) | 12.0 | 49.0 | 51 |
| Nexus more than 60 s after the last kill | 0% | 45% | 44% |

<sub>Sources: research/model/memory/m5_sim_compare.json (run memory_sim_compare) and app_sim_check.json (browser run, no run record).</sub>
<!-- /table -->

## 8. What this means for the redesign (plan for Luke to OK)

Each item below is a measured behaviour the game-memory sim must produce as an outcome. Each one gets fitted on training games, not
typed in.

1. **Real seconds, one event at a time.** No same-second stacks; real games have about 0.1 a game.
2. **Players with a state:** alive or dead with the official respawn timer (the feed agrees within 5 seconds for 85% of deaths), level,
   gold earned. A dead player does nothing.
3. **Fights as actions with a measured size:** the deaths per fight follow the real spread (half are single deaths, a fifth are 4+, almost
   never more than 5 on one side). Fights come a median 2 minutes apart.
4. **Fight winner from the state:** gold lead (about +0.15 log-odds per 1,000), players alive (+1 alive = 68%), health only when the
   gap is large, a small "won the last fight" effect, plus the team and player strength already in the sim.
5. **The response window:** until the losers respawn, the winner takes towers, dragons, Barons and inhibitors at the measured rates,
   by game phase and by how many of the losers died. The losers contest about 12% of the time.
6. **The Nexus only falls after a won fight:** in real games it falls a median of 12 seconds after the last kill, and never more than 60
   seconds after it.
7. **Outside the windows:** objectives at the base rate per minute, and early prizes (plates, grubs, Herald) from the laning slice.

**Decisions for Luke:**
- **Where to fit:** the responses on gol.gg timelines before each test day (the walk-forward rule: fit on every earlier game), with the
  Worlds feed as the check of the method. Recommended, since fitting on the feed's Worlds games would use test games.
- **Who's in a fight:** the feed has no positions. Options: count players by health lost (biased toward the losers), take fight sizes
  from the deaths only, or find a source with positions (the Riot match timeline API has them for solo queue only).

<sub>Built 17 Nov 2026 AEST by Claude in a Claude Code session; checks: feed v file (feed_check.py), scripts rerun after each change
with research/lib/compare.py where code moved, app sim check run in a local browser tab with the saved script.</sub>
