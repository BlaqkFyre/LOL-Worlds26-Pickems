# Real Worlds 2026 Swiss games — data and how the app uses them

Collected 26 Oct 2026: **23 games** from Swiss rounds 1–3 (16 Bo1s on 23–24 Oct; on 25 Oct HLE vs IG, TES vs G2, DK 2-0 MKOI, GEN 2-1 LYON). The rest of round 3 (26 Oct) had not been played yet. Data: `js/worlds-live.js`.

## What was collected per game
- **All games:** sides, winner, length, all 10 bans and 10 picks with roles, and each player's K/D/A, CS, damage share and kill participation (kill participation is calculated from kills where a source didn't list it).
- **25 Oct games only:** CS difference at 15 and team objectives (dragons, Barons, Heralds, voidgrubs, towers).
- **Not published anywhere I checked:** Player of the Game, so it isn't used.
- **Sides:** worked out from the source pages; under this year's First Selection rule the first-pick team isn't always blue.

## How the app uses it (never for simulated standings)
- **Champion cards (Worlds meta):** play-ins (22 games) plus the real Swiss games, so 45 games now. Your simulated run is shown on a separate line.
- **Draft presence:** the blended pro presence is mixed with real Worlds presence. The Worlds share is games / (games + 60), so about 43% now, rising as more games are added.
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

## Sources
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
