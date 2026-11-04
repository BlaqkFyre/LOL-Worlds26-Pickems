# Sim session 2 report, part 1: champions, lanes, synergy and the meta

Written 4 Nov 2026 (AEST). Covers the work done on 4 Nov; session 2 is not finished (power curves, comp profile and the draft meta model are still to do). Working files, every number's source and how to re-run: `research/sim2/README.md`. Plan and decisions: `research/sim-plan.md` (session 2 entry). Live tracker: https://claude.ai/artifact/J6sw8U1HziM7t8PAfKmqSL

- Data: the Oracle's Elixir file downloaded 2 Nov AEST (to 1 Nov 11:42 UTC), 2,845 major-league and international games. No knockout games (Luke, 4 Nov: work with the file as it is).
- Outside sources, opened directly on 4 Nov: gol.gg, Leaguepedia, lolalytics (Emerald+ solo queue), and the app's METAsrc and metabot tables.
- App change: none (v38).

---

## 1. Summary

- **Nothing tested so far improves who wins beyond v1.** Champion strength, comfort, patch strength, solo-queue win rate, lane matchups (solo queue and pro) and synergy (solo queue and pro) all fail to beat v1 on held-out games (from 1 Sep: v1 0.6461).
- **The meta follows the latest patches.** Worlds pick and ban presence matches 16.17 at 0.91 and 16.01 at 0.60 (rank agreement); 25 of Worlds' top 30 champions were top 30 on 16.16–16.17, 12 on 16.01. This is the evidence for Luke's current-meta principle, and it matters for the draft (what gets picked and banned).
- **Pro lane records predict the lane.** A champion pair's earlier lane result on 16.15–16.20 predicts the later pro gold lead at 15 (after player skill): top 0.30, jungle 0.27, mid 0.11. Solo-queue counters don't (top −0.08, jungle 0.09). This goes to the game sim's laning phase (session 3), not to pre-game odds.
- **Sources agree with each other.** Leaguepedia matches the file exactly (LCK Rounds 3–4); gol.gg differs by one game. METAsrc and lolalytics counters agree at 0.80; metabot and lolalytics duos at 0.54.
- **Likely reason champion choice adds so little to who wins** (not tested): both teams mostly pick meta champions, so drafts separate them very little; the team and player ratings already carry most of what's predictable.

---

## 2. Scorecard (who wins, log loss; lower is better)

Every row is on games not used to fit it. v1 = session 1's model (teams + league-adjusted players).

| Model | From 1 Sep (311) | Worlds (73) | Kept? |
|---|---|---|---|
| v1 | **0.6461** | **0.6446** | baseline |
| + games on champion (comfort count) | 0.6455 | 0.6452 | no (too small, mixed) |
| + champion strength, season | 0.6495 | 0.6488 | no |
| + comfort (games, results, new picks) | 0.6545 | 0.6518 | no |
| + champion strength, same patch | 0.6511 | 0.6511 | no |
| + lolalytics win rate on the game's patch | 0.6454 | 0.6443 | no (gain ~0.001, tuning check went the other way) |
| + lolalytics win rate and change from last patch | 0.6450 | 0.6440 | no (same) |
| + lane matchups, lolalytics | 0.6471 | 0.6491 | no |
| + pro synergy (16.15–16.20) | 0.6476 | 0.6464 | no |
| + pro lane matchups (16.15–16.20) | 0.6596 | 0.6592 | no |
| + lolalytics synergy, as given (278 games; v1 on these 0.6485) | 0.6478 | 0.6497 | no |

Notes:
- Step 2's champion strength helped on the July–August tuning games (0.6311 v 0.6350) but not after; the meta moved.
- A first patch-test run had a fault in my script (features on different scales, so the ridge flattened the small ones). Fixed and re-run; the table shows the fixed run.
- lolalytics synergy at half strength beat v1 (0.6461 from 1 Sep, 0.6447 Worlds) but that strength was chosen after seeing these games: not a fair result. The knockout games (when a newer file has them) are a clean test.

---

## 3. The meta by patch

Rank agreement of each champion's pro pick + ban presence with Worlds (16.20, 73 games), and of lolalytics win rates with 16.20:

| Patch | Pro games | Pro presence v Worlds | Top-30 overlap | lolalytics win rate v 16.20 |
|---|---|---|---|---|
| 16.01 | 184 | 0.60 | 12 | — |
| 16.05 | 45 | 0.69 | 15 | — |
| 16.10 | 252 | 0.78 | 18 | — |
| 16.13 | 122 | 0.79 | 18 | 0.85 |
| 16.15 | 230 | 0.86 | 21 | 0.87 |
| 16.16 | 215 | 0.90 | 25 | 0.88 |
| 16.17 | 251 | 0.91 | 25 | 0.91 |
| 16.19 | — | — | — | 0.92 |

- Pros played no games on 16.12, 16.18 or 16.19; domestic leagues ended on 16.17 and Worlds is on 16.20. The file and lolalytics name patches 16.xx; the app's 26.20 is 16.20.
- Solo-queue popularity is a poor guide to pro picks: Worlds presence v lolalytics pick + ban 0.07. Pro-favoured champions tend to have lower solo-queue win rates (−0.45).
- Use: the draft AI and each tournament's meta should weight 16.20 and 16.15–16.17 far above early-year patches (Luke's current-meta principle, `research/sim-plan.md`).

---

## 4. Lanes

Link between each input and the later pro lane result (gold at 15 after the two players' laning skills; games from 1 Sep):

| Lane | Pro records, 16.15–16.20 | lolalytics counters |
|---|---|---|
| Top | **0.30** | −0.08 |
| Jungle | **0.27** | 0.09 |
| Mid | 0.11 | **0.17** (about 50 gold per point) |
| Bot duo (ADC + support) | 0.05 | −0.05 |

- Part of the pro link may be the same players meeting again (their lane gap beyond the skill estimate): not tested.
- Neither input improves who wins; the fitted weight for pro lanes is negative (not explained yet).

---

## 5. Sources compared

| Comparison | Result |
|---|---|
| gol.gg v Leaguepedia v file, LCK 2026 Rounds 3–4 (regular season) | Leaguepedia = file exactly (98 games, 91 champions); gol.gg has 99 games (10 picks/bans, 5 wins differ; which game: not checked). Win-rate order 0.995–1.000 |
| File's learned champion strength v LCK Rounds 3–4 win rates | 0.52 |
| METAsrc (app, 440 pairs) v lolalytics counters, 16.20 | 0.80; direction agrees in 189 of 219 "wins" and 162 of 221 "loses" pairs |
| metabot duos (app, 27 pairs) v lolalytics ADC–support synergy, 16.20 | 0.54; same sign in 17 |
| lolalytics synergy v pro win left after v1 | 0.05–0.06 |

How the lolalytics data was read (for repeating it): tier lists and counters are in each page's embedded data block (all champions, not just the 20 on screen; script `lola_pull.py`, `lola_counters.py`); the site keeps patches 16.11–16.20 only. Synergy loads only after a real click on its strip, so it was read page by page in the browser pane (88 pages) and saved by file download.

---

## 6. What feeds the next steps

- **Session 2, still to do:** power curves (gold lead at 10/15/20/25 and wins by game length per champion), comp profile (siege / objectives / skirmish styles), and a **draft meta model** (which champions get picked and banned on a patch, tested on Worlds drafts it hasn't seen). Who-wins v2 is not built: no part has earned a place yet.
- **Session 3 (game sim):** pro lane records (16.15–16.20) for the laning phase; the meta tables for which champions appear.
- **Session 4 (app):** draft AI weighted to the current patch; who-wins stays v1 unless a later part beats it.
- **When a newer file has the knockouts:** re-test lolalytics synergy at half strength, the experience test (session 1), and everything above on the new games.

---

## 7. Open items for Luke

1. ~~Whether to keep testing who-wins inputs or accept v1.~~ **Decided (Luke, 4 Nov): keep testing, each role tested on its own** (top, jungle, mid, ADC, support; bot also as a duo).
2. Pro lane records' negative weight in who-wins: worth a look later, or leave.
3. lolalytics synergy at half strength: re-test on knockout games when available.
