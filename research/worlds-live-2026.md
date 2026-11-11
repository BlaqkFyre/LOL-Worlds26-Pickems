# Real Worlds 2026 Swiss games — data and how the app uses them

Updated 10 Nov 2026 (AEST): **72 games**: semi-finals (GEN 3–0 IG, BLG 3–1 T1), quarter-finals 1–4 (IG 3–1 TES, GEN 3–0 LYON, BLG 3–0 DK, T1 3–1 KC; sections below) and the whole Swiss stage (51 games): rounds 1–3 (16 Bo1s on 23–24 Oct; on 25 Oct HLE vs IG, TES vs G2, DK 2-0 MKOI, GEN 2-1 LYON; on 26 Oct T1 vs CFO, BLG vs KC, LOS 2-0 TSW, TL 2-0 AL), round 4 (28 Oct: T1 2-0 MKOI, IG 2-1 LYON; 29 Oct: KC 2-0 CFO, TES 2-1 BLG; 30 Oct: LOS 2-1 TL, HLE 2-0 G2) and round 5 (31 Oct: KC 2-0 MKOI, LYON 2-1 LOS, BLG 2-0 HLE). Dates are US event days; the Oracle's Elixir file uses UTC. Data: `js/worlds-live.js`.

## Quarter-final 4 and semi-finals: T1 3–1 KC, GEN 3–0 IG, BLG 3–1 T1 (added 10 Nov, v45)
- **Source:** the full Oracle's Elixir download was too slow, so Luke saved the file's rows for 6–9 Nov UTC as `research/SF26Results.xlsx` (deleted 11 Nov once the full file confirmed it; copied from the same data: the file's 165 columns, header row and game IDs). Checked in code: header identical to the main file's, 240 rows, no duplicates, no game already in the main file; each of the 11 Worlds games has 12 rows (10 players with every role once, 2 team rows) and the players' kills equal the team totals. Excel had turned the patch `16.20` into `16.2` (set back to 16.20) and dropped trailing zeros (values unchanged). Its 9 LCK academy (`LAS`) games are left out.
- **Not checked against Leaguepedia** (Luke, 10 Nov: the copy is accurate for now).
- **Confirmed against the full Oracle's Elixir file (11 Nov AEST; 9,904 games, data to 10 Nov 09:49 UTC):** all 240 spreadsheet rows found by game ID and participant; the 132 Worlds rows match on every one of their 21,516 fields (0 differences; the file's patch is 16.20). `build_from_oe.py` on a scratch copy with the full file: 72/72 Worlds games OK; `js/h2h.js` and `h2h_2026.json` identical to the repo's; `worlds-live.js` games identical. v1 re-run: the 2,866 earlier games' odds unchanged; knockout score unchanged (v1 0.5224, candidate 0.5104). The full file also adds 3 LCP games (Saigon Warriors v Team Gromp, 10 Nov, patch 16.22) and minor-league games; the pro matchups table would take those 3 LCP games (790 → 793), left as it is until Luke decides.
- Games (US dates; UTC 6 Nov 22:13 to 9 Nov 00:56): QF4 T1 v KC — T1 (35:39, 23–7), T1 (29:42), KC (36:44), T1 (35:15); SF1 GEN v IG — GEN 33:38, 29:16, 40:08 (IG blue in game 3); SF2 BLG v T1 — BLG 30:25, T1 32:15, BLG 36:58, BLG 37:47. Final (14 Nov US): Gen.G v Bilibili Gaming.
- Rows built with `research/build/ko_rows.py` (`r:"QF"` for QF4, `r:"SF"` for the semi-finals; the round label isn't shown anywhere in the app). The script was first checked by rebuilding the 10 existing quarter-final rows from the main file: 10 of 10 identical to the app's rows. 72 games now.
- `build_from_oe.py` and `build_pro_matchups.py` on a scratch copy of the main file plus these 11 games (patch 16.20): 72/72 Worlds games OK; `js/h2h.js` to 9 Nov: BLG v T1 4–2 → 7–3, GEN v IG 1–0 → 4–0, KC v T1 2–4 → 3–7 (the only changes); `js/pro-matchups.js` 779 → 790 games. Its `worlds-live.js` output differed only in the play-in team list order, so that file was edited directly.

## Out-of-sample check, quarter-final 4 and semi-finals (the app at v44, before this update; 3,000 simulated games per draft with the real picks)
| Game | App's odds for the winner | Result |
|---|---|---|
| T1 vs KC G1 (T1 blue) | T1 76% | T1 won |
| KC vs T1 G2 (KC blue) | T1 66% | T1 won |
| KC vs T1 G3 (KC blue) | KC 36% | KC won |
| KC vs T1 G4 (KC blue) | T1 67% | T1 won |
| GEN vs IG G1 (GEN blue) | GEN 75% | GEN won |
| GEN vs IG G2 (GEN blue) | GEN 93% | GEN won |
| IG vs GEN G3 (IG blue) | GEN 87% | GEN won |
| BLG vs T1 G1 (BLG blue) | BLG 55% | BLG won |
| T1 vs BLG G2 (T1 blue) | T1 32% | T1 won |
| BLG vs T1 G3 (BLG blue) | BLG 47% | BLG won |
| T1 vs BLG G4 (T1 blue) | BLG 73% | BLG won |

- Favourite won 8 of 11; log loss 0.494, Brier 0.164 (QF4 0.526; SF1 0.167; SF2 0.706). Two above the ~80% ceiling (GEN 93%, 87%).
- Running total across all real Worlds main-event games scored before their data was added: 41 of 61 + 8 of 11 = **49 of 72 (68%)**.
- The research models on all 21 knockout games (no drafts): v1 0.5224, the fixed v2 candidate 0.5104; favourite 16 v 17 of 21 (`research/sim2/README.md` step 15).

## Quarter-final 3: BLG 3–0 DK (added 6 Nov, v43)
- **Newer Oracle's Elixir file** (Luke, 6 Nov AEST): 9,867 games, data to 6 Nov 00:00 UTC; one new Worlds series, BLG 3–0 DK (5 Nov US; 5–6 Nov UTC; patch 16.20).
- **Checked against Leaguepedia** (Quarterfinals scoreboards, https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event/Scoreboards/Quarterfinals, and Picks and Bans, https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event/Picks_and_Bans, both read 6 Nov): BLG blue in game 1, DK blue in games 2–3, BLG won all three; lengths 33:21 / 32:11 / 32:36, kills 24–9 / 10–13 / 9–25; all 30 champions, every player's K/D/A and CS, all 30 bans in order, first pick (DK in all three) and towers, inhibitors, Barons, dragons, Heralds and grubs match.
- Rows built from the file (`r:"QF"`, `d:"2026-11-05"`). 61 games now.
- `build_from_oe.py` on a scratch copy: 61/61 Worlds games OK; `js/h2h.js` rebuilt to 6 Nov: BLG v DK 1–2 → 4–2 (the only change). Its `worlds-live.js` output differed only in the play-in team list order, so that file was edited directly. `build_pro_matchups.py` (scratch copy) refreshed `js/pro-matchups.js`: 776 → 779 games, to 6 Nov.

## Out-of-sample check, quarter-final 3 (the app at v42, before this update; 3,000 simulated games per draft with the real picks)
| Game | App's odds for the winner | Result |
|---|---|---|
| BLG vs DK G1 (BLG blue) | BLG 76% | BLG won |
| DK vs BLG G2 (DK blue) | BLG 69% | BLG won |
| DK vs BLG G3 (DK blue) | BLG 52% | BLG won |

- Favourite won 3 of 3; log loss 0.433, Brier 0.128. None above the ~80% ceiling.
- Running total across all real Worlds main-event games scored before their data was added: 38 of 58 + 3 of 3 = **41 of 61 (67%)**.
- The research models on all 10 knockout games so far (no drafts): v1 0.526, the fixed v2 candidate 0.516 (`research/sim2/README.md` step 15).

## Quarter-final 2: GEN 3–0 LYON (added 5 Nov, v40)
- **Newer Oracle's Elixir file** (Luke, 5 Nov 16:40 AEST): 9,864 games, data to 4 Nov 23:54 UTC; one new Worlds series, Gen.G 3–0 LYON (4 Nov US and UTC; patch 16.20).
- **Checked against Leaguepedia** (https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event/Scoreboards/Quarterfinals, read 5 Nov): Gen.G blue and winning in all three, lengths 32:13 / 26:32 / 33:29, kills 19–8 / 22–6 / 16–10, all 30 champions and all 30 bans match.
- Rows built from the file (`r:"QF"`, `d:"2026-11-04"`); first pick LYON in games 1–2, Gen.G in game 3. 58 games now.
- `build_from_oe.py` on a scratch copy: 58/58 Worlds games OK; `js/h2h.js` rebuilt to 4 Nov: GEN v LYON 5–1 → 8–1 (the only change). Its `worlds-live.js` output differed only in the play-in team list order (same content), so that file was edited directly instead.

## Out-of-sample check, quarter-final 2 (the app at v39, before this update; 3,000 simulated games per draft with the real picks)
| Game | App's odds for the winner | Result |
|---|---|---|
| GEN vs LYON G1 (GEN blue) | GEN 85% | GEN won |
| GEN vs LYON G2 (GEN blue) | GEN 96% | GEN won |
| GEN vs LYON G3 (GEN blue) | GEN 79% | GEN won |

- Favourite won 3 of 3; log loss 0.147, Brier 0.023. Two of the three are above the ~80% ceiling (85%, 96%).
- Running total across all real Worlds main-event games scored before their data was added: 35 of 55 + 3 of 3 = **38 of 58 (66%)**.
- The research models on all 7 knockout games so far (no drafts): v1 0.453, the fixed v2 candidate 0.469 (`research/sim2/README.md` step 15).

## Quarter-final 1: IG 3–1 TES (added 5 Nov, v39)
- **New Oracle's Elixir file** (Luke, 5 Nov AEST): 9,861 games, data to 4 Nov 02:20 UTC; one new Worlds series, IG 3–1 TES (3 Nov US; 3–4 Nov UTC; patch 16.20).
- **Checked against Leaguepedia** (https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event/Scoreboards/Quarterfinals, read 5 Nov): sides, winners, lengths 31:02 / 47:09 / 29:29 / 30:58, kills 27–12 / 17–20 / 9–16 / 16–10, and all 40 champions match.
- Rows built from the file (same format as the Swiss rows, `r:"QF"`, `d:"2026-11-03"` = US event day); first pick TES in games 1, 2, 4 and IG in game 3. 55 games now.
- `build_from_oe.py` on a scratch copy: 55/55 Worlds games OK (the 4 new ones included); `js/h2h.js` rebuilt to 4 Nov: IG v TES 8–10 → 11–11. Its `worlds-live.js` output differed only in the play-in team list order, so that file was not copied back.

## Out-of-sample check, quarter-final 1 (the app at v38, before this update; 3,000 simulated games per draft with the real picks)
| Game | App's odds for the winner | Result |
|---|---|---|
| IG vs TES G1 (IG blue) | IG 49% | IG won |
| IG vs TES G2 (IG blue) | TES 53% | TES won |
| TES vs IG G3 (TES blue) | IG 34% | IG won |
| IG vs TES G4 (IG blue) | IG 52% | IG won |

- Favourite won 2 of 4; log loss 0.773, Brier 0.288. The miss that cost most: TES 66% in game 3.
- Running total across all real Worlds main-event games scored before their data was added: 33 of 51 + 2 of 4 = **35 of 55 (64%)**.
- The research models on the same 4 games (no drafts): v1 0.669, the fixed v2 candidate 0.694 (`research/sim2/README.md` step 15).

## Swiss round 5, and HLE–G2 confirmed (added 2 Nov)
- **New Oracle's Elixir file** (downloaded 2 Nov AEST): 9,857 games, data to 1 Nov 11:42 UTC; last Worlds game 31 Oct 23:05 UTC. It has HLE–G2 and all of round 5 (7 games); no knockout games yet.
- **HLE 2-0 G2 confirmed:** the file matches what was entered from the Reddit post-match thread, Leaguepedia and pickorban on every field (sides, winner, length, bans in order, champions, K/D/A, CS including Hans Sama's 212, kill participation, objectives including grubs, first pick; damage share within rounding). Rows replaced with the file's, which adds CS@15.
- **Round 5:** KC 2-0 MKOI, LYON 2-1 LOS, BLG 2-0 HLE, taken from the file. Lengths, bans, objectives, champions, K/D/A and CS match Leaguepedia's Round 5 scoreboards in all 7 games. Cho'Gath (LOS's Curse, game 3) is new at Worlds.
- **H2H:** `build_from_oe.py` (scratch copy) reports 51/51 Swiss games OK and rebuilt `js/h2h.js` to 31 Oct. Changes: BLG v HLE 5-4 → 7-4, KC v MKOI 15-8 → 17-8, LOS v LYON 2-0 → 3-2 (each now met at Worlds). It reproduces HLE v G2 5-0 on its own. As before, its `worlds-live.js` output differed only in the play-in team list order, so that file was built from a scratch merge.
- **Pick/ban check:** the app's pick, ban and win counts for all 90 champions match Leaguepedia's Main Event champion statistics (51 games) exactly.

## Out-of-sample check, Swiss round 5 (the app at v37, before this update; 3,000 simulated games per draft with the real picks)
| Game | App's odds for the winner | Result |
|---|---|---|
| KC vs MKOI G1 (KC blue) | KC 89% | KC won |
| KC vs MKOI G2 (KC blue) | KC 62% | KC won |
| LYON vs LOS G1 (LYON blue) | LOS 11% | LOS won |
| LOS vs LYON G2 (LOS blue) | LYON 86% | LYON won |
| LYON vs LOS G3 (LYON blue) | LYON 71% | LYON won |
| BLG vs HLE G1 (BLG blue) | BLG 66% | BLG won |
| BLG vs HLE G2 (BLG blue) | BLG 51% | BLG won |

- Favourite won 6 of 7; log loss 0.629 and Brier 0.201. The miss was LOS winning game 1 at 11%. KC 89% and LYON 89% / 86% are above the ~80% ceiling.
- Running total across all real Swiss games scored before their data was added (23 + 6 + 5 + 5 + 5 + 7): favourite won 33 of 51 (65%).

## 30 Oct games, and TES–BLG confirmed (added 31 Oct)
- **New Oracle's Elixir file** (downloaded 31 Oct): 9,831 games, data to 30 Oct 22:00 UTC. It has TES–BLG and LOS–TL but not HLE–G2.
- **TES 2-1 BLG confirmed:** all 3 games in the file match what was entered from Leaguepedia and pickorban on every field (sides, winner, length, bans, champions, K/D/A, CS, objectives; damage share and kill participation within rounding). CS@15 and first pick (`fp`) were filled in from the file. The H2H rebuild now produces TES v BLG 8-11 on its own.
- **LOS 2-1 TL:** from the file. K/D/A, CS, kill participation and damage share for game 3 match pickorban (ps-1711005). In game 3 the file and pickorban both give Josedeodo 1/3/5 with TL on 5 kills, so his kill participation is 1.2 (pickorban shows 120%). It's kept as the sources give it; it is the only value above 1.0 in the data.
- **HLE 2-0 G2: not in the file yet.** Picks, bans, K/D/A, length, objectives and first pick from the r/leagueoflegends post-match thread (pasted by Luke). All of these match Leaguepedia's round 4 scoreboards. CS from Leaguepedia; damage share from pickorban (ps-1711006, whole %). Kill participation is calculated from kills. CS@15 is null. Pickorban has Hans Sama on 211 CS in game 2 (Leaguepedia 212); 212 is used. In game 2 HLE died 8 times but G2 got 7 kills on both sources (one death wasn't a G2 kill). First pick: the thread says HLE in game 1 and G2 in game 2, which fits the pick order it shows. The thread's "Player of the Series: Kanavi" is not used (POG still isn't). **Re-check both games against the next Oracle's Elixir file** and fill in CS@15.
- **H2H:** `build_from_oe.py` (scratch copy) rebuilt `js/h2h.js` to 30 Oct (only change: LOS v TL 2-1 at Worlds; the pair had not met before in 2026) and reports 42 of 44 Swiss games OK, with the 2 HLE–G2 games "not in file (yet)". HLE 2-0 G2 was then added by hand (HLE v G2 3-0 → 5-0, met at MSI and Worlds). `research/model/h2h_2026.json` is the file's own output, so it does not have HLE–G2 yet. Its `worlds-live.js` output differed only in the play-in team list order, so that file was edited from a scratch merge instead.
- **Pick/ban check:** after the update, the app's pick, ban and win counts for all 86 champions match Leaguepedia's Main Event champion statistics (44 games) exactly.

## Out-of-sample check, 30 Oct (the app at v33, before this update; 3,000 simulated games per draft with the real picks)
| Game | App's odds for the winner | Result |
|---|---|---|
| LOS vs TL G1 (LOS blue) | LOS 59% | LOS won |
| LOS vs TL G2 (LOS blue) | TL 80% | TL won |
| TL vs LOS G3 (TL blue) | LOS 28% | LOS won |
| G2 vs HLE G1 (G2 blue) | HLE 65% | HLE won |
| HLE vs G2 G2 (HLE blue) | HLE 66% | HLE won |

- Favourite won 4 of 5; log loss 0.573 and Brier 0.192. The miss was LOS winning game 3 at 28%. TL G2 at 80% is at the ceiling.
- Running total across all real Swiss games scored before their data was added (23 + 6 + 5 + 5 + 5): favourite won 27 of 44 (61%).
- Simulations are not seeded, so these numbers move by about a point if re-run.

## 29 Oct games (added 30 Oct)
- **KC 2-0 CFO:** from the Oracle's Elixir file downloaded 30 Oct (data to 29 Oct, 21:00 UTC). Every champion, K/D/A, CS, kill participation and damage share matches pickorban.com (ps-1711004); bans, length, towers, dragons, Barons, Heralds and voidgrubs match Leaguepedia's round 4 scoreboards.
- **TES 2-1 BLG: not in the file yet** (the file ends before it). Taken from Leaguepedia's round 4 scoreboards (sides, winner, length, bans, champions, K/D/A, CS, all objectives) with damage share from pickorban (ps-1711001, whole %); kill participation is calculated from kills. Champions, K/D/A, CS, towers, dragons and Barons match on both sites in all 3 games. CS difference at 15 is not published on either, so it is null; first pick (`fp`) is left out (Leaguepedia's "pick selection" team is not always the first-pick team: KC had pick selection in KC–CFO game 2 but the file shows CFO picking first). **Re-check all 3 games against the next Oracle's Elixir file** and fill in CS@15 and `fp`.
- **H2H:** `build_from_oe.py` (scratch copy) rebuilt `js/h2h.js` to 29 Oct (only change: KC 2-0 CFO at Worlds) and still reports 34/34 Swiss games OK. TES 2-1 BLG was then added by hand (TES v BLG 6-10 → 8-11, met at LPL and Worlds); the next rebuild should reproduce it. `research/model/h2h_2026.json` is the file's own output, so it does not have TES–BLG yet.
- **Pick/ban check:** after the update, the app's Swiss pick, ban and win counts for all 84 champions match Leaguepedia's Main Event champion statistics (39 games) exactly. pickorban's statistics page came up empty and dpm.lol showed a bot check, so they weren't used.
- Leaguepedia's checks of the 28 Oct games also match: the same lengths, including T1–MKOI game 1 at 40:00.

## Out-of-sample check, 29 Oct (the app at v31, before this update; 3,000 simulated games per draft with the real picks)
| Game | App's odds for the winner | Result |
|---|---|---|
| KC vs CFO G1 (KC blue) | KC 52% | KC won |
| CFO vs KC G2 (KC red) | KC 78% | KC won |
| BLG vs TES G1 (BLG blue) | BLG 89% | BLG won |
| BLG vs TES G2 (BLG blue) | TES 10% | TES won |
| TES vs BLG G3 (TES blue) | TES 24% | TES won |

- Favourite won 3 of 5; log loss 0.945 and Brier 0.334, worse than a coin flip. The app had BLG at 76–90% in all three TES games, above the ~80% ceiling, and TES won the series.
- Running total across all real Swiss games scored before their data was added (23 + 6 + 5 + 5): favourite won 23 of 39 (59%).
- After the update (in-sample, only shows the direction): BLG is still 66–88% in the TES games and KC 61% / 88% against CFO. The form update can't fix the ratings gap, which is a job for the new sim (`research/sim-plan.md`).

## 28 Oct games (added 29 Oct)
- **Source:** the Oracle's Elixir 2026 data file downloaded 29 Oct (data to 28 Oct): sides, winner, length, bans, picks, K/D/A, CS, CS difference at 15, damage share, objectives, first pick. Kill participation is calculated from kills and assists over team kills.
- **Cross-check:** every player's champion and K/D/A in all 5 games, plus CS, damage share and towers for T1–MKOI, match pickorban.com's match pages (ps-1711003, ps-1711002). Pickorban showed T1–MKOI game 1 as 20:10; the file says 40:00, which fits the CS and gold, so the file is used. gol.gg, NerfPlz and dpm.lol pages couldn't be reached this time.
- **Check script:** `research/build/build_from_oe.py` (run on a scratch copy) reports all 34 Swiss games OK against the file (`research/model/oe_check.txt`), and rebuilt `js/h2h.js` to 28 Oct. Its only other changes were list order, so `worlds-live.js` was edited by hand.
- **Player of the Game:** still not published by any source checked.

## Out-of-sample check, 28 Oct (the app before this update, 3,000 simulated games per draft with the real picks)
| Game | App's odds for the winner | Result |
|---|---|---|
| T1 vs MKOI G1 (T1 blue) | T1 75% | T1 won |
| T1 vs MKOI G2 (T1 blue) | T1 85% | T1 won |
| LYON vs IG G1 (IG red) | IG 49% | IG won |
| IG vs LYON G2 (LYON red) | LYON 51% | LYON won |
| LYON vs IG G3 (IG red) | IG 49% | IG won |

- Favourite won 3 of 5; log loss 0.508 and Brier 0.168. The IG–LYON games were coin flips to the app (49–51%), so they say little either way.
- T1 G2 at 85% is above the ~80% ceiling the calibration aims for (same issue as T1–CFO on 26 Oct: form plus star bonuses stack).
- Running total across all real Swiss games scored before their data was added (23 + 6 + 5): favourite won 20 of 34 (59%).
- The real-vs-simulator table below has not been re-run with these games.

## What was collected per game
- **All games:** sides, winner, length, all 10 bans and 10 picks with roles, and each player's K/D/A, CS, damage share and kill participation (kill participation is calculated from kills where a source didn't list it).
- **25 Oct games only:** CS difference at 15 and team objectives (dragons, Barons, Heralds, voidgrubs, towers).
- **Not published anywhere I checked:** Player of the Game, so it isn't used.
- **Sides:** worked out from the source pages; under this year's First Selection rule the first-pick team isn't always blue.

## 26 Oct games (added 27 Oct)
- **Source:** pickorban.com match pages (LoL Esports match feed): sides, winner, picks, K/D/A, CS, gold, damage share, kill participation, kills, towers, dragons, Barons.
- **Bans, CS difference at 15, Heralds and voidgrubs** came from the Oracle's Elixir 2026 data file (27 Oct), and the TL–AL bans match the Reddit post-match thread. Ban rates again cover all 51 games. (gol.gg's pages for these games were still empty placeholders, one showing the wrong winner, so they weren't used.)
- **Lengths:** taken from the Oracle's Elixir file for all 29 games. That corrected two earlier lengths (IG–GEN 26:01, not 31:27; TSW–IG 30:20, not 31:52) and replaced the T1–CFO estimate (27:23). Others moved by a few seconds.
- **Cross-check:** every player's champion and K/D/A in all 29 games matches the Oracle's Elixir file. One objective differed: T1 took 1 Baron against CFO (Pickorban said 2); the file's figure is used.
- **Player of the Game:** still not published by any source I could reach. Pickorban's "top performer" is its own pick (best KDA and kill participation), not the official award, so it isn't used.

## Out-of-sample check, 26 Oct (the app before this update)
| Game | App's odds for the winner | Result |
|---|---|---|
| T1 vs CFO | T1 81% | T1 won |
| BLG vs KC | BLG 88% | BLG won |
| LOS vs TSW (G1, G2) | LOS 45% | LOS won both |
| TL vs AL G1 (TL red) | TL 31% | TL won |
| TL vs AL G2 (TL blue) | TL 39% | TL won |

- Favourite won 2 of 6; log loss 0.676 and Brier 0.251, roughly a coin flip.
- Running total across all real Swiss games scored before their data was added (23 + 6): favourite won 17 of 29 (59%).
- The misses are the same kind seen in the season back-test: the ratings in `js/data.js` overrate some LPL teams (AL) and underrate others (TL, LOS).
- After adding the games, T1 vs CFO rises to 96%, which is above the 80% ceiling the calibration aimed for. Form updates stack with star bonuses, so a few strong games can push odds too far. A fitted model would control this (see below).

## Real games vs the simulator (all 29 Swiss games, same pairings simulated 60× each)
| Per game | Real | Sim |
|---|---|---|
| Length (min) | 33.4 | 32.8 |
| Kills (both teams) | 25.6 | 20.4 |
| Dragons* | 4.8 | 4.6 |
| Barons* | 1.6 | 1.4 |
| Towers* | 11.7 | 12.4 |
| Kill share top / jungle / mid / ADC / support | 19 / 19 / 29 / 29 / 4% | 17 / 20 / 29 / 29 / 6% |

\* Objectives only for the 13 games where they were published.
- Length, objectives and who gets the kills are close. The sim produces about 20% too few kills.

## How the app uses it (never for simulated standings)
- **Champion cards (Worlds meta):** play-ins (22 games) plus the real Swiss games, so 61 games now (bans over all 61). Your simulated run is shown on a separate line.
- **Draft presence:** the blended pro presence is mixed with real Worlds presence. The Worlds share is games / (games + 60), so about 50% now (61 games), rising as more games are added.
- **Win rate:** real Worlds wins are folded into the sample-adjusted win rate, counted double for recency.
- **Pairs with:** team-mates who won together at Worlds. Draft suggestions add a bonus for pairs with 2+ games together.
- **Countered by:** lane opponents that beat a champion at Worlds. Lane matchups with 2+ games are also used where METAsrc has no number.
- **Player pools:** each player's real Worlds champions join their pool, counted double for recency. Champions new to a player are tagged "new at Worlds".
- **Player form:**
  - Each player's K/D/A, kill participation, damage share, deaths per game, kill share, CS per minute (or CS difference at 15) and objectives (where available) are compared with the average for their role at Worlds (z-scores).
  - Each skill moves by the average z of its metrics, capped at ±1 per game and ±3 in total.
  - Tendency tags: "Carry focus" (damage share), "Low-risk" (few deaths), "Map player" (kill participation), "Aggressive" (kill share).

## Checks
- **Replay of the 23 games, before the update:** the favourite won 65% of games, but log loss was 0.697, about a coin flip. This was a fair out-of-sample test of the app as it was.
- **After the update:** log loss 0.603 and Brier score 0.205. This is in-sample (the form was built from these games), so it only shows the update points the right way. The real test is the next match days.
- **Simulator targets unchanged:**
  - Games average 33 minutes.
  - The team that takes the first Baron wins 83%; the team that takes the first Elder wins 75%.
  - POG shares by role: top 21%, jungle 22%, mid 27%, ADC 21%, support 9%.
  - Keria still leads supports at about 15% POG per game, double the next support.
- **Star cap:** the star-player effect is now capped at a rating of 96, so a hot start can't run away (e.g. Knight moved to 97 after two strong games).

## Updating after each match day
Add the new games to `js/worlds-live.js` (same row format) and bump the cache version. Everything else recalculates on load.
With a newer Oracle's Elixir file in `research/`: run `research/build/build_from_oe.py` on a scratch copy to rebuild `js/h2h.js` and check every game, then copy back only the files that really changed (see CLAUDE.md).

## Sources
- https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event/Scoreboards/Quarterfinals (IG 3–1 TES, all 4 games, 5 Nov)
- Oracle's Elixir 2026 match data file (downloaded 2 Nov AEST, data to 1 Nov 11:42 UTC; kept local in `research/`).
- https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event/Scoreboards/Round_5 (all 7 round 5 games, 2 Nov)
- https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event/Champion_Statistics (51 games, 2 Nov) Download: https://oracleselixir.com/tools/downloads → Google Drive folder https://drive.google.com/drive/u/1/folders/1gLSw0RLjBbtaNy0dgnGQDAZOHIgCe-HH (updated once a day)
- r/leagueoflegends post-match thread, HLE 2-0 G2 (pasted by Luke, 31 Oct)
- https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event/Scoreboards/Round_4 (HLE vs G2: CS, objectives, bans, lengths; 31 Oct)
- https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event/Champion_Statistics (44 games, 31 Oct)
- https://pickorban.com/matches/ps-1711006 (G2 vs HLE, damage share; 31 Oct)
- https://pickorban.com/matches/ps-1711005 (TL vs LOS, game 3; 31 Oct)
- https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event (schedule, results, pick/side selection, 30 Oct)
- https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event/Scoreboards/Round_4 (TES vs BLG and KC vs CFO, 30 Oct)
- https://lol.fandom.com/wiki/2026_Season_World_Championship/Main_Event/Champion_Statistics (39 games, 30 Oct)
- https://pickorban.com/matches/ps-1711001 (TES vs BLG, 29 Oct)
- https://pickorban.com/matches/ps-1711004 (KC vs CFO, 29 Oct)
- https://pickorban.com/matches/ps-1711003 (MKOI vs T1, 28 Oct)
- https://pickorban.com/matches/ps-1711002 (IG vs LYON, 28 Oct)
- https://dotesports.com/league-of-legends/news/worlds-2026-swiss-day-1-results
- https://dpm.lol/esports/matches/139806-anyones-legend-vs-karmine-corp
- https://dpm.lol/esports/matches/139807
- https://egamersworld.com/lol/news/38054/geng-survive-lyon-scare-2-1-thriller-punches-world-mCAx_65XC
- https://gol.gg/game/stats/83654/page-fullstats/
- https://gol.gg/game/stats/83654/page-game/
- https://gol.gg/game/stats/83654/page-timeline/
- https://gol.gg/game/stats/83655/page-fullstats/
- https://gol.gg/game/stats/83655/page-game/
- https://gol.gg/game/stats/83655/page-timeline/
- https://gol.gg/game/stats/83656/page-fullstats/
- https://gol.gg/game/stats/83656/page-game/
- https://gol.gg/game/stats/83656/page-timeline/
- https://gol.gg/game/stats/83657/page-fullstats/
- https://gol.gg/game/stats/83657/page-game/
- https://gol.gg/game/stats/83657/page-timeline/
- https://gol.gg/game/stats/83659/page-fullstats/
- https://gol.gg/game/stats/83659/page-game/
- https://gol.gg/game/stats/83659/page-timeline/
- https://gol.gg/game/stats/83660/page-fullstats/
- https://gol.gg/game/stats/83660/page-game/
- https://gol.gg/game/stats/83660/page-timeline/
- https://gol.gg/game/stats/83661/page-fullstats/
- https://gol.gg/game/stats/83661/page-game/
- https://gol.gg/game/stats/83661/page-timeline/
- https://www.gosugamers.net/lol/news/79405-karmine-corp-stun-anyone-s-legend-in-another-lec-upset-at-worlds-2026-swiss-stage
- https://www.gosugamers.net/lol/news/79414-gen-g-defeat-lyon-to-become-second-team-to-qualify-for-worlds-2026-knockout-stage
- https://www.invenglobal.com/articles/27686/geng-reaches-3-wins-as-well-beats-lyon-2-1-to-advance-to-quarterfinals
- https://www.nerfplz.com/lol-pro-games/dk-vs-g2-game-1-worlds-2026-10-23/
- https://www.nerfplz.com/lol-pro-games/dk-vs-t1-game-1-worlds-2026-10-24/
- https://www.nerfplz.com/lol-pro-games/dk-vs-t1-worlds-2026-10-24/
- https://www.nerfplz.com/lol-pro-games/hle-vs-gen-game-1-worlds-2026-10-24/
- https://www.nerfplz.com/lol-pro-games/ig-vs-gen-game-1-worlds-2026-10-23/
- https://www.nerfplz.com/lol-pro-games/kc-vs-al-worlds-2026-10-23/
- https://www.nerfplz.com/lol-pro-games/kc-vs-lyon-game-1-worlds-2026-10-24/
- https://www.nerfplz.com/lol-pro-games/los-vs-g2-game-1-worlds-2026-10-24/
- https://www.nerfplz.com/lol-pro-games/los-vs-t1-game-1-worlds-2026-10-23/
- https://www.nerfplz.com/lol-pro-games/lyon-vs-tsw-game-1-worlds-2026-10-24/
- https://www.nerfplz.com/lol-pro-games/mkoi-vs-blg-game-1-worlds-2026-10-23/
- https://www.nerfplz.com/lol-pro-games/mkoi-vs-cfo-game-1-worlds-2026-10-24/
- https://www.nerfplz.com/lol-pro-games/tes-vs-al-game-1-worlds-2026-10-24/
- https://www.nerfplz.com/lol-pro-games/tes-vs-hle-game-1-worlds-2026-10-23/
- https://www.nerfplz.com/lol-pro-games/tlaw-vs-blg-game-1-worlds-2026-10-25/
- https://www.nerfplz.com/lol-pro-games/tlaw-vs-cfo-game-1-worlds-2026-10-23/
- https://www.nerfplz.com/lol-pro-games/tsw-vs-ig-game-1-worlds-2026-10-24/
- https://gol.gg/game/stats/83654/page-game/ (and 83655–83657, 83659–83661)
- https://dpm.lol/esports/matches/139807
- https://pickorban.com/worlds/matches
- https://pickorban.com/matches/ps-1710998 (T1 vs CFO)
- https://pickorban.com/matches/ps-1710997 (KC vs BLG)
- https://pickorban.com/matches/ps-1710999 (LOS vs TSW)
- https://pickorban.com/matches/ps-1711000 (TL vs AL)
- https://riftdaily.com/worlds-2026-tsw-al-eliminated/ (game lengths)
- https://gol.gg/game/stats/83663/page-summary/ (BLG vs KC length)
- https://www.invenglobal.com/articles/27718/t1-defeat-cfo-behind-bot-duos-performance-to-reach-2-wins
- https://www.sheepesports.com/en/articles/worlds-2026-los-and-tl-knock-out-tsw-and-al-as-t1-and-blg-reach-2-1/en
- https://www.gosugamers.net/lol/news/79422-team-secret-whales-anyone-s-legend-are-the-first-teams-eliminated-from-worlds-2026-swiss-stage
