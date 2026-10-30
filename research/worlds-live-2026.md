# Real Worlds 2026 Swiss games — data and how the app uses them

Updated 30 Oct 2026: **39 games**, all of Swiss rounds 1–3 (16 Bo1s on 23–24 Oct; on 25 Oct HLE vs IG, TES vs G2, DK 2-0 MKOI, GEN 2-1 LYON; on 26 Oct T1 vs CFO, BLG vs KC, LOS 2-0 TSW, TL 2-0 AL) plus Swiss round 4 days 1–2 (28 Oct: T1 2-0 MKOI, IG 2-1 LYON; 29 Oct: KC 2-0 CFO, TES 2-1 BLG). Data: `js/worlds-live.js`.

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
- Oracle's Elixir 2026 match data file (downloaded 30 Oct, data to 29 Oct 21:00 UTC; kept local in `research/`). Download: https://oracleselixir.com/tools/downloads → Google Drive folder https://drive.google.com/drive/u/1/folders/1gLSw0RLjBbtaNy0dgnGQDAZOHIgCe-HH (updated once a day)
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
