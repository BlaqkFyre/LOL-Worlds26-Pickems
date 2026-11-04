# Sim session 2 — working files (champions, comps, synergies and counters)

Started 4 Nov 2026 (AEST). Plan and decisions: `research/sim-plan.md` (session 2 entry under Decided). Results tables go in `research/model/sim2/`; the report will be `research/sim2-report.md`. Live progress: the Sim Engine Progress artifact (https://claude.ai/artifact/J6sw8U1HziM7t8PAfKmqSL).

Data: the Oracle's Elixir file downloaded 2 Nov AEST (to 1 Nov 11:42 UTC). Only its games are used; no knockouts (Luke, 4 Nov).

| Step | Script | Makes | Status |
|---|---|---|---|
| 0 | `counts.py` | `model/sim2/counts.json`: sample sizes for champions, player–champion pairs, lane pairs, bot duos | Done 4 Nov |
| 1 | session 1 scripts, then `v1_offsets.py` | `model/sim2/v1_games.csv`: v1's pre-game log-odds (`z_v1`) and win chance for blue, per game | Done 4 Nov |

| 2 | `s2_champ.py` (from the scratch folder with `v1_games.csv`) | `model/sim2/champfit_results.json`, `champion_strength_now.csv` | Done 4 Nov: **not kept yet** (see below) |
| 2b | `compare_lck.py` with `gol_lck_r34.csv`, `lp_lck_r34.csv` (read 4 Nov) | `model/sim2/lck_r34_compare.csv` | Done 4 Nov |

Step 2 result (champion strength and comfort, measured beyond v1; tuning chose 90-day half-life, champion pull 100 games, comfort pull 30):

| Model | Jul–Aug (tuning) | From 1 Sep (311) | Worlds (73) |
|---|---|---|---|
| v1 | 0.6350 | **0.6461** | **0.6446** |
| + games on champion (count only) | 0.6357 | 0.6455 | 0.6452 |
| + new-pick count | 0.6361 | 0.6463 | 0.6451 |
| + champion strength | **0.6311** | 0.6495 | 0.6488 |
| + comfort (count, result, new picks) | 0.6375 | 0.6545 | 0.6518 |
| + champion strength + comfort | 0.6337 | 0.6558 | 0.6557 |

- Champion strength helps on July–August but makes the games from 1 Sep and Worlds worse, so it is **not kept as it stands**. Likely cause (not tested): the meta moved after August (Worlds is on its own patch, 16.20), so strength learned on earlier patches doesn't carry over. The plan's patch test is the next thing to try.
- Comfort from results on a champion is worse everywhere. Games on a champion alone gives a tiny gain from 1 Sep (0.0006) and a tiny loss at Worlds: too small to call.
- Note: v1's Jul–Aug number is partly in-sample (its player weights were fitted on Feb–Aug).

Step 2b, outside sources on LCK 2026 Rounds 3–4 (regular season; the file's split "Rounds 3-4" also holds 55 playoff games, flag `playoffs` = 1):
- **Leaguepedia matches the file exactly:** 98 games, all 91 champions' picks, bans and wins.
- **gol.gg has one more game (99):** 10 picks and bans and 5 wins differ (e.g. Jarvan IV 33 v 32 picks, Ezreal 30 v 29 bans). Which game it is: not checked.
- Win-rate order for the 39 champions with 10+ games: gol.gg v Leaguepedia 0.995, Leaguepedia v file 1.000 (rank correlation).
- File's learned season strength v LCK Rounds 3–4 win rate: 0.52 (rank correlation). Related, but strength covers the whole season and is pulled hard toward zero.
- **lolalytics:** its tier list shows only the top 20 champions to the browser (3 tries on 4 Nov), so it can't give a full list yet. Single champion pages do load (Orianna counters), so per-champion reads remain possible.

| 3a | `lola_pull.py` | `model/sim2/lola_tiers_all.csv`: lolalytics Emerald+ tier lists, 173 champions × 5 lanes × patches 16.11–16.20 | Done 4 Nov |
| 3b | `s2_patch.py` (scratch folder, with `v1_games.csv`) | `model/sim2/patchfit_results.json` | Done 4 Nov: **no gain** |
| 3c | `meta_by_patch.py` | `model/sim2/meta_by_patch.json` | Done 4 Nov |

Step 3a, lolalytics in full: the tier list shows only its top 20 champions on screen, but each page embeds all 173 in its data block (`qwik/json`). `lola_pull.py` reads that block. Checked against the page: Yone top 16.20 = 51.67% win, 8.81% pick, 15.44% ban, 238,834 games, the same in the browser and in the script. The site keeps patches 16.11 to 16.20 only (16.10 and earlier return "not found"), which covers 1,119 of the 2,845 pro games, all of Worlds and the summer. The site's patch numbers are the file's (16.xx).

Step 3b, patch-aware champion strength (features on the same scale; same-patch pull 5 games chosen on Jul–Aug):

| Model | From 1 Sep (311) | Worlds (73) |
|---|---|---|
| v1 | 0.6461 | 0.6446 |
| + champion strength, season (step 2) | 0.6516 | 0.6507 |
| + champion strength, same patch only | 0.6511 | 0.6511 |
| + lolalytics win rate on the game's patch | 0.6454 | 0.6443 |
| + lolalytics win rate and change from the patch before | 0.6450 | 0.6440 |

- Pro champion results from earlier games make the tests worse, by season or by patch.
- lolalytics win rate is the only champion input that doesn't hurt, but its gain is about 0.001 and its tuning check on Jul–Aug went the other way (0.651 with the change term), so it is **not adopted** on this evidence.
- A first run had a fault in my script: features on very different scales, so the fixed ridge flattened the small ones (solo-queue win rate). Fixed by putting every feature on the same scale before fitting; the table is the fixed run.

Step 3c, how the meta moves (the evidence for weighting the latest patches):
- Pro pick + ban presence at Worlds (16.20) against each earlier patch (rank agreement, 1.0 = same order): 16.01 0.60, 16.07 0.74, 16.10 0.78, 16.14 0.80, 16.15 0.86, 16.16 0.90, 16.17 0.91. Of Worlds' 30 most-present champions, 12 were also top 30 on 16.01 and 25 on 16.16 and 16.17.
- lolalytics win rates against 16.20 rise the same way: 16.11 0.84, 16.15 0.87, 16.17 0.91, 16.18 0.92, 16.19 0.92.
- Pros played no games on 16.12, 16.18 or 16.19; domestic leagues ended on 16.17 and Worlds is on 16.20.
- Solo-queue popularity is a poor guide to pro picks: Worlds presence v lolalytics 16.20 pick + ban 0.07 (16.17: 0.09). Pro-favoured champions tend to have lower solo win rates (Worlds presence v lolalytics win rate −0.45).
- Reading: for **who wins**, champion choice adds almost nothing measurable yet, likely because both sides mostly pick meta champions (not tested). For the **draft** (what gets picked and banned), the latest patches are clearly what matters: the draft AI should weight 16.20 and 16.15–16.17 far above early-year patches.

| 4a | `lola_counters.py` | `model/sim2/lola_counters.csv` (2.5 MB): lolalytics lane counters, 117 champion-roles (5+ pro games on 16.15–16.20) × 16.15, 16.16, 16.17, 16.20; bot also ADC v support and support v ADC; 43,667 matchups with 100+ games | Done 4 Nov (648 pages) |
| 4b | `s2_lanes.py` (scratch folder, with `v1_games.csv`, `gfeat.csv`) | `model/sim2/lanefit_results.json` | Done 4 Nov: **not kept** |
| 4c | `compare_metasrc.py` | `model/sim2/metasrc_v_lola.csv` | Done 4 Nov |

Step 4, lane matchups. lolalytics counter pages embed every matchup with 100+ games: `vsWr` (this champion's win rate v the opponent), `n`, `d1` = `vsWr` − `allWr` (checked: Orianna mid v Ezreal mid 16.20 = 59.86 − 54.83 = +5.03), `d2` (not used; its definition wasn't checked). Matchup edge = `d1` averaged both ways. Coverage: about 700 of the 769 pro games on 16.15+ per lane.

Lane result = pro gold lead at 15 v the lane opponent, after taking out the two players' laning skills (fitted before 1 Sep: 512–838 gold per skill SD by role). Link between lolalytics edge and that rest (correlation):

| Lane | All 16.15+ | From 1 Sep | Worlds | Gold per point, from 1 Sep |
|---|---|---|---|---|
| Top | −0.02 | −0.08 | 0.00 | −28 |
| Jungle | −0.01 | 0.09 | 0.21 | +35 |
| Mid | **0.12** | **0.17** | 0.07 | **+51** |
| ADC | −0.04 | −0.04 | 0.10 | −25 |
| Bot duo (ADC + support) | −0.09 | −0.05 | 0.00 | −56 |

- Only mid shows a steady link; jungle at Worlds (0.21) is 71 games and the other sets are near zero, so it isn't steady.
- Who-wins (trained on 458 games 16.15–Aug): lanes with one weight 0.6471 from 1 Sep / 0.6491 Worlds; four lanes 0.6515 / 0.6520; bot duo only 0.6488 / 0.6439; mid only 0.6457 / 0.6457. v1: 0.6461 / 0.6446. **Not kept.**
- METAsrc (the app's `CTR_RAW`, 460 pairs, 29 champions) v lolalytics 16.20: 440 pairs found; rank agreement of win rates 0.80; METAsrc's "wins" pairs are above 50% on lolalytics in 189 of 219, its "loses" pairs below 50% in 162 of 221. The two solo-queue sources agree with each other; it is the step from solo queue to pro lanes that loses the signal.
- Next for lanes: pro champion-pair lane records from the file (thin: 368 pairs with 10+ games all year), not yet tested.

| 5 | `s2_pro.py` (scratch folder, with `v1_games.csv`, `gfeat.csv`) | `model/sim2/profit_results.json` | Done 4 Nov |

Step 5, synergy and pro-only lanes (Luke, 4 Nov: "pro only lane tests, in relevant patches; synergy first").
- **lolalytics synergy:** each build page has a Synergy strip (most common, best and worst teammates per lane: win rate together, delta 1 = win rate together − both champions' own win rates averaged, games). It is not in the page's data block and no separate request was seen; it only draws once on screen. Reading it by script worked once (Vi jungle 16.20: 155 teammate rows), then returned nothing for 6 pages in a row while the browser pane was hidden. Stopped after more than 5 tries (CLAUDE.md rule 15). Not usable in the background; possible with the browser pane visible (about 90 pages).
- **Pro-only, two windows:** "meta" = only games on 16.15, 16.16, 16.17, 16.20; "season" = all games, 30-day half-life. Every value from earlier days only.

Pro matchup record v the later lane result (gold at 15 after skills), games from 1 Sep, meta window (pull 5 games):

| Lane | Pro records | lolalytics (step 4) |
|---|---|---|
| Top | **0.30** (250) | −0.08 |
| Jungle | **0.27** (260) | 0.09 |
| Mid | 0.11 (259) | 0.17 |
| Bot duo | 0.05 (165) | −0.05 |

- Pro records beat solo queue clearly in top and jungle, and the season window gives about the same (0.29, 0.27). Part of this may be the same players meeting again (their lane gap beyond the skill estimate): not tested.
- Who-wins (meta window, trained on 458 games): synergy 0.6476 from 1 Sep / 0.6464 Worlds; lanes 0.6596 / 0.6592 (the fitted weight is negative); both 0.6611 / 0.6607. Season window: synergy 0.6471, lanes 0.6482. v1 0.6461 / 0.6446. **Neither kept for who-wins.**
- Use: pro lane records are the input for the **game sim's laning phase** (session 3), not for pre-game odds.

| 6 | browser read (below), then `s2_syn.py` (scratch folder) | `sim2/lola_synergy.txt`, `model/sim2/lola_synergy.csv`, `synfit_results.json` | Done 4 Nov: **not kept yet** |

Step 6, lolalytics synergy (Luke, 4 Nov: "run it, pane visible").
- Read in the browser pane: 88 build pages (the 20 jungle and 24 ADC champions pros played 5+ times on 16.15+, each on 16.17 and 16.20). The synergy table only loads after a **real** mouse click on its strip (a script click doesn't load it), so each page was: open, scroll to the strip, one real click on "Common Teammates", then read the Common, Good and Bad views. 13,798 rows; kept 5,172 pro-relevant pairs (jungle with top, mid, ADC, support; ADC with support; teammate in the pro pool). Saved as a file download (75,044 bytes, Luke's OK) and moved here as `lola_synergy.txt`.
- Delta 1 (lolalytics' own definition, read on the page): win rate together − (current champion's win rate + paired champion's win rate) / 2.
- Coverage: 324 pro games on 16.17 and 16.20; 4.7 of 5 pairs found per side on average.
- Link with the pro win left after v1 (correlation): 16.17 0.06 (251 games), Worlds 0.05 (73). Weak but the same sign in both.
- Fitted weight: only 46 training games (16.17 before 1 Sep), weight came out negative: not usable.
- Used as lolalytics gives it (delta 1 points = change in win chance, no fitting): from 1 Sep 0.6478 v v1 0.6485 (278 games), Worlds 0.6497 v 0.6446, both patches 0.6435 v 0.6420. **Not kept.** At half strength it scored 0.6461 / 0.6447 / 0.6408, better than v1, but that strength was picked after seeing these games, so it is not a fair test; it can be tested fairly on the knockout games when a newer file has them.
- metabot duos (the app's `DUOS`, 29 pairs) v lolalytics ADC–support delta 1 on 16.20: 27 pairs found, rank agreement 0.54, same sign in 17.

Step 1 detail: `research/sim1/` scripts re-run on a scratch copy in order (`prep.py`, `playerprep.py` n0 = 6, `teamfit.py`, `leaguefit.py`; `playerfit.py` not needed). They reproduce the saved session 1 results exactly (validation 0.6441, from 1 Sep 0.6489, Worlds 0.6491, rolling 0.6451; league-adjusted 0.6367 / 0.6461 / 0.6446; same league shifts and 16 team ratings). `v1_offsets.py` runs from that folder (it uses `exptest.py`): v1 odds for 2,668 of 2,845 games (the first games of the year have no earlier games to rate teams from), 0.6461 from 1 Sep and 0.6446 on Worlds, the same as session 1.

## Sample sizes (step 0, major leagues + internationals, 2,845 games)
- 156 champions, 281 champion–role pairs: 146 with 10+ games, 113 with 30+, 74 with 100+.
- Player–champion pairs: 6,598 (3,460 with 3+ games, 2,213 with 5+, 810 with 10+); 28,682 across all leagues.
- Lane pairings (same role, opposite sides): 1,478 (760 with 3+, 568 with 5+, 368 with 10+). Bot duos (ADC + support on one side): 418, 106 with 10+.
- So most matchups and pairs are thin in pro play: solo-queue values as starting points are needed, and pro data can only move them a little.

## Patch names
The file names patches 16.xx (as lolalytics does); the app uses 26.xx. Read `patch` as text: pandas reads "16.10" as 16.1 and "16.20" as 16.2. The file has 73 major games on 16.20, the same count as its Worlds games, so 16.20 looks like the app's 26.20; not confirmed game by game.

## Outside sources (`sources.csv`)
Three per part (Luke, 4 Nov). Opened on 4 Nov and readable: gol.gg champion table (https://gol.gg/champion/list/season-S16/split-ALL/tournament-LCK%202026%20Rounds%203-4/), Leaguepedia champion statistics (https://lol.fandom.com/wiki/LCK/2026_Season/Rounds_3-4/Champion_Statistics), lolalytics counters (https://lolalytics.com/lol/orianna/counters/). First cross-check: Orianna in LCK Rounds 3–4 is 20 games, 8–12, KDA 4.3 on both gol.gg and Leaguepedia; bans 61 (gol.gg) v 60 (Leaguepedia), not explained yet. The rest are listed as not opened yet.
