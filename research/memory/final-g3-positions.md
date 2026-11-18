# Worlds final game 3 (GEN blue v BLG red, BLG won 20–8 in 37:40): positions around every fight (18 Nov 2026 AEST)

Luke asked for the whole of game 3 read the way the 27:36 check was done: who was in each fight from the feed (deaths, kills and
assists credited by the second, health lost), where everyone was from the broadcast minimap (stills a few seconds before each death),
and champions hidden in fog placed by where they were last seen and next appear. Hand-read; stills and minimap notes are in
`research/local/vod_stills/final_g3/` (git-ignored). One game: these are leads to test on the 98 games, not findings.

**How the broadcast minimap works (checked at 27:36):** it shows a champion only when the other team can see it. At 27:36 Knight, Xun and
ON were off the map; 3 s later they killed Chovy and appeared beside him. Dead players aren't shown either. So a missing champion is
dead (feed health), out of the enemy's sight, or under a stack of portraits in a fight.

## Fight by fight

"In" = credited with a kill, assist or death, or lost 15%+ health in the fight (from 20 s before the first death to 5 s after the last).

| Fight | Deaths GEN–BLG | Winner (gold) | In the fight | Where (minimap) | What followed (feed) |
|---|---|---|---|---|---|
| 6:56 | 1–0 | BLG | Duro alone v Bin, Xun, Viper, ON | Bot, at BLG's outer tower; Ruler not involved | GEN dragon 7:26 anyway |
| 7:33 | 0–1 | GEN | Ruler (solo kill) and Canyon v Knight | Mid; Annie, Wukong near but not involved; BLG's others in their jungle and base | – |
| 13:09–16:32 | – | – | no kills | – | 4 towers fall (BLG 13:09, both 15:36, GEN 16:32): lane pressure, not fights |
| 17:42 | 1–0 | BLG | Ruler alone v Xun, Viper | Top-side river; Jax top, Viktor in base, Annie bot | BLG dragon 18:07 |
| 19:24 | 1–0 | BLG | Kiin, Canyon, Duro v all 5 BLG | Top-side river and GEN's top jungle | BLG tower 19:47 |
| 20:28 | 0–1 | GEN | Chovy (solo kill) v Bin | GEN's top-side jungle: Jax pushed in alone | – |
| 21:04–21:23 | 1–3 | GEN | all 5 GEN v 4 BLG (Bin dead going in) | GEN's top-side jungle, then moved to mid on GEN's side | GEN tower 21:42 |
| 23:21–23:42 | 3–1 | BLG | all 10 (Bin joined from top: 2 kills) | BLG's bot-side jungle and river, then chased to GEN's bot inner tower | BLG dragon 24:09 |
| 25:02–25:10 | 3–1 | BLG | all 10 | GEN's jungle, covered by effects | **BLG Baron 25:50** |
| 27:39 | 1–0 | BLG | Chovy alone v Knight, Xun, ON (all three out of sight 3 s before) | Mid on BLG's side; Jax split top | BLG towers 28:07, 28:33 |
| 30:13–30:31 | 4–0 | BLG | all 10 | BLG's bot-side jungle by the river | **BLG dragon 30:13, during the fight** |
| 30:54 | 0–1 | GEN | Ruler (solo kill) v Knight | Knight alone in GEN's base while 3 GEN were dead | – |
| 34:28 | 1–0 | BLG | all 10 | GEN's top-side jungle | BLG dragon 35:24 |
| 36:58–37:05 | 3–0 | BLG | 4 GEN v 5 BLG (Chovy not in) | GEN's top-side jungle | BLG towers 37:10, inhibitor 37:13, towers 37:26–27, Nexus 37:40 |
| 37:32 | 1–0 | BLG | Chovy v all 5 BLG (3 GEN dead) | (player cams on screen) | Nexus 37:40 |

## What this suggests for the sim (to test on all 98 games before anything is built)

1. **Two kinds of fight, with different rules.** Game 3 had 7 picks (one victim, 1–3 attackers, everyone else elsewhere) and 7
   fights where every live player joined. Across all 98 Worlds games (feed, same "in" rule but 25%+ health): 25% of fights are picks
   (one death, 4 or fewer players) and 41% involve 8+ players; picks fall from 40% of fights before 14:00 to 14% after 25:00, while
   8+-player fights rise from 19% to 60%. The sim's fights should first choose their kind and size from the game state, not draw a
   single fight type. (The 98-game count was a one-off command on 18 Nov, not yet a recorded script.)
2. **Who gets picked is whoever is alone.** Every pick victim was apart from their team: a support at the enemy tower (6:56), an ADC
   in the river (17:42), a mid in the enemy half (27:39), a split-pusher deep in the enemy jungle (20:28), a mid in the enemy base
   with 3 enemies dead (30:54). The game state needs each player's spot (at least: own lane, side lane alone, with team, in base),
   and pick chances should depend on it.
3. **Attackers come out of fog.** At 27:36 the three who killed Chovy were all out of sight 3 s before. Vision belongs in the state;
   the Oracle's Elixir file has wards placed and cleared and vision score per player, so "vision lead → more picks" can be tested.
4. **Teamfights happen at objectives, and the objective goes to the winner.** The four big BLG wins came just before a dragon (24:09),
   the Baron (25:50), a dragon taken mid-fight (30:13) and the base push (37:10–37:40). This fits the game-memory report (winner takes
   the objective before the losers respawn). Next step: time from fight to the next objective spawn, real v sim.
5. **Side-laners join late or not at all.** Bin was split-pushing top through the mid-game and still got 2 kills in the 23:21 fight
   (he arrived during it), but was absent from the picks. The sim needs a side-lane role that joins fights late (a delay, not "all 5").
6. **Long fights move.** 21:04 started in GEN's top jungle and ended mid; 23:21 started in BLG's jungle and ended at GEN's bot inner
   tower. A chase after a won fight carries the winner toward the loser's towers, which is how fights turn into structures.
7. **Towers also fall with no fight.** 13:09–16:32 had four towers and no kills: lane pressure takes plates and towers on its own
   (the laning slice), separate from fight responses.

## Tested on all 98 Worlds games (18 Nov, `m6_fight_kinds.py`)

"In a fight" = kill, assist or death credited, or 25%+ health lost; pick = one death and 4 or fewer in; big = 8+ in.

<!-- table: leads -->
| Phase | Fights | Picks | Big fights (8+) | Pick victims: top / jng / mid / bot / sup (share of all deaths) | Towers with no death in the 60 s before |
|---|---|---|---|---|---|
| before 14:00 | 371 | 36% | 19% | 47% (24%) / 4% (18%) / 22% (16%) / 13% (20%) / 13% (22%) (n 135) | 58% of 43 |
| 14:00-25:00 | 420 | 24% | 45% | 32% (22%) / 12% (21%) / 28% (18%) / 14% (17%) / 15% (22%) (n 102) | 49% of 492 |
| after 25:00 | 357 | 13% | 60% | 33% (20%) / 20% (21%) / 22% (20%) / 11% (20%) / 15% (20%) (n 46) | 34% of 633 |

| Gold gap going in | Picks (all) | Big (all) | Picks after 25:00 | Big after 25:00 |
|---|---|---|---|---|
| under 1k | 30% | 31% | 19% | 57% |
| 1-3k | 29% | 40% | 16% | 66% |
| 3-6k | 18% | 47% | 11% | 54% |
| 6k+ | 12% | 62% | 11% | 64% |

| Objective | Big fight in the 90 s before | Pick | Any fight |
|---|---|---|---|
| baron (141) | 55% | 9% | 79% |
| dragon (484) | 24% | 12% | 49% |
| Random second after 5:00 (chance) | 22% | 13% | 48% |

| Role | Not in a big fight | Entry after the first player (median s) | Entering 10 s+ after |
|---|---|---|---|
| top | 11% | 10 | 51% |
| jng | 4% | 8 | 42% |
| mid | 9% | 11 | 55% |
| bot | 6% | 10 | 52% |
| sup | 4% | 9 | 45% |

| Fights won, per +10 points of the team's share of… | Estimate | 90% range | Fights |
|---|---|---|---|
| pick: share won per +10 points of vision share | +0.381 | +0.227 to +0.538 | 283 |
| big (8+): share won per +10 points of vision share | +0.470 | +0.346 to +0.615 | 476 |
| pick: share won per +10 points of wards_killed share | +0.112 | +0.023 to +0.199 | 283 |
| big (8+): share won per +10 points of wards_killed share | +0.090 | +0.005 to +0.169 | 476 |

<sub>Source: research/model/memory/m6_fight_kinds.json (run record research/runs/20261118T025910Z_memory_fight_kinds.json, script research/memory/m6_fight_kinds.py at commit 46a92e7 with uncommitted edits).</sub>
<!-- /table -->

| Lead | Verdict |
|---|---|
| 1 Fight kind and size from the state | **Holds, mainly by phase.** Picks fall and big fights rise through the game; a bigger gold gap goes with bigger fights overall, but after 25:00 the gap barely changes the mix, so phase (game time) is most of it |
| 2 Whoever is alone gets picked | **Holds as "side-laners get picked".** Top laners are about twice their share of deaths among pick victims all game, mids above their share; junglers, ADCs and supports below. Game 3's support and ADC picks were not typical |
| 3 Vision gives picks | **Not shown.** Vision share goes with winning picks and big fights alike (per-game totals only; no timing), so it marks the stronger team, not picks in particular |
| 4 Teamfights at objectives | **Holds for Baron, not for dragons.** 55% of Barons follow a big fight within 90 s (chance 22%); dragons 24%, the same as chance: dragons are mostly taken without a fight before them |
| 5 Side-laners join late | **Weak.** Top laners miss big fights most (11%, junglers 4%), but when they join they arrive no later than others (median 8–11 s after the first player for every role) |
| 6 Long fights move | Not testable without positions (the towers after a fight are in `m2_responses`) |
| 7 Towers fall with no fight | **Holds.** 58% of towers before 14:00, 49% at 14–25 min and 34% after 25:00 have no death in the 60 s before |

Checks: feed times and kills match the file and the on-screen clock (game clock = video second − 7,177). Hand-read limits: champion
names only in small fights; big fights are covered by spell effects; 2 of 16 stills were covered by broadcast shots.
