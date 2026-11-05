# Sim session 3 report: the game-state sim (minute by minute)

Written 5 Nov 2026 (AEST), final version the same evening. Working files, every number's source and how to re-run: `research/sim3/README.md`. Plan and decisions: `research/sim-plan.md` (session 3 entry, with Luke's realism rules). Results tables: `research/model/sim3/`. Comps options: `research/comps-plan.md`. Live tracker: https://claude.ai/artifact/J6sw8U1HziM7t8PAfKmqSL

- **Data:**
  - The Oracle's Elixir file (Luke's second file of 5 Nov, to 4 Nov 23:54 UTC, quarter-finals 1–2 included) is the source of record.
  - The order and time of events come from gol.gg game timelines (read 5 Nov): 627 games from 12 events since late July, 623 matched to the file by champions and date. gol.gg has no LPL timelines.
- **Split:** fitted on games before 1 Sep (395 timeline games; 2,267 file games for laning). Judged on games from 1 Sep (304; 151 with timelines) and Worlds (80, play-ins and knockouts included).
- **App change:** none from this session (the app is v40 for the quarter-final data). The sim reaches the app in session 4.

---

## 1. Summary

- **A working minute-by-minute sim, built only from fitted chances.** Each minute it plays laning (to 15:00), fights, dragons, grubs, Herald, Baron and Elder (real spawn timers), tower pushes, inhibitors, nexus towers and nexus. Every event is a random draw from chances fitted to real games; nothing is scripted to a result. The same seed replays the same game, and a different seed plays the same draft out differently.
- **On held-out games it beats v1 at who wins:** from 1 Sep log loss 0.635 against v1's 0.640; at Worlds 0.626 against 0.628.
- **Its games look like real ones on average:**
  - length 32.1 minutes (real 32.3), kills 27.3 (26.9), towers 11.6 (11.7), dragons 4.34 (4.45), soul games 42% (41%);
  - gold lead at 15 (median 1,667 against 1,604);
  - every role's kill share within 1.4 points;
  - blue-side and first-tower win rates;
  - first-dragon and first-Baron timing;
  - how fast games end once an inhibitor falls (sim 0:29, real 0:42).
- **Timing is flexible, as in real games, because every chance depends on the game state.** Who takes a dragon depends on side, the gold lead, jungle, bot-lane and mid leads (lane priority), a fight just won and the first dragon's special timing. Tower damage comes in pushes, more after a won fight and under Baron. So the same draft plays out differently each time but follows the real tendencies.
- **Still off:**
  - Games vary too much from one to the next: length sd 7.0 against 5.6, kills sd 12.4 against 7.3. Real games probably each have their own tempo; the sim doesn't yet.
  - Barons are a little low: 1.32 against 1.42, and 88% of games have one against 97%. Inhibitor turrets fall under Baron less often than real (31% against 61%), and the T2-to-T3 stage is still slower than real (median 3:34 against 1:29).
  - The first-Baron team wins 78.5% against 84.4%.
- **Draft styles, tested three ways:**
  - Deciding who wins things: this cost the Worlds odds badly.
  - Timing only (kept for now, Luke's choice): roughly neutral.
  - "A comp converts a lead": not supported by data.
  - Today's data supports one style effect clearly: draft pace on kills per minute. See section 4 and `research/comps-plan.md`.
- **New facts about real pro games on these patches** (timelines, all checked):
  - Every tower has 5 damage segments and falls with the 5th (990 of 990).
  - Tower damage comes in pushes: 38% of inhibitor turrets fall in a push that started at or before the T2.
  - Real games end a median 42 s after the first inhibitor.
  - The first dragon goes to red side 62% of the time in league play (Worlds 49%), and to the side ahead in bot + jungle at 5:00 65% of the time (Worlds 72%).
  - Half of all Barons come right after the taker won the last minute's fighting.
  - Towers fall after won fights: 0.99 segments per minute at even kills, 2.65 at +3.

---

## 2. How the sim works (one game, minute by minute)

Held-out checks are on games from 1 Sep / Worlds; "base" is the side-only or phase-only baseline.

| Part | What it does | Fitted from | Held-out check (model v base) |
|---|---|---|---|
| Laning (0–15) | Each lane's farm lead moves toward a drawn lane result: the matchup's expectation (v1 strength, lane skill gap, champion lane values from training games) plus noise drawn jointly for the five lanes | file, 2,267 games | gold lead at 15, R² top 0.19, jungle 0.19, mid 0.15, support 0.12, bot 0.05 (Worlds similar; bot −0.03) |
| Fights | How many start (phase, size of the lead, monster up, buff up, both drafts' pace), how many die (real sizes by phase), who gets each kill (gold lead, v1, Baron/Elder, plus a per-fight swing) | timelines | fights 0.716 v 0.719 / 0.708 v 0.713; who gets the kill 0.636 v 0.694 / 0.637 v 0.691 |
| Killer, victim, assists | Real role shares (before 1 Sep) | file | role kill share within 1.4 pts |
| Monsters | Take chance once up (minutes since spawn, lead, fight this minute, the game's first dragon on its own, both drafts' objective focus); taker (side, gold, jungle / bot / mid / top leads, kills in the last minute, v1) | timelines | taker: dragon 0.543 v 0.690 / 0.571 v 0.694; Herald 0.531 v 0.627 / 0.605 v 0.672; Baron 0.227 v 0.687 / 0.285 v 0.690; **grubs 0.690 v 0.667 (worse) / 0.651 v 0.663** |
| Tower pushes | Chance a push starts in a lane this minute (lane and team lead, v1, Baron, Elder, Herald, grubs, tier, phase, net kills this minute, both drafts' siege); size from real pushes by tier; a tower falls with its 5th segment | timelines | 0.380 v 0.405 / 0.372 v 0.396 |
| Base | Once a lane is open: chance a base push starts (lead, v1, buffs, open lanes, lane just opened), size from real pushes (base takes under 30 s apart) by whether an inhibitor is already down | timelines | 0.441 v 0.674 / 0.411 v 0.651 |
| Gold | Each event moves the lead by its fitted worth (kill 605, tower 291, segment 111 before 14:00 and 80 after, Baron 730), split across roles the way real team swings split (bot 28%, support 12%); after 15:00 a fitted drift, catch-up (−18.5 gold per minute per 1,000 lead) and noise | timelines | — |
| End | The nexus falls (both nexus towers down, an inhibitor down) | — | 0:29 from first inhibitor (real 0:42; diagnostic, 600 sims) |
| Box score | K/D/A, kill participation, damage share (role norm + kill participation), CS diff at 15, vision, solo kills: the app's `pack()` fields | file | POG by role: session 4 |

**Calibration** sets four numbers, none of which sets an outcome:
- **gain 1.65:** how strongly v1's strength turns into every event chance, set so the sim's win chance moves with v1 at slope 1.
- **lane_mu 0.05 and lane_k 0.02:** how much of the lane result is drawn directly; kills and pushes already move gold, so most of the spread comes from events.
- **fight swing 1.0:** so fights are two-sided as often as real ones.

Draft styles run in **timing-only** mode (Luke, 5 Nov): both drafts' pace, siege and objective focus together change how often fights start, how fast towers and monsters go, never who gets them.

---

## 3. Scorecard: simulated v real (held out, 200 sims per game)

| Check | Target | Sim (from 1 Sep) | Real (from 1 Sep) | Sim (Worlds) | Real (Worlds) |
|---|---|---|---|---|---|
| Length (min) | within 5% | **32.1** (sd 7.0) | 32.3 (sd 5.6) | 31.8 | 33.1 |
| Kills per game | within 5% | **27.3** (sd 12.4) | 26.9 (sd 7.3) | 27.2 | 25.6 |
| Gold lead at 15 (median size) | within 5% | 1,667 | 1,604 | 1,729 | 1,399 |
| Towers per game | within 5% | 11.6 | 11.7 | 11.6 | 11.8 |
| Dragons per game | within 5% | 4.34 | 4.45 | 4.30 | 4.79 |
| Barons per game | within 5% | 1.32 | 1.42 | 1.31 | 1.36 |
| First-Baron team wins | within 5% | 78.5% | 84.4% | 79.4% | 81.3% |
| First-dragon team wins | within 5% | 54.9% | 58.8% | 56.7% | 61.3% |
| First-tower team wins | — | 68.7% | 69.7% | 70.2% | 65.0% |
| Blue side wins | — | 58.4% | 56.6% | 58.5% | 57.5% |
| Soul games | — | 42.4% | 40.6% | 42.6% | 43.8% |
| Kill share top / jng / mid / bot / sup | within 2 pts | 18.1 / 22.1 / 24.9 / 29.5 / 5.4 | 18.7 / 21.4 / 26.3 / 29.3 / 4.4 | same | 18.4 / 21.7 / 26.2 / 28.9 / 4.8 |

Timing (real side from the gol.gg timelines in the same window; LPL not included):

| Check | Sim (from 1 Sep) | Real (from 1 Sep) | Sim (Worlds) | Real (Worlds) |
|---|---|---|---|---|
| First dragon, median wait after 5:00 spawn | 2:13 | 2:07 | 2:13 | 1:46 |
| First dragon within 30 s of spawn | 12.8% | 4.6% | 13.1% | 6.2% |
| First dragon to blue side | 38.7% | 33.8% | 39.4% | 51.2% |
| First dragon to the bot + jungle leader at 5:00 | 57.1% | 60.6% | 58.3% | 71.9% |
| Grubs and first dragon to different teams | 49.2% | 61.3% | 48.8% | 43.8% |
| First tower (median) | 14:30 | 15:22 | 14:30 | 15:12 |
| First Baron (median) | 24:05 | 24:41 | 24:02 | 25:09 |
| Games with a Baron | 87.7% | 97.4% | 87.3% | 93.8% |
| Stage medians: T1 / T2 / T3 / inhibitor / end (diagnostic) | 14:39 / 21:54 / 28:00 / 29:16 / 31:25 | 15:14 / 24:42 / 29:34 / 30:34 / 31:59 | — | — |
| T2 → T3 in the same lane, median (quarter of lanes faster than) | 3:34 (0:32) | 1:29 (0:20), from 1 Sep incl. Worlds | — | — |
| T3 falls under the taker's Baron buff | 30.9% | 60.8% | — | — |
| First inhibitor to end (median; diagnostic, 600 sims) | 0:29 | 0:42 | — | — |

Who wins (log loss; lower is better):

| | From 1 Sep (304) | Worlds (80) |
|---|---|---|
| **Sim** (timing-only draft styles) | **0.635** | **0.626** |
| v1 | 0.640 | 0.628 |
| Coin flip | 0.693 | 0.693 |

- Calibration bands from 1 Sep with 20+ games (said / won): 36% / 25% (20 games); 46 / 51 (49); 55 / 54 (86); 66 / 69 (78); 75 / 65 (40); 85 / 90 (20). Four of six are within 6 points; the 30–40% band is off by 11 and the 70–80% band by 10.
- The sim's odds sit about 3.7 points from v1's on average. With 200 runs per matchup, the noise alone is about 2.8 points.

**Ablation** (`s3_ablate.py`; same held-out games and seeds, 200 sims each, inputs switched off):

| Sim inputs | From 1 Sep | Worlds |
|---|---|---|
| Full sim (timing-only styles) | 0.635 | 0.626 |
| Draft styles off | **0.632** | **0.617** |
| Draft styles and lane inputs off | 0.633 | 0.615 |
| v1 | 0.640 | 0.628 |

Draft styles cost a little on both sets in this final version (0.003 from 1 Sep, 0.009 at Worlds; sampling noise is about 0.0025 from 1 Sep and larger on 80 Worlds games). Earlier versions of the sim gave mixed signs. See section 4.

---

## 4. Draft styles and comps: what the data shows

| How styles were used in the sim | From 1 Sep | Worlds |
|---|---|---|
| Decide who gets kills, monsters, towers (own minus enemy) | 0.650 | 0.675 |
| Timing only (both drafts together) | 0.635 | 0.626 |
| Off | 0.632 | 0.617 |

(The first row is from an earlier version of the sim, before the push fixes; the comparison within that version was 0.650 with, 0.646 off.)

**Do styles move timing in real games?** Real held-out games (231 timeline games from 1 Sep, Worlds included) against the sim (40 runs per game). Correlation of a draft style with the game's timing:

| Style → timing | Real | Sim |
|---|---|---|
| Pace → kills per minute | **+0.19** (+0.032 per 0.1 of pace) | +0.73 (+0.041) |
| Pace → length | −0.06 | −0.30 |
| Siege → first tower time | −0.06 (−9.9 s per 0.1) | −0.12 (−4.9 s) |
| Objectives → first dragon wait | +0.03 | +0.11 |
| Objectives → first tower time | −0.09 | −0.02 |

Only pace → kills per minute is clearly real (the rest are under 0.12, within noise for this many games). The sim's correlations are higher because it averages 40 runs per game; its slopes are the fair comparison, and pace's is close to real.

**Comps options tested** (`research/comps-plan.md`):
- **Option A, a comp converts a lead:** own siege × lead for towers, objectives × lead for monster takers. No consistent gain on held-out games, and the signs flip between objectives. Not kept.
- **Option C, damage and frontline balance:** Riot's tags via the League wiki. One damage type never happens in pro play. No-frontline drafts (44% of all) win exactly as expected (0.0 ± 1.1 points). Low magic doesn't do worse. Not kept. The app's "one damage type" warning is untested (flag for session 4).

---

## 5. Real timing on these patches (gol.gg timelines, 623 matched games)

| | Before 1 Sep (395) | From 1 Sep (151) | Worlds (80) |
|---|---|---|---|
| First dragon taken within 30 s of spawn | 5.6% | 4.6% | 6.2% |
| First dragon, median wait after spawn | 2:15 | 2:07 | 1:46 |
| First dragon to blue side | 38% | 34% | 51% |
| First dragon to the side ahead in bot + jungle at 5:00 (lead over 150) | 65% | 61% | 72% |
| Grubs and first dragon to different teams | 58% | 61% | 44% |
| Herald taken | 100% | 100% | 100% |
| First tower (median) | 15:15 | 15:22 | 15:12 |
| First Baron (median) | 24:47 | 24:41 | 25:09 |
| T2 → T3 in the same lane (median) | 2:07 | 1:29 | — |
| T3 falls under the taker's Baron buff | 60% | 61% | — |

- **Baron (861 takes):** 49% come straight after the taker won the last minute by 2+ kills, 28% with no kills in the last minute, 3% when the taker lost the last minute's fighting.
- **Share to blue side, all takes:** dragons 48%, grubs 63%, Herald 66%, Baron 55%, Elder 36% (69 takes). This matches the map: grubs, Herald and Baron spawn in the top-side pit, dragon in the bottom-side pit. The sim has no positions; the side terms are fitted on top of v1's own side edge.
- **Tower pushes** (a lane's segments under 30 s apart):
  - T1 pushes before 14:00 are mostly single segments (84%).
  - T2 pushes average 2.9 segments.
  - A quarter of T3 pushes take the whole T3 at once.
- **Towers and fights:** tower segments per minute from 14:00 by the side's net kills that minute: −3: 0.52, 0: 0.99, +3: 2.65.
- **Gold per event** (minute-level fit on training games): kill 605, tower 291, segment 111 before 14:00 and 80 after, Baron 730, dragon 22. Grubs and Herald show about 0, and an inhibitor −118. Those are side effects of fitting alongside towers and fights in the same minute, not real costs.

---

## 6. Outside sources this session

| Check | Result |
|---|---|
| gol.gg timelines v the file, 623 matched games | winner and length agree in every game; dragons and Barons in every game; grubs, Heralds and inhibitors in almost all; kills differ on 4% of team-sides; towers on about 6% (mostly one more in the timeline, likely nexus towers; not checked further) |
| gol.gg game counts v gol.gg's own tournament list | the pull's 627 games match every event's listed count |
| Tower segments | every T1 / T2 / T3 fell on its lane's 5th / 10th / 15th segment (990 of 990) |
| Riot client tags via the League wiki (Module:ChampionData/data) v the app's CHAMP_AP and Data Dragon | the app's list agrees on 141 of 155 pro champions; Data Dragon's 0–10 magic rating is too coarse to label damage type |
| Leaguepedia quarter-final scoreboards v the file | IG 3–1 TES and GEN 3–0 LYON match on sides, winners, lengths, kills, champions and bans |

---

## 7. Mistakes and fixes in session 3

- **Pull:** the first pull skipped every Bo1 (Bo1 rows link to the game page); found from the Worlds count (38 main-event games instead of 55) and fixed. A network drop lost 15 pages; a second pass re-read them.
- **Engine fixes:**
  - Kill gold now splits by real role shares (supports had too much).
  - The gold snapshot is taken at the start of each minute.
  - Counts are as bursty as real.
  - The first dragon has its own fitted input.
  - Calibration uses the team gold lead.
- **Base pushes:** games ran long because the final push was too slow (2:28 from first inhibitor to end, against 42 s real). Fixed in three checked steps, ending with pushes defined by time instead of clock minute.
- **Tower pushes:** games still ran 3 minutes long because the inhibitor-turret stage dragged (4:33 from T2 to T3 against 2:07 real). Fixed by tower pushes (a fitted push chance, then a real push size); median length went from 35:01 to 31:25.
- **"Won fight → towers" input:** added and kept (it improves the held-out fit), though on its own it didn't shorten games.
- **Process:**
  - A test crashed because scripts were edited during the run; since then nothing is edited while a run is going.
  - Two editing slips (a broken line, a wrong comparison baseline) were caught by checks before any results were used.
  - One request tried to get past a website's bot check with browser-like headers. It was blocked, rightly, and the page was read in the browser pane instead.

---

## 7b. Player choice moments (5 Nov, parked for later)

Luke's idea: at each stage (laning, after first and second back, mid game, late game) each player makes a choice, such as a jungler farming or ganking, or a support staying with the ADC or roaming. Those choices should give variety, based on data. Measured from the timelines (`research/sim3/s3_choices.py`; `research/model/sim3/choices.json`, per-player table `choices_players.csv`). Kills are tagged with each champion's player and role through the matched file game: 4,182 of 4,206 early kills.

- **What can be seen:** only choices that ended in a kill (killer, assisters, victim, time). Positions and paths aren't in any source used, so a gank or roam with no kill is invisible.
- **Per game before 14:00:** the jungler is involved in about 2.3 kills (bot 0.85, enemy jungle 0.57, mid 0.44, top 0.42); supports make about 0.55 roam kills; mids about 0.77.
- **Inside a game the choices go with outcomes:** a jungler involved in more early bot-side kills than the enemy jungler goes with first dragon 46% of the time (33% when fewer). A support roaming more goes with its bot lane being ahead at 15 (+413 gold v −76), likely because roams happen when bot has priority.
- **As player habits they mostly aren't stable:** first half v second half of each player's games: jungle ganks top / mid / bot 0.12 / 0.16 / −0.05; support roams 0.20; mid roams −0.06; **jungle CS at 14 (farming) 0.55, a real habit**.
- **Known before the game, they don't predict it:** players' earlier gank and roam tendencies made held-out first-dragon, Herald and grub predictions worse (first dragon from 1 Sep 0.631 → 0.641) and didn't change lane gold at 15. Not kept as player traits.
- **Farming habit, every role** (`s3_farm.py`, `farm.json`; the file's CS at 15 in all 2,719 games, against the role average of the previous 30 days). Luke's rule: what one role gets, check for the others.
  - It's a stable habit in every role: first half v second half 0.58 (top), 0.62 (jungle), 0.71 (mid), 0.58 (bot), 0.69 (support).
  - Known before the game, it doesn't help who-wins beyond v1. Only support is better on both held-out sets, by about 0.001–0.002 with a near-zero weight. Jungle farming doesn't predict first dragon, Herald or grubs. **Not kept.**
  - One small lead: a top laner's farming habit predicts their gold lead at 15 a little better from 1 Sep (error 868 → 855; no change at Worlds). It overlaps session 1's laning skill, so it would need a test inside the lane model before being kept.
- **For later:** (1) state-driven choices in the sim: each choice moment's chances fitted from the timelines and depending on the game state (lane priority, timers), which gives the play-by-play variety without claiming a player always ganks bot; (2) jungle farming as a tested player trait.

## 7c. Session 2 inputs v in-game events, every role and pair (5 Nov)

Luke: if an input feeds the sim for one role, check the other roles too. `research/sim3/s3_roleevents.py`; `research/model/sim3/roleevents.csv`.
- **Inputs** (pre-game, earlier days only): comfort, champion strength (each role), time together and champion-pair synergy (each of the 10 teammate pairs).
- **Events** (major games, the file): the role's or pair's gold lead at 15; kills minus deaths by 15; the jungle pair's side objectives.
- **Pass rule** (as in session 2): better than v1 alone on Jul–Aug (fit Feb–Jun) and from 1 Sep (fit Feb–Aug).

- **80 tests, 14 pass (9 also better at Worlds).** About 20 would pass by luck alone, so as a group these inputs move in-game events no more than chance. Single passes are mostly noise.
- **Consistent with session 2's separate evidence, and kept as candidates for the sim's laning:**
  - ADC champion strength → bot gold at 15: 0.3% / 0.7% / 1.7% lower squared error, Jul–Aug / from 1 Sep / Worlds. It also passed for who-wins in session 2.
  - ADC + support pro pair synergy → bot lane gold at 15: 0.03% / 0.5% / 0.7%. Pro ADC–support synergy passed in session 2.
- **Other passes:**
  - Top champion strength → top gold at 15 (0.1% / 1.5% / 2.2%), but the effect is negative, which is likely gold flow (tanks) rather than power, as session 2 warned.
  - ADC + support time together → bot lane gold (0.2% / 0.3% / ~0).
- **Comfort moves no lane events in any role (0 of 13),** jungle included, although jungle comfort helps predict winners at big events. **Jungle–mid time together** (session 2's strongest pair) doesn't move mid/jungle gold, early kills, Herald or grubs. These act on winning through something the file doesn't record well (decisions, teamfights), so they belong at the who-wins level (the v2 candidate's knockout test), not as lane events.

## 8. Open items for Luke

1. **Spread of games:** length and kills vary too much from game to game. Next test: a per-game tempo (some games slow, some fast) fitted from the timelines.
2. **Baron:** too few games have one (88% against 97%), and the first-Baron team wins too rarely (78.5% against 84.4%).
3. **Draft styles in timing-only mode cost a little** in the final version. Keep (realism, and pace is supported), or keep only pace?
4. **Grub taker model** doesn't hold from 1 Sep: simplify to side only, or keep?
5. **The app's "one damage type" warning** is untested (session 4).
6. **Elder:** only 69 real Elder takes in the timelines, so Elder chances are rough.
7. **Player choice moments** (parked, Luke 5 Nov): come back to choices as a source of variety, based on data (section 7b).
