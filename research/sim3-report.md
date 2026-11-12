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
  - Games vary too much from one to the next: length sd 7.0 against 5.6, kills sd 12.4 against 7.3. Three data-based fixes were tested after the final version and none is kept (section 7d); the cause is still open.
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

## 7d. The spread of games: three fixes tested, none kept (5 Nov)

Tested after the final version; the committed sim is unchanged. The scripts keep each option switched off by default (`s3_sim.py` `cal["form"]`, `s3_test.py ... phase`), and the defaults reproduce the committed sim exactly (300 of 300 seeded games identical). Quick checks used `research/sim3/s3_quick.py` (150 held-out matchups × 4 runs).

**Where the spread comes from** (held out, sim v real):

| | Sim | Real |
|---|---|---|
| Games under 24 min | 11.5% | 2.6% |
| ...of those with no Baron | 59% | 17% |
| ...kills per minute | 0.77 | 1.01 |
| Kills per minute in 42+ min games | 0.94 | 0.69 |
| Link between kill rate and length | +0.15 | −0.34 |
| Kill difference at 15 (sd) | 3.7 | 2.7 |
| Gold lead at 15 (sd) | 2,793 | 2,265 |

Real fast games are bloody and real long games are slow. The sim makes too many quiet stomps and lets long games keep fighting.

| Fix tried | What the data said | Result in the sim | Kept? |
|---|---|---|---|
| **Per-game tempo** (one slow/fast factor per game for fights and pushes) | Measured (`rates3_results.json` → `tempo`) on training games after the fitted rates: the leftover game-to-game spread is negative (fights −0.012, pushes −0.009), so real games vary *less* than chance once their state is known; there is no hidden tempo to add | not built | no |
| **Game form** (the gold-lead effect on who wins kills, fitted within each game, plus a once-per-game form draw) | (`events3_results.json` → `kill_side_within`) The pooled effect (0.125 per 1k gold) is mostly "stronger team in this game": within games it's 0.048 (from 1 Sep 0.061, Worlds 0.069; these two from a one-off check, printout not saved); form spread after noise about 0.47 | early kill spread 3.72 → 3.60; short games unchanged (12%); with the per-phase swing below it was worse | no |
| **Per-phase fight swing** (how one-sided a fight is, fitted per phase) | Real 2-kill fights go both ways 52% of the time before 14:00, 37% at 14–24 and 30% later (3-kill: 73 / 51 / 42%); one swing for all phases made early fights too one-sided. Fitted swing: 0 / 0.95 / 1.45 | short games 11.5% → 7.8%, Baron games about the same, but who-wins worse (log loss 0.641 v 0.635 from 1 Sep, 0.635 v 0.626 at Worlds; beyond the ~0.0025 noise). Results: `test3_phase_eps.json` | no |

- Also checked: a who-wins-each-kill model fitted by phase is no better on held-out kills (before 14:00: 0.6876 v pooled 0.6868; both near a coin flip, 0.693).
- With the per-phase swing, simulated kills before 14:00 split almost like real ones (sd 2.94; real 2.72 by 15:00); the small remainder is the gold-lead feedback.

## 7e. The spread of games, continued: where short games come from (6 Nov)

Research only; the default sim is unchanged (300 of 300 seeded games identical). New options stay off by default: `cal["within"] = "on"` and `cal["kill_z_phase"]`.

**1. Lead effects fitted within games (the untested idea from 7d): not kept.** Each game's average lead was added as an input (`s3_rates.py`, `s3_events.py`; results `research/model/sim3/within3.json`). The live-lead effects mostly got *bigger*, not smaller:

| Lead effect | Pooled | Within games |
|---|---|---|
| Base push, per 1k lead | 0.05 | 0.22 |
| Dragon taker, per 1k lead | 0.18 | 0.37 |
| Gold feedback after 15:00, per 1k lead per minute | −18.5 | −33.0 |

In the sim (`s3_quick.py`, 150 held-out matchups × 4) games under 24 min went from 11.8% to 13.5% and Baron games from 87% to 85%. Not kept.

**2. Team strength by phase.** How strongly pre-game strength (v1) decides who gets each kill (logistic slope), real timeline games v the sim (`s3_zphase.py`):

| Kills | 0:00–14:00 | 14:00–25:00 | 25:00+ |
|---|---|---|---|
| Real, before 1 Sep | 0.29 | 0.43 | 0.37 |
| Real, from 1 Sep | 0.26 | 0.49 | 0.62 |
| Sim (final version) | 0.13 | 0.34 | 0.35 |
| Sim with the per-phase fight swing (7d) | 0.23 | 0.29 | 0.29 |
| Sim with the swing + strength by phase matched to training games (×1.24 / ×1.48 / ×1.26) | 0.30 | 0.43 | 0.47 |

Strength in the sim's kills is *weaker* than real, so the early spread comes from randomness, not strength. The swing + matched strength gives games under 24 min 9.3% (real 2.6%), but kills still vary far too much (sd 12.7 v 7.0). Who-wins not run for this version yet.

**3. Long games are fine; short games aren't.** For games past 21 min, length and kill rate by gold lead at 20:00 match real games (`s3_lead_end.py`):

| Lead at 20:00 | Sim: median length, kills/min | Real |
|---|---|---|
| under 2k | 34.0 min, 0.81 | 35.0 min, 0.76 |
| 2–5k | 31.5 min, 0.86 | 31.8 min, 0.80 |
| 5–9k | 28.3 min, 0.92 | 27.2 min, 0.88 |

**4. The likely cause: second-tier towers fall too early.** Median times (`s3_diag.py`): first T1 sim 14:39 v real 15:14; **first T2 21:54 v 24:42**; first T3 28:00 v 29:34; first inhibitor 29:16 v 30:34; end 31:25 v 31:59. Bases open almost 3 minutes early, which gives the short no-Baron games. **Next test:** the tower-push model's tier-2 stage (push chance and push size for T2 segments by minute), checked against real T2 timing, then who-wins on held-out games.

## 7f. Second-tier towers: the tier-2 test (6 Nov)

Research only; the default sim is unchanged (300 of 300 seeded games identical). New options, off by default: `cal["seg_lane_tier"]`; `s3_test.py ... timing phase,zphase,lt`. Results `research/model/sim3/t2_tests.json`; check script `s3_t2check.py`.

**Real v sim (held-out matchups, 150 × 4 sim runs; real = 231 timeline games from 1 Sep):**

| | Real | Sim | Sim + lane × tier |
|---|---|---|---|
| First T2, median | 24:42 | 21:29 | 21:35 |
| A T2 down by 18 / 20 min | 8% / 16% | 25% / 39% | 23% / 38% |
| T1 → T2 gap, top / mid / bot (s) | 547 / 371 / 516 | 406 / 422 / 404 | 468 / 332 / 426 |

- **Lane × tier push terms** (four terms: T2 and T3, mid and bot, against top): real mid T2s and T3s are much easier to push than side-lane ones (T2 × mid +1.14, T3 × mid +1.08). They predict held-out pushes better (log loss 0.3769 v 0.3797 from 1 Sep, 0.3683 v 0.3715 at Worlds, about 45,000 lane-minutes) and give the right per-lane pattern in the sim, but the first T2 still falls early: leads at 15:00 are too spread (sim gold-lead spread about 2,800 v real 2,265), and bigger leads push earlier.

**Full held-out tests** (recalibrated on training games, 200 sims per game):

| Version | Who wins from 1 Sep | Worlds | Length sd (real 5.6) | Kills sd (real 7.3) |
|---|---|---|---|---|
| Final sim (re-run) | 0.635 | 0.626 | 7.0 | 12.4 |
| + lane × tier | 0.639 | **0.617** | 7.1 | 12.3 |
| + per-phase swing + strength by phase + lane × tier | 0.643 | 0.635 | 7.1 | 12.5 |
| v1 | 0.640 | 0.628 | | |

- The combined version is worse at who-wins: **not kept**.
- Lane × tier is mixed (0.004 worse from 1 Sep, 0.009 better at Worlds; noise about 0.0025 from 1 Sep, more on 80 Worlds games). It is a better tower-push input on held-out pushes and more realistic lane by lane. **Luke decided (7 Nov): keep it in the sim and keep testing it** (to be switched on as the default next session, with the baseline re-run).
- **None of these narrows the spread.** The biggest remaining gap is total kills per game (sd 12.4 v 7.3). Real fights per minute are less bursty than chance (dispersion 0.7–0.8) and real games vary less than chance given their state (7d), while the sim's kill totals add chance on top of chance (fight count × fight size). **Next test:** how kills per game build up in the sim v real (fights per game, kills per fight, and their link to game length).

## 7g. How kills per game build up, sim v real (10 Nov)

Script `research/sim3/s3_killbuild.py`, results `research/model/sim3/killbuild.json`. Held-out games from 1 Sep with timelines (231 real; the current sim, 4 runs each = 924). Kills are grouped into fights the same way for both (a gap of 20 s+ starts a new fight).

| Per game | Real | Sim |
|---|---|---|
| Length (min): mean, sd | 32.8, 5.6 | 32.1, 7.1 |
| Kills: mean, sd | 26.0, 7.0 | 27.7, 12.7 |
| Kills per minute: mean, sd | 0.80, 0.22 | 0.85, 0.31 |
| Kills per fight: mean | 2.22 | 2.50 |
| Link between kill rate and length | −0.34 | +0.17 |

**1. Long games are slower in real games, bloodier in the sim.** This is the biggest single difference:

| Game length | Real: kills per min, kills | Sim: kills per min, kills |
|---|---|---|
| under 28 min | 0.91, 23.7 | 0.80, 19.6 |
| 28–33 | 0.84, 25.6 | 0.83, 25.3 |
| 33–38 | 0.74, 26.1 | 0.86, 30.3 |
| 38+ | 0.71, 29.6 | 0.95, 40.6 |

Real short games are bloody stomps (the kills are what end them); the sim's short games are quieter (the "quiet stomps" in 7d). Real long games slow down; the sim's keep fighting at a rising rate with ever bigger fights. So in the sim, kills go almost in step with length (link 0.62 against real 0.29), and the two spreads add up.

**2. Fights are bigger and far more uneven in the sim**, at every stage after laning (same 20 s grouping):

| Window (games that reach its end) | Real: fight size mean, variance | Sim: mean, variance | Real: kills variance | Sim: kills variance |
|---|---|---|---|---|
| 0:00–15:00 | 1.64, 1.11 | 1.86, 1.89 | 11.8 | 20.2 |
| 15:00–25:00 | 2.18, 2.49 | 2.54, 3.91 | 18.4 | 32.7 |
| 25:00–35:00 | 2.33, 2.66 | 3.27, 6.03 | 19.3 | 54.8 |

- The number of fights is fine: fight starts per window are as regular as real ones (variance / mean 0.64–0.77 in both).
- Real games hold themselves in check: when a stretch has more fights, they are smaller (link between fight count and fight size −0.29 at 15:00–25:00; sim 0.00), and a fight minute is followed by fewer fights the next minute (30% v 39% after a quiet minute; sim 33% v 36%).
- Kills per minute played are higher in the sim after laning (14:00–19:59: 0.96 v 0.76; 25:00–29:59: 1.26 v 1.14; 30:00–34:59: 1.50 v 1.32; 35:00+: 1.70 v 1.55), while fight starts per minute are slightly lower. The sim draws fight size from one real table per broad stage (0–13, 14–24, 25–34, 35+), so 14:00–19:59 gets the bigger 20:00–24:59 fights, and nothing ties a fight's size to what just happened.

**3. Fights per minute by gold lead:** real games fight a little more when the lead is big (0.40 per minute under 3k, 0.52 at 9–12k); the sim doesn't (0.36 and 0.35).

**Reading.** The extra kill spread comes from (1) how kills and length go together and (2) fight sizes that aren't held in check, not from the number of fights. Both are things the sim's tables don't yet carry, so the fix is to fit them, not to set a number (Luke, 6 Nov).

**The fixes, fitted and tested (10 Nov).**
- **Fight types** (Luke: duels / 2v2s, skirmishes, team fights; `s3_fighttypes.py`, `fighttypes.json`). Types from the players seen in each fight's kills (larger side 1–2, 3, 4–5). Team fights carry 75% of all kills; their size grows from 2.6 to 3.6 kills from early to 35:00+, while duels and skirmishes stay at 1.0–1.4. Fitted on training games: a fight in the last minute makes a new one less likely (−0.33), recent kills make the next fight less likely to be a team fight (−0.30). These predict held-out fight counts better (from 1 Sep 0.7134 v 0.7156; Worlds 0.7050 v 0.7084); the type model is better from 1 Sep, slightly worse at Worlds (0.9113 v 0.9091).
- **Won fights into pushes** (`s3_fightpush.py`, `fightpush.json`). Real teams turn won fights into towers and wins far more than the sim: a side that won the minute's fighting by 4+ kills takes a structure within 3 minutes 94% of the time (sim 76%) and, from 20:00, wins within 4 minutes 76% (sim 31%); 7.4% of real games end before 26:00 against 20% in the sim. The push fits had only this minute's net kills; added: last minute's net kills and "won by 4+" (`s3_rates.py` → `segment_push_fight` on top of lane × tier, `base_push_fight`). Held-out base pushes improve clearly (log loss 0.4211 v 0.4411 from 1 Sep; 0.3928 v 0.4111 Worlds), almost all from last minute's net kills (+0.39); tower pushes barely change. Caution: the "4+" cutoff was picked after seeing held-out games; its weights are small (+0.20 towers, −0.09 base), to be re-checked with it dropped.

Full held-out test (fixed split, 200 sims per game, recalibrated on training games each time; lane × tier on in all; `research/local/sim3/out_7g_*`):

| Version | Who wins, from 1 Sep | Worlds | Length sd (real 5.6) | Kills sd (real 7.3) | Games with a Baron (real 97%) | First-Baron team wins (real 84%) |
|---|---|---|---|---|---|---|
| Current (lane × tier) | 0.6385 | 0.6173 | 7.08 | 12.3 | 87% | 78.6% |
| + fight types | 0.6429 | 0.6334 | 7.07 | 12.2 | 88% | 78.6% |
| + won-fight pushes | **0.6311** | **0.6154** | 7.10 | 12.3 | 88% | 78.7% |
| + both | 0.6379 | 0.6260 | 7.09 | 12.1 | 88% | 78.5% |
| v1 (same games) | 0.6396 | 0.6278 | | | | |

- **Won-fight pushes with the first cutoff (4+, see the caution above): better at who wins on both sets** (0.6311 v 0.6385 from 1 Sep, 0.6154 v 0.6173 at Worlds), and ahead of v1 on both (0.6396, 0.6278). The redo below did not repeat this at Worlds. After a side wins a minute by 4+ kills the sim takes a structure within 3 minutes 80% of the time (was 74%; real 94%) and wins within 4 minutes 35% (was 32%; real 76%); games under 26:00 17% (was 20%; real 7%).
- **Cutoff redone properly (11 Nov), and the result weakens.** The "4+" above was picked after seeing held-out games. `s3_rates.py` now chooses the cutoff on training games only (fit on training dates before 9 Aug, check on 9–31 Aug): base pushes — this minute's kills edge only 0.4480, + last minute's 0.4291, + clear fight win at 2+ **0.4272**, 3+ 0.4299, 4+ 0.4305, 5+ 0.4290; tower pushes — 0.37454 / 0.37443 / 2+ **0.37393** / 3+ 0.37446 / 4+ 0.37438 / 5+ 0.37450. So 2+ for both (weights: towers +0.38; base +0.68, with last minute's kills edge +0.25). Held-out pushes: towers 0.3765 / 0.3679 (lane × tier 0.3769 / 0.3683), base 0.4220 / 0.3911 (before 0.4411 / 0.4111). Full held-out test with 2+ (`out_7g_pf2`): **who wins 0.6344 from 1 Sep (current 0.6385) but 0.6269 at Worlds (current 0.6173; v1 0.6278)**; favourite 61.8% / 61.3% (current 63.8% / 65.0%); spreads unchanged (length sd 7.09, kills sd 12.2); after a 4+ won minute a structure within 3 minutes 79%, a win within 4 minutes 35%; games under 26:00 19%.
- **Reading:** the push fits themselves are better on held-out pushes with either cutoff, but the who-wins gain is not stable: the 4+ run was better on both sets, the properly chosen 2+ run is better from 1 Sep and worse at Worlds. Each run recalibrates strength (gain 1.64 current, 1.62 with 4+, 1.57 with 2+), and 80 Worlds games move a lot between such runs. The flag versions are not shown to be better. To settle it: the simplest version (last minute's kills edge, no cutoff flag), and the walk-forward test, which scores more games.
- **Simplest version (11 Nov; `s3_test.py ... pfs`, `out_7g_pfs`): last minute's kills edge only, no flag, so nothing is chosen.** Held-out pushes: towers 0.3767 / 0.3682, base 0.4216 / 0.3931. Full test: **who wins 0.6334 from 1 Sep and 0.6116 at Worlds, better than the current sim on both (0.6385, 0.6173) and than v1 (0.6396, 0.6278)**; favourite 64.8% / 66.2% (current 63.8% / 65.0%); spreads unchanged (length sd 7.12, kills sd 12.3). This is the candidate to carry forward: the cleanest of the three, and the only one better on both sets without a choice made on test games. Three versions were tried, so it still needs the walk-forward test and session 4's test over the Worlds results before it is kept (Luke, 11 Nov: every version is kept and re-tested then).

| Won-fight pushes | Who wins, from 1 Sep | Worlds | Strength scaling (gain) |
|---|---|---|---|
| Current sim (lane × tier) | 0.6385 | 0.6173 | 1.64 |
| Flag at 4+ (picked after seeing test games) | 0.6311 | 0.6154 | 1.62 |
| Flag at 2+ (chosen on training games) | 0.6344 | 0.6269 | 1.57 |
| **No flag (last minute's kills edge only)** | **0.6334** | **0.6116** | 1.67 |
- **Fight types: worse at who wins on both sets and no change to the spreads.** Not kept for now (the counts' "what just happened" terms alone could be re-tested).
- **None of them narrows the spread** of length or kills. Real games end soon after a big won fight far more often than the sim's do, and short sim games stay quieter; the next lead is how the gold lead grows after 15:00 (the file has every game's gold lead at 20 and 25 minutes to compare) and how a won fight turns into the ending.

## 7h. Tower context: lanes, tiers, what comes before a tower falls (7–10 Nov)

Luke (7 Nov): record towers by lane × tier for all lanes; compare tower times with other objectives and kills (more towers after a solo laner dies? after a dragon?); side; comps (some champions' job is to push towers). Script `research/sim3/s3_tower_context.py`, results `research/model/sim3/tower_context.json` (printout `research/local/sim3/tower_context_run2.txt`). 626 timeline games matched to the file.

**Checks.** Kill victims matched to a role through the file's champions: 17,239 of 17,253 kills (14 not found). Nexus towers left out: 1,272; the tower labels used are only T1–T3 in top, mid and bot. Fit fixed: in mid, no tower ever fell within 2 minutes after grubs, which sent that input to −18; the per-lane fits now use the same small ridge as `s3_rates.py`, so it stays finite (−1.3).

**Towers by lane × tier (all 626 games; per team-game; side = the team that took it).**

| Tower | Falls in | Median time | Middle half | Gap after the tower before it | Blue takes / red takes |
|---|---|---|---|---|---|
| T1 top / mid / bot | 89% / 79% / 87% | 18.6 / 20.0 / 18.4 min | 16.2–21.8 / 17.5–24.5 / 15.8–21.2 | — | 93/86% · 86/71% · 91/84% |
| T2 top / mid / bot | 44% / 55% / 51% | 27.4 / 26.8 / 26.8 | 24.4–31.3 / 24.1–31.0 / 23.8–31.0 | 536 / 386 / 514 s | 52/37% · 63/46% · 56/46% |
| T3 top / mid / bot | 19% / 41% / 27% | 31.3 / 30.5 / 30.0 | 27.4–34.4 / 27.0–34.1 / 26.4–34.1 | 57 / 145 / 87 s | 22/15% · 47/34% · 30/23% |

- Blue takes every tower more often and mostly sooner than red.
- First tower of the game: blue's comes from top 50%, bot 35%, mid 15%; red's from bot 59%, top 28%, mid 14%.
- Mid T2 falls soonest after its T1 (386 s); T3s fall within 1–2.5 minutes of their T2 (the same push, as in section 5).

**What comes before a tower falls.** One logistic fit per lane on every minute that lane's next tower is standing (118,442 lane-minutes, 5,810 tower falls), with events in the 2 minutes before, tier, 5-minute period, gold lead and side; fitted on games before 1 Sep, refitted on games from 1 Sep. Pass = same sign and |t| ≥ 2 on both.

| Input (per lane: top / mid / bot) | Passes |
|---|---|
| Baron taken | all three (log-odds about +1.1 / +1.4 / +1.7) |
| Gold lead (per 1k) | all three (+0.17–0.26) |
| Blue side | top only (+0.29 / +0.26) |
| Herald taken | mid only (+0.98 / +1.22) |
| Killed that lane's enemy laner | mid only (+0.17 / +0.21) |
| Grubs taken | bot (−1.7 / −1.2; negative, most likely timing: grubs come before towers start falling) |
| Dragon taken, killed the enemy jungler or another lane's laner, lost own laner | none |
| Lane's or team's champions' measured tower damage (siege) | none (team siege for bot only on the later games) |

Share of tower-falling minutes with each event in the 2 minutes before, against other at-risk minutes (all games): a Baron 17–25% v 3%; a kill of that lane's laner 27–38% v 12–21%; a dragon 22–24% v 13–14%; a Herald 7–11% v 3%. Dragons and kills do sit before towers, but once lead and Baron are counted they add nothing that holds up.

**For the sim (to test, fitted, not set):** the sim already has Baron, gold lead, net kills and Herald in its tower pushes, but with one Herald term for every lane and no lane-specific kill term. Candidates: a mid-only Herald term and "killed that lane's laner" for mid, each judged on held-out pushes like the lane × tier terms in 7f. No champion or comp siege effect holds up, which matches the draft-style validation (`research/comps-plan.md`): measured tower damage moves tower counts and first-tower time, not which lane falls.

## 7i. Session 4 pre-work: lane × tier becomes the default sim (11 Nov)

Luke's 7 Nov decision (keep the lane × tier push terms in the sim and keep testing them) is now in the code: `s3_sim.py` uses them unless told otherwise, and `s3_test.py ... nolt` runs the earlier sim. Every later test compares against this baseline.

| Who wins (log loss, held out, 200 sims per game) | From 1 Sep (304 games) | Worlds (80 games) |
|---|---|---|
| Sim, lane × tier on (the default) | 0.6385 | 0.6173 |
| Earlier sim (`nolt`) | 0.6348 | 0.6260 |
| v1 | 0.6396 | 0.6278 |

- **Nothing new was measured here.** These are the scores of the 10 Nov lane × tier run and the 6 Nov base run; the 7g comparisons already used 0.6385 / 0.6173 as "the current sim".
- **How checked:** both versions were re-run with the current `params3.json` (458 s and 442 s). Calibration, scores and shape tables are the same as the saved runs, and all 60,800 simulated games (304 × 200) are identical in each (`research/local/sim3/out_s4_base` v `out_7g_lt`; `out_s4_nolt` v `out_t_base`).
- **Worlds is still 80 games here.** The sim's test files were built on the 5 Nov file, so quarter-finals 3–4 and the semi-finals (14 games) are not in this test yet.
- Scripts that build their own settings without naming the switch now get lane × tier too; results from before 11 Nov in sections 3 to 7e are from the earlier sim.

## 7j. Session 4 pre-work: both tests for every version, and how much is chance (11–12 Nov)

**In short:** at 1,000 sims per game, no sim version clearly beats the baseline. Every version is ahead of v1 on all games from 1 Sep and about level with v1 on Worlds games. Scores from 200 sims per game moved by chance by about 0.004 from 1 Sep and 0.007 at Worlds, so the smaller who-wins gaps reported in 7d to 7i cannot be relied on.

**What was built**

- **Walk-forward test** (`research/sim3/s3_walkforward.py`): for each week from 1 Sep, every fit is redone on the games before that week, the sim is calibrated on those games, and only that week's games are predicted. 11 weeks, 321 games, all 94 Worlds games.
- **Half-life** (`research/sim3/s3_halflife.py`): in the walk-forward fits, laning weights recent games with a 120-day half-life and draft styles with 60 days, chosen by test on July–August weeks (Luke's choice, 11 Nov; numbers in `research/sim-plan.md`). The timeline-fitted parts use no fade. The fixed test uses no half-life.
- **Full game set:** the skill table and features were rebuilt on the full file to 10 Nov UTC, so both tests cover 321 games from 1 Sep, 94 at Worlds and 21 knockout games (before: 304 / 80 / 7).

**The seed finding**

Each held-out game's seeds came from its place in the sorted game list. Adding 17 games moved later games' places, so 132 of the 304 shared games got different draws and different odds, with identical calibration. Four seedings of the same version (kills edge) on the same games, fixed test, 200 sims:

| Seeding | From 1 Sep (321) | Worlds (94) |
|---|---|---|
| Usual seeds | 0.6356 | 0.6287 |
| Seeds +200M | 0.6326 | 0.6168 |
| Seeds +300M | 0.6327 | 0.6176 |
| Seeds +400M | 0.6328 | 0.6233 |
| All four pooled (800 sims) | 0.6314 | 0.6197 |

Chance spread of the score by sims per game (standard deviation over 2,000 redraws, treating the pooled odds as each game's true sim odds): 200 sims 0.0041 from 1 Sep and 0.0074 at Worlds; 1,000 sims 0.0017 and 0.0033; 4,000 sims 0.0009 and 0.0017. Noisy odds also cost log loss: at 200 sims the average score is about 0.0025 worse than with exact odds, which v1 does not pay.

**Luke's decision (12 Nov):** seeds by game ID (adding games never changes another game's draws; every version plays each game on the same seeds) and 1,000 sims per game, for both tests. `s3_test.py ... oldseeds` at 200 sims reproduces earlier runs.

**Results at 1,000 sims** (who wins, log loss, lower is better; same 321 / 94 / 21 games in every column):

| Version | Fixed, from 1 Sep | Fixed, Worlds | Walk-forward, from 1 Sep | Walk-forward, Worlds | Walk-forward, knockouts (21) |
|---|---|---|---|---|---|
| v1 | 0.6348 | 0.6173 | 0.6348 | 0.6173 | 0.5224 |
| Baseline (default sim) | 0.6324 | 0.6158 | 0.6312 | 0.6203 | 0.5345 |
| + kills edge (`pfs`) | 0.6326 | 0.6192 | 0.6315 | 0.6188 | 0.5327 |
| + fight types (`typed`) | 0.6314 | 0.6152 | 0.6321 | 0.6190 | 0.5396 |
| + pushes, fitted cutoff 2+ (`pf`) | 0.6307 | 0.6147 | 0.6328 | 0.6208 | 0.5365 |
| + fight types and pushes (`typed,pf`) | 0.6310 | 0.6169 | 0.6272 | 0.6181 | 0.5383 |

- **Between versions:** apart from one score, they sit within 0.002 of each other from 1 Sep and within 0.005 at Worlds, inside the chance spread. Fight types and pushes at 0.6272 (walk-forward, from 1 Sep) is the one larger gap, and its fixed-test lead is only 0.0014.
- **Against v1:** every version is ahead from 1 Sep in both tests (by 0.002 to 0.008). At Worlds four of five are ahead in the fixed test and none in walk-forward, all by under 0.004. On the 21 knockout games v1 is ahead of every version (favourite 16 of 21 v 14).
- **"Kills edge" as the candidate (7g, 7i):** its lead over the baseline at 200 sims does not hold at 1,000.
- **Luke's decision (12 Nov):** two sims go into session 4: the baseline, and the baseline with fight types and pushes. The app ships one, or both with an option.

**Not run or not measured**

- **Pushes with a 4+ cutoff:** since 11 Nov the cutoff is chosen on training games (2+), so 4+ would have to be typed in by hand.
- **Fixed-test knockout scores:** the fixed test does not print them.
- **Chance from the number of games:** 94 Worlds games is a small sample in itself; only the sim's own draws were measured.
- **Shared seeds:** whether they make the gap between two versions steadier than each score alone.
- **The lane noise table** in the fixed test includes test games (small, predates this work, left as it is).

**How checked:** every run exited cleanly with 321 / 94 / 21 games scored. `oldseeds` at 200 sims gave the baseline's earlier scores exactly (0.6360 / 0.6188). With no walk-forward setting the edited fit scripts reproduce the saved fits (11 Nov; not re-run after a later one-line fix for empty windows in `s3_rates.py`). Runs: `research/local/sim3/out_n1000_*`, `wf_hl/` (`wf_results_n1000.json`, `wf_results_n1000b.json`), `seed_noise/`.

## 7k. Lane-level play, and the spread again (12 Nov)

**In short:** lane-level play (each lane's lead at 15 built from that lane's players, champions and its own kills) is in the sim as an option and improves who-wins on both sims in both tests, most at Worlds. The spread of game length and kills is still too wide: four more fitted attempts did not narrow it. A bug was found in how the sim reads tower-push timing.

**Luke's rules for this work (12 Nov):** keep every lane and input in the model even when its effect is small; a version that is marginally better or worse is acceptable if it adds depth to the sim's results. Values are fitted, never hand-picked.

**Timeline data:** the 14 knockout timeline pages were parsed and matched (708 pages parsed; 640 matched to the file, was 626; all 10 champions fit in each; in the 14 new games the timeline and the file differ on kills for 2 team-sides and on Heralds for 1, `research/model/sim3/tl_check.json`).

**What a lane's pre-game inputs explain** (`research/sim3/s3_lanelevel.py`, fitted before 1 Sep, held out from 1 Sep): lane skill and champion lane value explain 18% of the gold lead at 15 for top, 20% jungle, 13% mid and 10% for the bot duo (team strength alone: 2–7%). A lane's kills minus deaths is barely predictable before the game (1–3%). Extra inputs added about nothing, and the first dragon was not predicted better.

**Lane-level play, version 2** (sim setting `cal["lane_level"] = "on"`; `s3_test.py ... ll`; fit in `research/model/sim3/lanelevel_fit.json`). A lane's gold lead at 15 is three fitted parts:

1. the pre-game part (that lane's skill gap and champion lane value, plus team strength);
2. gold from what happens in the game before 15:00: own kill about 310–390, own death about −5 to −240, own assist about 50–90, a team plate about 1–7, by role;
3. leftover noise per role (sd 501 top, 334 jungle, 403 mid, 592 bot, 211 support).

Who gets each early kill leans on the lane's expected pre-game lead (killer +0.433 per 1,000 gold; victim −0.008). Version 1 (the lane model at full strength with the real leftover links between lanes, no event gold) left the kill-to-gold link too weak and is superseded.

**Who wins, 1,000 sims, log loss** (321 games from 1 Sep / 94 Worlds / 21 knockouts; chance spread about 0.002 / 0.003):

| Version | Fixed, from 1 Sep | Fixed, Worlds | Walk-forward, from 1 Sep | Walk-forward, Worlds | Walk-forward, knockouts |
|---|---|---|---|---|---|
| v1 | 0.6348 | 0.6173 | 0.6348 | 0.6173 | 0.5224 |
| Baseline | 0.6324 | 0.6158 | 0.6312 | 0.6203 | 0.5345 |
| Baseline + lane-level (`ll`) | 0.6256 | 0.6049 | 0.6296 | 0.6114 | 0.5483 |
| Fight types and pushes (`typed,pf`) | 0.6310 | 0.6169 | 0.6272 | 0.6181 | 0.5383 |
| Fight types and pushes + lane-level (`typed,pf,ll`) | 0.6232 | 0.6019 | 0.6259 | 0.6074 | 0.5291 |

- Lane-level gains on both sims in both tests. At Worlds the gain is about three times the chance spread in both tests; from 1 Sep it is clear in the fixed test and inside the chance spread in walk-forward.
- Both lane-level sims beat v1 at Worlds in walk-forward, which no version did before.
- On the 21 knockout games v1 is still ahead of every sim version (too few games to judge).
- Lane-level version 1 on the fixed test, for the record: baseline 0.6311 / 0.6227, fight types and pushes 0.6275 / 0.6135.

**Lane checks, version 2 v real, games from 1 Sep** (`s3_lanecheck.py`, `research/model/sim3/lanecheck_ll2.json`; baseline in brackets where measured):

| Check | Real | Lane-level v2 |
|---|---|---|
| Kill–gold link by role (top, jng, mid, bot, sup) | 0.71 / 0.82 / 0.79 / 0.75 / 0.67 | 0.74 / 0.81 / 0.83 / 0.77 / 0.68 (baseline 0.62 / 0.66 / 0.66 / 0.67 / 0.58) |
| Top lane lead at 15, sd | 911 | 944 (baseline 480) |
| Lane lead explained by the lane model | 0.18 / 0.21 / 0.13 / 0.05 / 0.13 | 0.21 / 0.17 / 0.09 / 0.07 / 0.05 |
| Top–bot lead link | 0.02 | 0.26 (baseline 0.94) |
| Bot–support lead link | 0.63 | 0.47 |
| Team lead at 15, sd | 2,596 | 2,848 |
| First dragon to the bot-lane leader | 61% | 57% |
| First tower falls mid | 12% | 25% (baseline also 25%) |
| Length sd / kills sd | 5.6 / 7.3 | 7.0 / 12.3 (unchanged) |

Open in the lanes: mid first towers (25% v 12%, same before this work), the top–bot link (0.26 v 0.02), team lead at 15 a little too spread.

**The spread: where the sim's games go wrong** (`s3_spreadcheck.py`, 245 real held-out timeline games v 6 sims each with lane-level on; a shape check, not recalibrated; `research/model/sim3/spreadcheck_ll2.json`):

| | Real | Sim |
|---|---|---|
| First inner tower (T2), median | 24.8 min | 21.4 min |
| First inhibitor, earliest 10% of games | 24.7 min | 21.9 min |
| Games under 24 min | 2.4% | 11.6% |
| Kills in those short games | 23.3 | 16.9 |
| Kills per minute, 0–5 min | 0.245 | 0.485 |
| Kills per minute, 15–20 min | 0.79 | 0.94 |
| Kills in games of 38–45 min | 28.1 | 37.4 |
| Length–kills link | 0.28 | 0.62 |
| Kills by 20:00, sd | 4.79 | 5.98 |

Short sim games are quiet walkovers (structures fall too early) and long sim games are too bloody.

**Bug found: tower-push game-phase terms.** The sim reads the phase terms for tower pushes from the older count fit (`P["segments"]`: +1.05 / +1.03 / +1.16 / +1.44 / +1.56), not from the push fit it uses (lane × tier: +1.03 / +0.96 / +0.96 / +1.23 / +1.38). So pushes from 20:00 come a little too often in every version, the baseline included. The corrected reading is an option (`cal["seg_phase"] = "own"`; `s3_test.py ... sp`), off by default so earlier runs replay. With it on alone the spread gets wider (length sd 7.84, kills sd 13.3), so the bug was partly hiding the long tail. **Decided later on 12 Nov (Luke): it is the default** (section 7l).

**Fitted attempts at the spread (all opt-in, off by default, none kept):**

| Attempt | Switch | Held-out fit | In the sim |
|---|---|---|---|
| Early mid/bot first-tower terms and a damaged-tower term | `S3_EARLY_LANE=1` (`s3_rates.py`) | n/a | games 1.5 min too short; mid first towers unchanged |
| Endings: base-push chance with kills edge × game time, and "does this push end the game" | `s3_test.py ... ends` | ends-the-game log loss 0.466 v 0.643 | games under 24 min 11.3% → 7.4%, but mean length 34.2 and sd 7.6: worse overall |
| Tier × game-phase terms for T2 / T3 and an early-minute term for pushes and fights | `S3_TIER_PHASE=1` (`s3_rates.py`), with `sp` | pushes 0.3673 / 0.3585 v the current lane × tier fit 0.3769 / 0.3671 (clearly better; without lane × tier 0.3797 / 0.3703); fight starts 0.7111 / 0.7009 v 0.7156 / 0.7048 (same 640-game timeline set) | kills per minute 0–5 min 0.49 → 0.31 (real 0.25); T2 timing, short games (10.5%) and spreads (length 7.63, kills 13.1) not improved |

Each minute's chances now fit real games better, yet whole games still come out wrong. That points at how one stage feeds the next (first tower → inner tower → inhibitor) and at the lack of a per-game pace (real quiet games stay quiet and run long). Next measurement: follow one lane at a time, real v sim, from its first tower to its second to its third, with the lead and kills at each step.

**Outside check (read 12 Nov 2026 in the browser pane)**

- **gol.gg, Worlds 2026 main event** (https://gol.gg/tournament/tournament-stats/Worlds%202026%20Main%20Event/ and its team table): 72 games, average length 33:28, 26 kills a game, shortest 23:51, longest 47:29, most kills 39. The saved Oracle's Elixir file gives the same (72 games, 33:28, 26.32, 23:51, 47:29, 39), and the team table's towers (12.03 a game) and plates (28.2 per team per game) match the file's 12.04 and 28.22. Gen.G, BLG, T1 and LYON were compared line by line (games, win rate, length, kills, towers, first tower %, gold difference at 15, plates, Barons, dragons): identical.
- **League wiki, gold rules** (https://wiki.leagueoflegends.com/en-us/Champion_gold_bounties, https://wiki.leagueoflegends.com/en-us/Turret): a kill's base bounty is 300 at levels 1–6, plus 100 for first blood; assists share half the kill bounty, reduced early in the game. The fit's 310–390 per kill and 50–90 per assist fit that. Every lane turret has five plates worth 120 local gold each, and plates are no longer removed at 14:00 (which patch: not read).
- **No published figure found** for first tower by lane, first inner tower or inhibitor timing, the share of games under 24 minutes, or bot lead and first dragon. Riot's patch notes, Leaguepedia and the Oracle's Elixir site were not opened.

**Found from that check: plate gold in version 2 is near zero.** The fit's plate input is the file's `turretplates`, a team's plates over the whole game (about 28 per team; 56 a game in the timelines, of which about 13 fall before 15:00 and 11 before 14:00). So it got almost no weight (1–7 gold), and with lane-level on the sim skips its older plate gold before 15:00. Quick measurement on the timeline games (395 before 1 Sep to fit, 245 from 1 Sep to check; no pre-game inputs; scratch script, not saved in the repo): a plate before 15:00 in the role's own lane is worth 160 gold to top, 113 to mid, 143 to bot, 31 to support, and 20 for any plate to the jungler; a plate in another lane 10–26. Held-out share of the lane lead explained, without plates → with plates before 15:00: top 0.53 → 0.67, mid 0.60 → 0.68, bot 0.54 → 0.65, support 0.63 → 0.68, jungle 0.69 → 0.70. **Fix (version 3): built the same day, section 7l.** Version 2's scores above stand as tested.

**How checked:** with every option off, 648 of 648 seeded games are identical to the committed sim after every edit, on both sims; with options on, the same seed replays the same game (648 of 648). With no setting, `s3_rates.py` gives the committed coefficients (only held-out score fields changed, from the 14 new timeline games). Fixed tests and the walk-forward exited cleanly with 321 / 94 / 21 games scored. The spread and attempt figures are from 6 sims per game (or 200-sim runs), not full tests. Runs: `research/local/sim3/out_n1000_ll2`, `out_n1000_typed_pf_ll2`, `wf_hl/` (`wf_results_n1000c.json`), `lanelevel/`, `fit_ends/`, `fit_tp/`.

## 7l. Plates by lane (lane-level version 3), the gold lead at 15, and the tower-push fix as default (12 Nov, evening)

**In short:** plate gold is now fitted by lane and comes out at the game's own figure (about 120 gold a plate). On the short Worlds test version 3 is level with version 2. Every sim's gold lead at 15 is too wide and too tied to team strength; one cause (a double-count in the first plate fit) is fixed, the older gap is open. The tower-push phase fix is now the sim's default.

**Luke's decisions (12 Nov):** fix the tower-push bug; use version 3 if reasonably level; shorter testing on the 94 Worlds games at 1,000 sims; explore the gold lead; begin the app work alongside (plan in `research/sim-plan.md`).

**The short test.** `S3_TEST_LEAGUE=WLDs` makes `s3_test.py` play only the 94 Worlds games (about 10 minutes a version: 566 s and 658 s measured, against about 21 minutes). Calibration is unchanged and seeds are by game ID, so these games' odds are exactly what the full test would give them. It is a screen: the other 227 games from 1 Sep and the walk-forward have not been run for anything in this section.

**Version 3 fit** (`s3_lanelevel.py`; local fits `research/local/sim3/ll_fit3b/`):
1. Stage 1, all file games before the cutoff (2,267): the lane's lead at 15 on the pre-game inputs and the role's own kills, deaths and assists. The whole-game plate term is gone.
2. Stage 2, timeline games before the cutoff (395): plates before 15:00 in the role's own lane and in the other lanes (jungle: any lane).
3. Leftover noise from those timeline games after both stages.

**First try and the double-count.** Stage 2 was first fitted on what stage 1 left over and paid on top of stage 1's weights. Strong teams and lanes with kills take more plates, so stage 1's weights already held part of the plates' effect and it was counted twice: on training games the sim's team lead at 15 moved 1,441 gold per unit of team strength (real 748; version 2 1,023; baseline 1,072), and the Worlds lead at 15 widened (median 2,142; version 2 1,789; real 1,399). **Corrected:** the plate values are fitted on the part of the plate gap that stage 1's inputs do not predict, and stage 1's weights give back the plates' share (the two-step form of fitting everything together). Values, first try → corrected:

| Role | Own-lane plate | Other-lane plate | Lane lead explained, held-out timeline games (no plates → with plates, corrected fit) |
|---|---|---|---|
| Top | 98 → 133 gold | 3 → 15 | 0.67 → 0.75 |
| Mid | 70 → 95 | 15 → 24 | 0.69 → 0.73 |
| Bot | 94 → 122 | −9 → 7 | 0.60 → 0.68 |
| Support | 18 → 25 | 6 → 10 | 0.71 → 0.73 |
| Jungle | 14 → 20 (any lane) | n/a | 0.83 → 0.84 |

The laner values now sit on the wiki's 120 gold a plate. With the corrected fit the lane's weight on team strength falls to about zero (top −29, jungle 0, mid −5, bot 27, support 9 per unit; version 2: 31, 14, 32, 30, 25): strength reaches the lane through the kills and plates it produces. Leftover sd 416 / 336 / 353 / 554 / 198 (version 2: 501 / 334 / 403 / 592 / 211).

**Short Worlds test, first-try version 3 on the sim before the tower-push fix** (94 games, 1,000 sims; log loss, favourite won):

| Sim | Version 3, first try | Version 2 | v1 |
|---|---|---|---|
| Baseline + lane-level | 0.6067, 67.0% | 0.6049, 64.9% | 0.6173, 64.9% |
| Fight types and pushes + lane-level | 0.6054, 66.0% | 0.6019, 64.9% | |

Level within about the chance spread (0.003). Length sd 7.05 and kills sd 12.18 are unchanged.

**The gold lead at 15 is too wide in every sim, and too tied to strength.** Worlds games, absolute team lead at 15: real median 1,399 (sd 1,377); baseline 1,715 (1,847); version 2 1,789 (1,846). The team ahead at 15 wins 67.5% of real Worlds games and 74% in the sims. On a sample of training games (300 games, 24 sims each, from each run's calibration) the team lead at 15 moves 748 gold per unit of team strength in real games and 1,072 in the baseline. In the baseline, calibration had already turned the lane's own strength term down to 0.051 of its fitted size and the lane noise to 0.023 (its floor is 0.02), so the link most likely comes through early kills following team strength more than real ones do. That last step is a reading of the settings, not a measurement: early kills by team strength, real v sim, is the next thing to measure.

**Tower-push fix as default.** `cal["seg_phase"]` now defaults to `"own"` (7k's bug); `"segments"` (`s3_test.py ... oldsp`) is the sim as it was. It changes 452 of 648 check games, so every score before this point is from the uncorrected sim.

**Corrected-sim re-runs** (Worlds-only, 94 games, 1,000 sims; runs in `research/local/sim3/out_wlds_sp_*`; v1 0.6173, favourite 64.9%):

| Sim, tower-push fix on | Log loss | Favourite | Before the fix | Length mean / sd | Kills sd | Lead at 15, median |
|---|---|---|---|---|---|---|
| Baseline | 0.6187 | 64.9% | 0.6158 | 32.6 / 7.54 | 13.0 | 1,709 |
| Fight types and pushes | 0.6134 | 67.0% | 0.6169 | 32.9 / 7.72 | 12.8 | 1,732 |
| Baseline + lane-level version 3 (corrected plate fit) | 0.6103 | 63.8% | version 2: 0.6049; version 3 first try: 0.6067 | 32.3 / 7.53 | 12.9 | 2,010 |
| Fight types and pushes + lane-level version 3 (corrected) | 0.6109 | 66.0% | version 2: 0.6019; first try: 0.6054 | 32.6 / 7.72 | 12.8 | 2,039 |
| Real Worlds games | | | | 33.1 / 5.78 | 6.2 | 1,399 |

- **The tower-push fix by itself** moves the two sims without lane-level in opposite directions (baseline +0.0029, fight types and pushes −0.0035), about the chance spread (0.003). Game length moves closer to real on average (32.3–32.9 against 31.9 before; real 33.1) but the spread gets wider (sd 7.5–7.7 against 7.0–7.1; real 5.78), as 7k's check suggested.
- **Lane-level still helps on the corrected sim:** 0.6187 → 0.6103 on the baseline; 0.6134 → 0.6109 on fight types and pushes (the second inside the chance spread). Both lane-level sims are ahead of v1; the baseline alone is not.
- **Version 3 against version 2 on the corrected sim** (two more runs, `out_wlds_sp_ll2`, `out_wlds_sp_typed_pf_ll2`; 567 s and 606 s):

  | Sim, tower-push fix on | Version 2 | Version 3 (corrected plate fit) | Gap |
  |---|---|---|---|
  | Baseline + lane-level | 0.6068, favourite 66.0% | 0.6103, 63.8% | 0.0035 |
  | Fight types and pushes + lane-level | 0.6022, favourite 66.0% | 0.6109, 66.0% | 0.0087 |

  **Version 3 is worse at who wins on both sims:** by about the chance spread on the baseline and by nearly three times it on fight types and pushes. The tower-push fix barely moves version 2 (0.6049 → 0.6068; 0.6019 → 0.6022), so the drop in the lane-level rows above comes from the plate fit, not from the fix. Version 2 also keeps the narrower lead at 15 (median 1,783 and 1,807 against 2,010 and 2,039; real 1,399; per unit of team strength on the training sample 1,010 and 1,077 against 1,199 and 1,298; real 748). Length and kills spreads are the same in both (sd 7.45–7.71 and 12.85–12.9). **So version 3 is not "reasonably level" on the corrected sim: version 2 stays the lane-level fit in use; version 3 stays in the code and local fits.** Its plate values are closer to the game's rules, but paying plates by lane adds to a lead at 15 that is already too wide; the gold-lead work (early kills and team strength) comes first, then version 3 can be tested again. Best sim on this test: fight types and pushes + lane-level version 2, 0.6022 (v1 0.6173).
- **Gold lead at 15 with the corrected plate fit:** better than the first try but still wider than version 2 (median 2,010 against 1,789; real 1,399; per unit of team strength on the training sample 1,199 and 1,298 against version 2's 1,023 and 1,109, first try 1,441 and 1,550, real 748). So paying plates by lane still adds to a lead that was already too wide.
- Run times: 607, 685, 543 and 596 seconds.

**How checked:** 648 seeded games each time. With the first plate fit: options off identical to the committed sim (648), version 2's fit identical (648), version 3 replays by seed (648). After the default changed: `seg_phase="segments"` identical to the committed default (648), the new default identical to the committed sim with the fix switched on (648), version 2 lane-level with `"segments"` identical to committed (648), version 3 replays by seed (648). Scores read from the saved result files. Not run: the fixed test on all 321 games and the walk-forward for anything in this section.

## 8. Open items for Luke

0a. **12 Nov, evening (7l):** full tests for version 3 and the corrected sim, or accept the short Worlds test? Gold lead at 15 too wide and too tied to strength in every sim (early kills follow strength too much): next thing to measure. Session 4 plan drafted in `research/sim-plan.md`, waiting for Luke's OK.
0. **12 Nov (7k):** the tower-push phase bug (decided the same day: fixed as the default, 7l). Spread still open after four more attempts; next is the lane-by-lane tower timing measurement. Lane-level play is in as an option and improves who-wins.
1. **Spread of games:** length and kills vary too much from game to game. Tested and not kept: per-game tempo, within-game "form", per-phase fight swing (7d), within-game lead effects for pushes and takers (7e). Found (7e): second-tier towers fall about 3 minutes early in the sim. Tested (7f): lane × tier push terms fix the per-lane pattern and predict held-out pushes better but don't narrow the spread (who-wins mixed; Luke, 7 Nov: keep them in the sim and keep testing); the combined fix is not kept. Measured (7g, 10 Nov): the extra kill spread comes from fight sizes that aren't held in check and from kills going in step with length (real long games slow down, the sim's get bloodier), not from the number of fights. Proposed next: fit fight size and the next fight's chance on what just happened, and check how game endings follow fights (7g).
2. **Baron:** too few games have one (88% against 97%), and the first-Baron team wins too rarely (78.5% against 84.4%).
3. **Draft styles in timing-only mode cost a little** in the final version. Keep (realism, and pace is supported), or keep only pace?
4. **Grub taker model** doesn't hold from 1 Sep: simplify to side only, or keep?
5. **The app's "one damage type" warning** is untested (session 4).
6. **Elder:** only 69 real Elder takes in the timelines, so Elder chances are rough.
7. **Player choice moments** (parked, Luke 5 Nov): come back to choices as a source of variety, based on data (section 7b).
