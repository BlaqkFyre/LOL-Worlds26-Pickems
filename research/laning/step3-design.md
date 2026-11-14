# Laning slice, step 3 design: the laning module in the research sim (draft for Luke, 14 Nov 2026 AEST)

Status: **design only, nothing built.** Plan: `research/laning-plan.md`. What the data supports: `research/laning/step1-report.md`.
Traced games (Luke: all the semi-finals plus two quarter-finals): `research/laning/step3-traces.md` (generated: 15 games, per lane the
players, champions, the model's pre-game expected edge and what really happened before 14:00).

## What changes, and what doesn't

A new option in the research sim (`research/sim3/s3_sim.py`, `cal["laning"] = "actions"`), **off by default** so every earlier run
replays exactly (checked the same way as before: hundreds of seeded games identical with the option off). From 0:00 to 14:00 it replaces
four things the sim draws today; from 14:00 the current sim carries on from the state the module leaves.

| Part of the early game | Today (research sim and app) | With the laning module | Fitted from (step 1) |
|---|---|---|---|
| Lane gold | Each lane's lead at 15 is drawn once at the start (lane-level fit, `lane_end`) and farmed in minute by minute | **Built from actions, no lead noise (revised 14 Nov, Luke):** each minute both laners alive farm as a **CS contest** (expected edge from the players, champions and matchup; minute-to-minute spread measured from the feed); a dead laner farms nothing; gold = CS + kills + assists + plates + passive at the values measured from the feed | `s5_farm.py` (feed), `s5_lane_edges.py` (lane model on CS) |
| Who wins an early fight | Kill direction from team strength, lead and noise | **Fight winner** from the players and champions in the roles taking part, team strength and those roles' gold now | `s5_fight_winner.py` (Worlds 0.689 → 0.661) |
| When fights happen and who is in them | Fitted counts per minute, fight players, early-window types | **Unchanged** (step 1: lane kill rates barely move with lane state; ganks and roams don't follow lane state in this data) | existing fits |
| Plates (3:00–13:59) | Tower segments from the push model | **Plates per side, lane and minute** from that lane's gold edge, laners just killed, plates already off, own grubs; 5 plates and the tower falls as now | `s5_lane_actions.py` A |
| First dragon taker | Fitted taker (side, strength, lanes) | **Taker** from side, strength, bot / mid / jungle edges at the time, kills in the 60 s before, and a Worlds term (Luke: keep kills-before) | `s5_lane_actions.py` B |
| Grubs | One draw for all three (split 3–0 or 2–1) | **Each grub its own contest**: side, strength, top / mid / jungle edges, kills in the 60 s before, team grubs priority (Luke: full model) | `s5_lane_actions.py` C |
| Dead players | No timers in the app; research option `dt` | **Death timers on** (wiki table, confirmed on 608 Worlds deaths); a dead laner can't fight, defend plates or contest | `research/sim4/s4_deathtimer.py`, feed check |
| Dragon and grub timing, Herald, everything after 14:00 | Fitted | Unchanged in this slice | existing fits |

Not in this slice (later slices, per the plan): damage types, comp styles and synergies, team meta awareness, scaling, objectives after
14:00, pushes and endings driven by fights.

## The farm contest (measured 14 Nov from the feed, `s5_farm.py`, `research/model/laning/farm.json`)

Luke asked what fitting the module removes. The first design still drew part of each lane's gold as fitted "leftover noise" to make the
spread look right. Revised: lane gold comes only from actions, and the test is whether real lane spreads come out.
- **Where gold comes from** (11,800 Worlds player-minutes, 1:00–13:59): about 19.6 per CS, 333 per kill, 92 per assist, 62 per own-lane
  plate, minus 35 for a minute spent dead; these explain 81% of the minute-to-minute gold.
- **The CS contest:** per minute, blue's CS minus red's swings about ±4.7 (support ±1.8), and almost none of that is a fixed "on the day"
  edge (0–2%): minutes are independent contests.
- **Players and champions do drive it:** the lane model's pre-game expected CS edge at 10 (fitted only on games before each Worlds day)
  lines up with the real CS edge at 10 on Worlds lanes: correlation top 0.55, jungle 0.25, mid 0.62, ADC 0.47, support 0.43. Minute by
  minute it's drowned by the swing (no gain on a single minute), but it adds up over the laning phase.
- **Do real lane spreads come out of actions alone?** Each Worlds lane rebuilt from the CS contest each alive minute (nothing while dead),
  plus that game's real kills, assists and plates at the measured values, with no lead noise:
  - **CS edge at 15: yes**, the spread comes out about right, a little wide (top 20.6 v real 18.9; mid 19.0 v 14.3).
  - **Gold edge at 15: not yet**, about 75–90% of the real spread for top, jungle and ADC (top 733 v 994, ADC 750 v 1,063; mid 605 v 666;
    support right). The real edge falls inside the rebuilt 80% range in only 44–72% of lanes. **So a gold source is missing,** most likely
    the size of each kill (bounties and shutdowns vary; this used the average), plates taken by roamers, and objective gold.
  - **Next measurement:** the gold each event actually pays, second by second from the feed (kill gold by the victim's streak and first
    blood, plates by who was there, grubs and dragon). Then re-run this test. No noise term gets added to close the gap.

## Official gold values, checked against the feed (14 Nov, Luke: read the official docs too; `s5_event_gold.py`, `event_gold.json`)

League of Legends Wiki pages, opened 14 Nov 2026: Gold (edited 3 Jul 2026), Champion gold bounties (6 Jul 2026), Turret, Role Quests
(8 Nov 2026, V26.19), Voidgrub camp (9 Nov 2026), Infernal Drake (26 Mar 2026), Minion. Measured on Worlds games second by second:

| Event | Official (wiki) | Measured at Worlds |
|---|---|---|
| First blood | bounty 300 + 100 | 418 (73 kills) |
| Other kills | 300 at levels 1-6, +10 a level; rises with the victim's kill and assist gold (1 per 3), shutdown above base + 100; falls after deaths | median 321 (10th-90th: 273-390); victims with 5+ kills and assists: 543 |
| Assists | half the bounty, at most half the base, split among assisters | 1 assister 170, 2: 83 each, 3: 57, 4: 40 |
| Plate | 120, shared by allies nearby | about 49 per player of the lane's side a plate (shared) |
| First turret | +300 extra | fits as extra gold to the side that takes it |
| ADC role quest | 300 on completion, then +2 a minion, +40 a takedown | a 318 jump with no kill or plate, median 12:18 (90% by 13:49) |
| Passive | 20.4 per 10 s from 1:05 | in the minute baseline |
| Grubs, drake | 30 each grub; 75 a drake | not yet measured separately |

**Lane gold from actions, re-tested to 15:00 with towers added:** gold from events now lines up closely with the real gold that isn't
from CS (correlation 0.81-0.89 by role), but its spread is still about 75-80% of the real one (top 529 v 686, ADC 587 v 806), because
every kill, assist and plate is paid the average. The official rules say why: a kill's value depends on the victim's earlier kills and
assists (bounty), first blood, how many share an assist or a plate, and when the ADC finishes the role quest. **So the module pays gold by
the official rules (bounties, first blood, assist split, plate split, first turret, ADC quest), not averages,** then this test is re-run;
no noise term.

## Lane gold paid by the official rules: re-run (14 Nov, Luke: rerun it; `s5_rule_gold.py`, `rule_gold.json`)

Each real event paid by the wiki rules (bounty from the victim's level, kill and assist gold and farm, first blood, assist split, plates
split among the lane's players, first turret, 50 a turret, ADC quest 300 at its real time then +2 a minion and +40 a takedown):
- **Kill by kill** (498 clean Worlds kills): the rules give median 330 v 330 real, mean miss 38 gold, correlation 0.71. Not applied for
  lack of published numbers: the early assist reduction and the shut-down cut after 6:00.
- **Spread of lane gold at 15, actions only** (CS contest + rule gold, no noise term), real v rebuilt: top 992 v 927, jungle 797 v 630,
  mid 663 v 667, ADC 1,058 v 865, support 386 v 436. Gold from events now has about the real spread in mid, ADC and support, a little
  too much in top (plates all paid to the top laner, though junglers and mids often share them) and too little in jungle (camp quest gold,
  grubs and drakes aren't in yet).
- **Calibration:** the real edge falls inside the rebuilt 80% range in 50-76% of lanes. This run centres each lane's CS contest on the
  average, not yet on the lane model's expectation for those players and champions, so it understates the fit; the step 3 tests use the
  full module.
- **Next, in the build:** jungle gold (camps, quest +10 a camp, grubs, drakes) and who shares plates come from the feed and timelines in
  the module; still no noise term.

## Worked example: semi-final game 1, Gen.G (blue) v Invictus Gaming (red) (`LOLTMNT02_487213`)

From `research/laning/step3-traces.md`. Model values are fitted only on games before that Worlds day.
1. **Pre-game (the lane model):** expected gold edge at 10, blue minus red: top Kiin (Olaf) v TheShy (Kled) **+110**, jungle Canyon (Qiyana) v
   Wei (Vi) **+368**, mid Chovy (Cassiopeia) v Rookie (Syndra) **+220**, bot Ruler (Jhin) / Duro (Leona) v JiaQi (Xayah) / Meiko (Rakan)
   **−48**. Team strength (v1) favours Gen.G (z = 1.03).
2. **3:45 top-side fight** with both junglers and top laners (real: three kills in 4 s, Canyon finishing with a solo kill on Wei). The
   module draws a fight here at today's fitted rate; its winner comes from the fight model: roles in it top + jungle, pre-game edge
   +0.48k, strength 1.03, lanes even so far: **Gen.G wins it about 60% of the time** (fitted on all fights: 0.027 + 0.176 × 0.48 +
   0.304 × 1.03). Real: Gen.G 2–1.
3. **5:43 first dragon:** the taker model uses side (red's 2026 dragon edge, cancelled at Worlds by the Worlds term), strength, and the bot,
   mid and jungle edges at that minute. Real: IG took it.
4. **8:10–8:28 grubs:** each grub a contest (top, mid and jungle edges, kills just before, both teams' grub priority). Real: IG 2, Gen.G 1.
5. **8:39–9:04 bot-side teamfight** (five kills): roles everywhere; Gen.G's pre-game edges and lead by then make them favourites. Real:
   Gen.G 4–1.
6. **Plates:** each side-lane-minute from that lane's edge and who just died. Real: Gen.G top 3, IG bot 3, mid 1 each.
7. **At 14:00** the current sim takes over with each player's gold, the kills and deaths, who is dead and for how long, plates and towers,
   dragons and grubs.
8. **Lanes at 10 / 15:** real top +108 / +962, jungle +1,455 / +1,788, mid +149 / −367, bot +978 / +565. The module's lanes come out as the
   pre-game expectation plus whatever its fights and plates did: a game where Canyon wins the 3:45 fight gets a big jungle lead, as here.

The other 14 traced games are in the traces file. One game can't be "right": the tests below judge the module over all Worlds games.

## New and changed files (research only)

| File | Change |
|---|---|
| `research/laning/s5_fit_laning.py` (new, on `research/lib`) | Fits every table the module reads, from the step 1 models: lane model effects, the event-gold worth, leftover lane noise, fight winner, plates, first dragon, grubs, team grub priority. Writes one params file per fit cut-off: one per Worlds test day (fitted only on earlier games) and one on every game (for the app later). Run records as usual |
| `research/sim3/s3_sim.py` | The option `cal["laning"] = "actions"` (reads `P["laning"]`): lane gold, fight winners, plates, first dragon, grubs, death timers on, from 0:00 to 14:00; everything else untouched. Inputs per game in `x`: each role's pre-game expected edge, both teams' grub priority, a Worlds flag |
| `research/sim3/s3_test.py` | Option flag `la` (and Worlds day-by-day fits picked by date) |
| `research/laning/s5_laning_check.py` (new, on `research/lib`) | The checks below, real v sim, on Worlds day by day, then 2026 from 1 Sep |
| `research/laning/report_tables.py`, a step 3 report | Generated tables |

No app file changes in step 3. The app port (JS engine, tables, play-by-play lines for lane fights, ganks, plates, and the draft AI's lane
tables) is step 5, after the tests, with its own plan.

## Tests (Worlds day by day first, then 2026 non-Worlds from 1 Sep; 1,000 sims a game, seeds by game ID)

The module must match real games on:
- **Lanes:** gold edge at 10 and 15 by lane (spread, and how often the higher-rated lane wins it); the team gold edge at 15 and how tied it
  is to team strength (too tied in every earlier sim).
- **Early fights:** kills before 14:00 by role and lane, first blood time and role, and how often the side favoured by the fight model wins
  (real Worlds: 62% for the strongest fifth, 47% for the weakest).
- **Plates** by lane; first tower lane and time; **first dragon** and **grub** takers and timing.
- **Re-deaths inside the death timer:** real 0.0%.
- **Who wins the game:** log loss inside the noise band (0.6013–0.6069 on the short Worlds test) and against the current default (0.6041).
- **Replay:** with the option off, every earlier seeded game identical.

## Questions for Luke before building

1. **Fight timing stays as today's fitted rates** (step 1: when and where early kills happen barely moves with lane state; who wins them
   is what the data supports). OK, or should I look for more data on timing first?
2. **Lane gold from actions only** (revised, Luke 14 Nov): no leftover noise; the gap found above is closed by measuring the missing gold
   sources, not by a noise term.
3. **Fits per Worlds day for the tests** (each test day uses tables fitted only on earlier games), then one fit on every game for the app.
   OK?
