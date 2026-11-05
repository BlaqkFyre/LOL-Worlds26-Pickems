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

| 7 (part 2) | `s2_roles.py` (scratch folder, with `v1_games.csv`, `gfeat.csv`, the lolalytics files) | `model/sim2/roles_results.csv`, `roles_base.json` | Done 5 Nov |

Step 7, every draft input role by role (Luke, 4–5 Nov). 41 tests: 8 inputs × 5 roles (synergy × 6 teammate pairs), each added alone to v1. Pass = better than v1 on both July–August (fit Feb–Jun) and from 1 Sep (fit Feb–Aug). Change in log loss (negative = better):

| Passes | Jul–Aug | From 1 Sep | Worlds |
|---|---|---|---|
| Champion strength, ADC | −0.0027 | −0.0014 | −0.0041 |
| Comfort (games on champion), jungle | −0.0004 | −0.0022 | −0.0040 |
| Comfort (games on champion), mid | −0.0004 | −0.0001 | −0.0015 |

- 17 fail. 21 can't be checked on July–August (built from 16.15 onward, so the Feb–Jun fit has no values); of those, better on both from 1 Sep and Worlds: pro lane matchup support (−0.0006 / −0.0006), pro synergy ADC–support (−0.0009 / −0.0078), lolalytics synergy jungle–top (−0.0015 / −0.0098). Pro synergy jungle–mid is much worse (+0.0113 / +0.0219); pro lane top worse still (+0.0297 / +0.0597).
- **Reading:** with 41 tests, a few passes by chance are expected, so these are candidates, not results. The two that improve all three sets (ADC champion strength, jungle comfort) are the strongest. A combination chosen after seeing these numbers can only be tested fairly on new games (knockouts, when a newer file has them).
- Earlier combined tests hid these: champion strength over all roles was worse (step 2), but the ADC part alone is better on every set.

| 7b | `s2_comfort_worlds.py` | `model/sim2/comfort_worlds.csv` | Done 5 Nov |

Step 7b, comfort at Worlds checked directly (Luke, 5 Nov). 730 Worlds picks (73 games). For each pick, the player's earlier games on that champion (all leagues, earlier days only), grouped 0–2 / 3–9 / 10+; "won − expected" = win rate minus v1's expected win rate for that side (percentage points):

| Role | 0–2 earlier games | 3–9 | 10+ |
|---|---|---|---|
| Top | +7.4 (31 picks) | +3.6 (57) | −7.6 (58) |
| Jungle | +3.6 (16) | **−9.9** (60) | **+7.7** (70) |
| Mid | **−9.1** (22) | +3.1 (76) | −0.7 (48) |
| ADC | +10.5 (22) | −1.9 (54) | −1.8 (70) |
| Support | +11.5 (20) | −2.3 (74) | −1.2 (52) |
| All roles | +4.9 (111) | −1.3 (321) | −0.4 (298) |

- Overall, low-comfort picks did **not** lose more than expected at Worlds (0–2 games: +4.9 points over 111 picks).
- Jungle is the one role with the comfort pattern (10+ games +7.7 v 3–9 games −9.9); mid's few low-comfort picks lost more than expected (−9.1, 22 picks). Top, ADC and support show the opposite (low-comfort picks did better), possibly deliberate counter or meta picks (not tested).
- Sizes: cells are 16–76 picks in 15–60 games; a ±10-point gap on ~20 games is within chance (rough standard error about ±11 points). The five picks of a side share one result, so picks are not independent.
- Fits the step 7 model result: the Worlds gain is in jungle (and a little mid), not comfort in general.

| 7c | `s2_comfort_events.py` | `model/sim2/comfort_events.csv` | Done 5 Nov |

Step 7c, the comfort check on other events (Luke, 5 Nov). Same bands; won − expected (v1) in points, picks in brackets. Games: Worlds 73, MSI 71, EWC 232, First Stand 45, domestic playoffs 586 (1,007 big-event games together), domestic regular season 1,661.

| Jungle | 0–2 | 3–9 | 10+ |
|---|---|---|---|
| Worlds | +3.6 (16) | −9.9 (60) | +7.7 (70) |
| MSI | −15.7 (30) | +2.8 (72) | +6.8 (40) |
| EWC | −3.1 (138) | +1.1 (263) | +2.3 (63) |
| First Stand | −6.5 (39) | +4.7 (48) | +9.3 (3) |
| Domestic playoffs | −1.1 (490) | +0.4 (504) | +2.0 (178) |
| **Big events together** | **−2.3 (713)** | **+0.3 (947)** | **+3.8 (354)** |
| Domestic regular season | −0.5 (1,489) | +0.6 (1,415) | −0.4 (418) |

- **Jungle:** in every big-event group the 10+ band is above the 0–2 band (5 of 5); together −2.3 → +0.3 → +3.8. Flat in the domestic regular season. Rough standard errors (by game) for the jungle cells together: 2.1 / 1.8 / 2.8 points, so the 6.1-point gap from 0–2 to 10+ is about 1.7 standard errors: suggestive, not proven on its own; the consistency across events is the stronger evidence. (Several role and band splits were looked at, which also weakens any single gap.)
- **Mid:** big events together −1.3 → +0.6 → +1.4, a smaller gap; Worlds and MSI disagree (−9.1 v +13.7 at 0–2).
- **Top, ADC, support:** no comfort pattern at big events (top −1.0 / +0.8 / +0.1; ADC +1.2 / −1.3 / +1.5; support −1.3 / +1.3 / −1.1).
- **All roles:** big events −1.0 / +0.4 / +1.3; regular season +0.5 / −1.1 / +2.0.
- **Reading:** jungle comfort matters on the big stage (playoffs and internationals), not in the regular season and not for other roles. A fixed test for the knockouts: jungle comfort only, in big-event games.

| 8 | `s2_together.py` | `model/sim2/together_results.csv`, `together_bands.csv` | Done 5 Nov |

Step 8, player time together (Luke's "player and team synergy"). Earlier games two teammates played on the same team, all leagues, earlier days only; 2026 only (the file starts 1 Jan, so 2025 history isn't counted). Some minor-league rows have no player ID; those are skipped.

Model test (each alone on v1; change in log loss, negative = better):

| Input | Jul–Aug | From 1 Sep | Worlds | Passes |
|---|---|---|---|---|
| Pair jungle–mid | −0.0017 | −0.0018 | −0.0011 | yes (all three) |
| Pair jungle–ADC | −0.0002 | −0.0019 | −0.0007 | yes (all three) |
| Pair jungle–support | −0.0013 | −0.0016 | +0.0023 | yes |
| Pair mid–ADC | −0.0007 | −0.0004 | +0.0003 | yes |
| Team cohesion (mean of 10 pairs) | −0.0020 | −0.0002 | +0.0032 | yes |
| Newest link | −0.0022 | +0.0003 | +0.0051 | no |
| Other 6 pairs | | | | no |

- Every one of the 12 fitted weights is positive (more time together, better), which is more consistent than any draft input.
- Direct check, sides grouped by their newest link (won − v1 expected, points): domestic regular season 0–9 games −2.1 (1,060 sides, SE 1.5), 10–49 0.0 (1,632), 50+ +3.5 (630, SE 1.8); domestic playoffs −3.8 / −0.1 / +0.7; internationals +1.9 / −2.6 / +2.0; Worlds 0–9 only 8 sides. The clear pattern is in the regular season, where roster changes happen; by big events rosters are settled.
- Possible reasons (not tested): v1's team rating lags after a roster change (it rates the team name, not the current five), and this corrects for it; stable rosters may also mark better-run teams.
- Jungle pairs again lead, as with comfort.

| 9 | `s2_bans_pools.py` | `model/sim2/bans_pools_results.csv`, `bans_bands.csv` | Done 5 Nov: **neither kept** |

Step 9, denials (bans) and player pool depth. Player history = all leagues, 2026, earlier days only.
- **Denials:** each opposing player's 3 most-played champions; sides ban 1.6 of these on average. Model test (each alone on v1, change in log loss): bans on top-3 comfort +0.0015 / 0.0000 / +0.0001 (Jul–Aug / from 1 Sep / Worlds), weight ≈ 0; bans weighted by the opponents' games on them +0.0004 / −0.0014 / −0.0013 but with a **negative** weight; opponents pushed off comfort +0.0007 / −0.0005 / +0.0006. Direct check (won − v1 expected, points): big events 0 comfort bans +0.7 (318 sides), 1 −1.0 (701), 2+ +0.5 (995); regular season 0 +3.8 (477, SE 2.1), 1 −0.5, 2+ −0.7. Banning comfort picks doesn't help; sides that banned none did slightly better in the regular season (possibly stronger teams banning for the meta rather than the opponent: not tested).
- **Pool depth:** effective number of champions (exp of entropy) and champions with 3+ games, last 90 days. All fitted weights positive (deeper pool, a little better), but only top laners' effective pool passes (−0.0015 / −0.0002, Worlds +0.0021); ADC effective pool −0.0015 from 1 Sep and −0.0033 Worlds but fails Jul–Aug (+0.0003); team total 0.0000 from 1 Sep. Not kept.

| 10 | `s2_fearless_check.py`, `s2_pool.py`, `s2_pool_cards.py` | `model/sim2/pool_results.csv`, `pool_direct_g1.csv`, `pool_direct_g3plus.csv`, `pool_cards_worlds.csv` | Done 5 Nov |

Step 10, pool depth as part of player ratings (Luke, 5 Nov: "deep research").
- **Fearless everywhere:** in every 2026 league in the file, no team re-picks a champion inside a multi-game series (0 repeats in LPL 4,280 later-game picks, LCK 3,140, LEC 1,970, LCS 1,660, LCP 1,860, CBLOL 1,690, EWC 1,290…; a handful of repeats only in three minor leagues). Series = same day, same two teams.
- **Measures** (all leagues, earlier days only): effective pool (90 days); champions with 3+ games (180 days); meta pool = the player's champions with 2+ games that are in the role's current pro meta (top 10 by pro picks in the previous 30 days); free comfort = 3+-game champions not yet used in the series by either team. Typical player: 6–7 champions with 3+ games, effective pool ~10.
- **Pool v skill:** correlation with the player's pre-game role skill is low (top 0.07–0.11, jungle 0.06–0.14, mid 0.21–0.22, ADC 0.11–0.17, support 0.17–0.20): mostly new information, not a copy of skill.
- **Beyond v1** (change in log loss; Jul–Aug / from 1 Sep / Worlds): **jungle** passes on all three for every measure that counts champions: 3+ games −0.0021 / −0.0034 / −0.0038, free comfort −0.0015 / −0.0033 / −0.0047, meta pool −0.0007 / −0.0020 / −0.0054. Meta pool also passes for ADC, support and team total (smaller). Effective pool fails almost everywhere.
- **Fearless split** (from 1 Sep, game 1 = 109 games, games 2+ = 202): top and mid pool measures hurt in game 1 but mostly help in games 2+ (e.g. top free comfort +0.0054 v −0.0013), as Fearless would predict; jungle helps most in game 1 (−0.0084). Direct check, games 3+ of a series by team free comfort: lowest quarter −1.3 points v v1 expected (364 sides), middle half +0.3, highest quarter +0.9 (SE ~2.5): same direction, not proven. Game 1: flat.
- **Outside check (gol.gg, opened 5 Nov, https://gol.gg/players/player-stats/48/season-S16/split-ALL/tournament-ALL/):** Faker 2026 on gol.gg = 178 games, 23 champions; the file = 160 games, 21 champions, all 21 on gol.gg's list; gol.gg's extra 18 games and 2 champions (Mel, Yasuo) are not in the file (which events: not checked; may include games after the file's cut-off). Leaguepedia's 2026 champion statistics page for Faker does not exist.
- **Pool card** (S5 scale, mean of the 3+ games and meta pool z-scores; `pool_cards_worlds.csv`): highest of the 80 Worlds players Faker 89 (16 champions with 3+ games, all 10 current-meta mids), Caliste 89, Peyz 88; lowest 369 43 (he played Jan–Mar, then only 6 Worlds games in the last 180 days: a recent window marks stand-ins), Rookie 65. Knight 82, Kanavi 81, Canyon 78, Chovy 76.
- **Reading:** pool depth belongs on the player card as its own skill ("Pool"): it isn't a copy of skill, and Faker's depth is real where his laning numbers are not. For win odds, only jungle pool (closely related to jungle comfort) is a candidate. Its main job in the sim is mechanical: in Fearless series the draft AI must run out of comfort picks game by game, which uses pool depth directly without needing a fitted weight.

| 11 | `s2_curves.py` | `model/sim2/champion_curves.csv`, `champion_curves_recent.csv` | Done 5 Nov |
| 12 | `s2_comp.py` | `model/sim2/champion_styles.csv` | Done 5 Nov |

Step 11, champion power curves. Per champion-role: gold lead v the lane opponent at 10/15/20/25 minutes after the two players' laning skills (k = 20), scaling = 25-min value − 10-min value, and the win left after v1 in short (< 28 min, 558 games), medium (1,311) and long (> 34 min, 976) games.
- **Curves are lasting champion traits.** Before v from 1 Sep (77 champion-roles with 10+ games in both): gold lead at 10 0.72, 15 0.76, 20 0.72, 25 0.69; scaling 0.61 (jungle 0.88, top 0.68, mid 0.53, support 0.31, ADC 0.23).
- **Results by game length don't last** (short 0.05, long 0.10): noise.
- **Who-wins:** team scaling alone on v1: Jul–Aug +0.0012, from 1 Sep −0.0004, Worlds −0.0004: not kept. The more-scaling side does not win more of the long games (correlation with the win left after v1: −0.01 in long games).
- **gol.gg check:** LCK Rounds 3–4, 65 champions with 5+ games: gol.gg's GD@15 = the file's mean gold lead at 15 (correlation 1.000, all 65 within 50 gold; e.g. Orianna −218 both, Jayce +318 both).
- Use: the game sim's laning and mid-game gold (session 3), per champion; not pre-game odds.

Step 12, comp profile. Team stats per side as shares of both teams (plates, towers, first tower; dragons, grubs, Heralds, Barons; kills by 15; kills per minute of both teams), each **minus what v1's odds predict** (a first run without this mixed champion style with team strength and was replaced). Champion style = mean over its games (k = 20); a draft = its five summed.
- Styles last only weakly (before v from 1 Sep, 77 champion-roles): siege 0.29, objectives 0.29, pace 0.28, skirmish 0.07.
- A draft's style predicts a little of how the game goes (games from 1 Sep, styles from before; beyond team strength): siege 0.14, objectives 0.18, pace 0.16, skirmish 0.05.
- Who-wins (each alone on v1; Jul–Aug / from 1 Sep / Worlds): siege +0.0032 / −0.0002 / +0.0036; objectives −0.0028 / +0.0006 / +0.0039; skirmish +0.0002 / −0.0003 / +0.0041; pace +0.0009 / +0.0001 / +0.0012. **None kept.**
- Use: a mild flavour input for the game sim (which side leans to plates, objectives, a faster game), not pre-game odds.

| 13 | `s2_draftmeta.py` | `model/sim2/draftmeta_presence.csv`, `draftmeta_picked.csv` | Done 5 Nov: **kept for the draft AI** |

Step 12b, curves and styles v three outside labels (`lola_length.py` → `model/sim2/lola_length.csv`; `s2_style_sources.py`; 123 champion-roles with 20+ pro games):
- **lolalytics win rate by game length** (7 buckets in length order, edges not stated; 16.17 + 16.20 pooled; solo scaling = last 3 buckets − first 3): v pro gold-curve scaling, rank agreement **0.04** (top 0.18, jungle −0.02, mid −0.19, ADC 0.37, support −0.45). Solo-queue length curves don't describe pro gold curves.
- **Riot Data Dragon classes** (16.22.1, all 123 matched): gold-curve scaling by primary class: Assassin +376, Fighter +111, Marksman +42, Support +29, Mage −14, Tank −196. **Caveat found:** the "scaling" measure tracks where gold goes (tanks give it away as games go on), not late-game power. It is renamed "gold curve" for use, and the sim's late-game strength must not be read from it.
- **The app's `CHAMP_ARCH`** (engage 24, poke 16, scaling 16, skirmish 25, protect 12) v learned styles (list v the rest): poke → siege +0.0145 v −0.0005; engage → objectives +0.0052 v −0.0004; scaling → early tempo down (siege −0.0125 v +0.0033, pace −0.0097 v −0.0017); skirmish → objectives +0.0091 and gold curve +99 v −7. The hand-set labels broadly agree with what the data learned.

Step 13, draft meta model: which champions get picked or banned in a pro game. One row per (game, champion), 156+ champions; every feature from earlier days only; logistic, trained on games before 1 Sep. Score: share of the game's actual picks and bans that are in the model's top 20 for that game (log loss per champion-row in brackets).

| Model | From 1 Sep (311) | Worlds (73) |
|---|---|---|
| Season presence only | 42% (0.301) | 42% (0.297) |
| Last-30-days presence only | 48% (0.286) | 53% (0.274) |
| Pro presence (30 days + season + same patch) | 48% (0.284) | 53% (0.271) |
| + lolalytics pick/ban rate on the patch | 48% (0.284) | 53% (0.270) |
| + player pools (players with 3+ games on it) | 48% (0.280) | 53% (0.266) |
| **Full (+ Fearless lock: picked earlier in the series)** | **60% (0.236)** | **60% (0.239)** |

- Picked only (not bans): season 33% → full 50% from 1 Sep; 36% → 50% at Worlds.
- Weights per standard deviation (presence model): same-patch presence 0.83, last 30 days 0.65, **season 0.07**, player pools 0.31, lolalytics pick 0.05, Fearless lock −2.33. Recent and same-patch presence carry the meta; the season adds almost nothing (the current-meta principle, measured).
- lolalytics adds nearly nothing once pro presence is known; player pools help the picked model more (0.39) than presence.
- Use: the **draft AI's** sense of what is in the meta for this tournament, including Fearless locks in series. Pro presence rolls forward with each new patch and event.

| 14 | `s2_v2candidate.py` | `model/sim2/v2_candidate.json` (fixed 5 Nov 10:33 AEST) | Done 5 Nov |
| 15 | `s2_score_candidate.py` (with the session 1 scripts and `v1_offsets.py` re-run on the new file) | `model/sim2/knockout_score_2026-11-05.txt`, then `knockout_score_2026-11-05_qf2.txt`; `v1_games.csv` (now to 4 Nov 23:54 UTC) | Done 5 Nov: **running total, 7 games** |

Step 15, first knockout test (Luke's new Oracle's Elixir file, saved 5 Nov 10:40 AEST, 7 minutes after the candidate was fixed; the candidate file's SHA-256 is unchanged).
- New file: 9,861 games, data to 4 Nov 02:20 UTC; one new major series, the quarter-final **IG 3–1 TES** (3–4 Nov UTC, patch 16.20). All 4 games match Leaguepedia's Quarterfinals scoreboards (https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event/Scoreboards/Quarterfinals, read 5 Nov): sides, winners, lengths 31:02 / 47:09 / 29:29 / 30:58, kills 27–12 / 17–20 / 9–16 / 16–10, and all 40 champions.
- v1 re-run on the new file (scratch copy): the 2,845 earlier games have **identical** v1 odds (largest change 0); 4 new games.
- Score on the 4 knockout games: **v1 log loss 0.6692, Brier 0.2381, favourite 2 of 4; v2 candidate 0.6935, 0.2502, 2 of 4.** The candidate leaned toward TES because Tian had the deeper pool (12 v Wei's 9) and more games with his mid and ADC (99–101 v 69–86); IG won 3–1.
- Reading: one series is far too few to judge (either model could be ahead after the next one). The candidate stays fixed; the knockout total keeps running and is judged when all knockout games are in.

Step 15, second knockout update (Luke's newer file, 5 Nov 16:40 AEST: Gen.G 3–0 LYON, 3 games, 4 Nov UTC). Session 1 scripts and `v1_offsets.py` re-run (2,852 games; earlier games' v1 odds unchanged, largest change 0); candidate SHA-256 unchanged. Output `model/sim2/knockout_score_2026-11-05_qf2.txt`.
- All three GEN v LYON games: v1 gave Gen.G 85% and the candidate 84–85%; Gen.G won all three.
- **Running total, 7 knockout games: v1 log loss 0.4528, Brier 0.1459, favourite 5 of 7; v2 candidate 0.4686, 0.1533, 5 of 7.** The candidate is still slightly behind; still too few games to judge.

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
