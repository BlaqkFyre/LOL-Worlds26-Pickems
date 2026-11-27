# Base push learns the game state, with real base timing (plan, 27 Nov 2026 AEST; not built)

Steps 2 and 3 of `next-steps-plan.md` in one change. They come from the v54 play-test (`m15_series_playtest.json`) and the Nexus
measurements (`m16_nexus_push.json`, `m16_nexus_sim.json`). Each part below stops for Luke's OK.

## The problem (measured, not assumed)

- Games run long. Median 39.2 min, 28% at 45+ (real: 32.2 min, 2.8%).
- The time goes in the open-base phase. From the winner's first T3 tower to the Nexus takes a median 455 s in the sim; real games take 68 s.
- After a won fight with an inhibitor and both nexus towers down, the Nexus falls in 40% of sim pushes (real: 94%).
- The traced engine copy shows why. In 65% of those minutes the per-minute base push draws no push at all. Its inputs (`base_push_fight`
  in `js/sim-tables.js`, fitted by `research/sim3/s3_rates.py`) have no term for how close the Nexus is or how many defenders are dead.
- Base gaps: all four base pairs share one table (median 7 s). Real gaps by pair are 4 / 7.5 / 3 / 9 s:
  - T3 tower > inhibitor;
  - inhibitor > nexus tower;
  - nexus tower > nexus tower;
  - nexus tower > Nexus.

Luke's rule (21 Nov) stands: **keep the per-minute base push and all its inputs, add no block rule, the behaviour comes out of the fit.**

## Worked example: IG v T1, series 1 game 1 (seed 1716133153739033, v54)

**What v54 did:**
- 28:49–29:02: IG take the mid inhibitor and both nexus towers. Structures left to T1's Nexus = 0.
- 29:00–30:52: the Nexus is exposed, but each minute's base push is drawn without that fact.
- 30:53: IG win a fight. v54's draw, for that minute and the next, again uses only the lead, time, buffs, lanes and net kills.
- About 32:02: T1's nexus towers return (after 180 s). About 33:49: the inhibitor returns (after 300 s).
- IG win fights at 44:24 and 47:03 (5-0), break the base again at 49:04–49:24 and 57:36–58:05, and the game ends at 61:23.

**What the plan changes at 30:53:**

1. **The fitted push draw** (A below). The minute's row gains these inputs:
   - structures left = 0;
   - the most T1 players dead at once in the minute (from the fight; each death lasts its official timer);
   - the most IG players dead at once.

   The fitted coefficients decide how much more likely a push is. The real share (94% of 0-left won fights end in the Nexus) is the test, not a setting.
2. **Push size** is drawn from real pushes with 0 structures left, where the Nexus is usually the first structure.
3. **Nexus time** is drawn from the real "0 left" table. It is measured from the fight's last kill (real median 7 s), so about 31:00.
   It still needs a won fight, and it still has to come before T1's last respawn (the existing v51 check, real: never 60 s+).
4. **If no push is drawn**, or T1 are back first, the game goes on as now. The draw is a chance, not a rule.

**Not checked:** what v55 does with this seed. The draws move once the push terms change, so the game will play out differently from
29:00 on. The build step reports this game's v55 play-by-play next to v54's.

**Through each file:**

| File | What changes (traced with this game) |
|---|---|
| `research/memory/m17_base_push_state.py` (new, through `research/lib`) | Builds the same team-minute rows as `s3_rates.py` (reproducing `base_push_fight` exactly is the port check) and adds three inputs: structures left, enemies dead (most at once), own dead (most at once). T1's minute 30 row in a real game like this has left = 0. Fits a research copy (before 1 Sep) with held-out log loss, then an app copy (to 10 Nov). Also builds push sizes by structures left, base gaps by pair, and the Nexus from the last kill by structures left. Writes `research/model/memory/m17_base_push_state.json`, a run record, and the `SIM_TABLES.base` block of `js/sim-tables.js` |
| `js/sim-tables.js` | Gains the generated `SIM_TABLES.base` block (never hand-edited) |
| `js/sim-engine.js` (base push block, about lines 441–478) | New setting `base_push: "v2"`, on by default; `"off"` replays v54 exactly. In v2, for IG at 30:00: `left = nxTowers + (inhib down ? 0 : 1)` = 0. Enemies and own dead are counted from the engine's own `respawn` times over the minute. These feed the new coefficients. The push size comes from the 0-left table, each base step's gap from its pair's table, and the Nexus time from the 0-left table, keeping the won-fight and respawn checks |
| `index.html` | Cache bump to v55 on all 12 tags |
| `research/memory/m16_nexus_sim.js` (reused, no edit) | The same reading of the app sim with `M16_CAL = {base_push: "off"}` (v54) against the default (v55) |
| Docs | `research/memory/README.md`, `SESSION_NOTES.md`, the CLAUDE.md Code map line for the data sim |

## A. The fit (research only; stops for Luke's OK before B)

- **Rows:** team-minutes with an open lane, from the 640 gol.gg timelines. Nexus towers are labelled in their event detail.
- **Splits:**
  - research copy: fit before 1 Sep; held-out log loss from 1 Sep and on Worlds;
  - app copy: refit on all games to 10 Nov, as m9, m12 and m14 did.
- **New inputs**, each reported with held-out log loss against the current fit; all kept even if small (Luke, 12 Nov):
  1. **Structures left to the Nexus at the minute's start (0–3)**, as m16 counts it. Tried both as one slope and as 0/1/2 dummies; the held-out score picks.
  2. **Enemies dead and own dead** (the most at once during the minute). Death time = the official timer at the victim's level from XP by minute,
     the same machinery as `research/sim4/s4_deadpush.py`. That 14 Nov fit (research sim only, never put in the app, and I found no note saying
     why) already showed a gain on the base push: held-out log loss 0.4220 → 0.4160 from 1 Sep.
  3. **Own base under attack** (own base structures fell this minute or the last; step 2 of the plan).
  4. **An interaction, structures left × enemies dead**, only if the held-out score supports it (the exposed-Nexus case is rare: real 0.15
     won fights a game).
- **Shrinkage:** the same small ridge as the current fits (`logit_fit`, l2 = 1). About 2,600 training rows, so a few terms only.
- **Push size** by structures left, from real pushes (it replaces the inhibitor-down / not-down split).
- **Timing tables** (quantiles, as m14):
  - base gaps for each of the four pairs;
  - the Nexus after the fight's last kill by structures left at the fight's start (real medians 7 / 9 / 15 / 28 s).
- **Report:** a Markdown report with tables generated from the results.

## B. The app (after Luke OKs A's results)

- Engine as in the table above. The v54 replay fingerprint stays identical with `base_push: "off"` (72 drafts × 20 seeds, as m13).
- **Shape checks**, sim v55 against real (m16 reading, 72 Worlds drafts × 100 large seeds):
  - first T3 tower to the Nexus;
  - the structures-left table (share that take the Nexus, Nexus from the last kill);
  - base gaps by pair;
  - game length with 45+ and 50+ shares;
  - kills a game;
  - blue win;
  - Player of the Game by role.
- **Browser check:** a new tab, desktop and 375 px, console clean. Then the 100-series play-test (`m15_series_playtest.js`) re-run on v55.
- **Who-wins:** the 1,000-sim test needs these rules in the research sim. It stays step 4 of `next-steps-plan.md`, as for v51–v54 (not run).

## What this does not fix

- **Kills a game** (33 against 27) and **fights in the open-base phase** (sim 0.76 won 0-left fights a game, real 0.15). Faster ends should cut
  both, but that is to be measured, not assumed.
- **Lane-tower pushes:** the 14 Nov fit found only a small gain from dead players (held-out 0.3765 → 0.3749). Left for later.
- **Supports' Player of the Game share** (4.4% against real 10%): item 3 of the open list.
