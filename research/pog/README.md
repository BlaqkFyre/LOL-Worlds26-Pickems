# Player of the Game and per-game ratings: research (6 Nov 2026)

Groundwork for sim session 4 (decision 6 in `research/sim-plan.md`; Luke confirms it again before session 4's final commit).
Scripts run from a scratch folder (Python + pandas, `python -I`); the Oracle's Elixir CSV stays local.

## Sources
- **Leaguepedia Cargo export** (`https://lol.fandom.com/wiki/Special:CargoExport`, read 6 Nov 2026 with plain requests, no spoofing):
  - per game: `MatchScheduleGame.MVP` joined to `ScoreboardGames` (date, sides, winner) → `pog_games_2026.json` (1,546 rows, all 2026 events)
  - per series: `MatchSchedule.MVP` → `pog_series_2026.json` (1,734 rows)
- Where Leaguepedia takes the awards from (broadcast, league site) was not checked.
- **LCK has no per-game award in 2026** in any source checked: Leaguepedia's per-game field is empty for every LCK 2026 game (only a showmatch has one); LCK's own 2026 awards notice (lolesports.com, read 6 Nov) lists "Most POMs" (Player of the Match, per series); Sheep Esports match pages (HLE v T1, playoffs, Game 1 and Game 5 tabs) show no award. Liquipedia's LCK page asked for a human check and was not read.

## Steps
| # | Script | Output | What it does |
|---|---|---|---|
| 1 | `pog_pull.py <out_dir>` | `pog_games_2026.json`, `pog_series_2026.json` | pulls both award tables, 500 rows a page |
| 2 | `pog_match.py <OE csv> <dir>` | `pog_games_matched.csv`, `pog_series_matched.csv` (kept local, about 8 MB; rebuild with this step) | matches awards to the file: same two teams (Leaguepedia → file names, a few aliases), game number, start within 6 h; series games within 8 h of the series' first game. Per game: LPL 672 of 685, LCS 260 of 260, First Stand 45 of 45; every award winner found among the game's 10 players. Series: 916 (LCP Wildcard rows dated 2025 aren't in the file) |
| 3 | `pog_measure.py <dir> <out json>` | `research/model/pog/pog_measure.json`, `pog_worlds_series_scored.csv` | who wins awards; a quick choice model among the winning five (fitted on LPL Splits 1–2 and their playoffs; judged on later LPL games and on LCS + First Stand); LPL series MVP v per-game awards; the per-game model naming series MVPs elsewhere |
| 4 | `pog_rate_example.py <OE csv> <measure json> <gameid>` | printout | example rating on a 6 + 1.5 × z scale (superseded by step 5) |
| 5 | `pog_pct_compare.py <OE csv> <measure json> <gameid>` | printout | percentile ratings from two scores: today's app formula (`gameStats` in `js/tournament.js`) and the quick model; reference = major-league player-games before 1 Sep, check on games from 1 Sep |
| 6 | `pog_fit.py <OE csv> <dir> <out json>` | `research/model/pog/pog_fit.json` | the session 4 refit: only stats the new sim produces (kills, deaths, assists, kill participation, damage share, CS lead at 15, vision per minute, role); A today's app formula with one fitted temperature, B per-game awards, C per-game + series awards (series MVP chance = mean of the player's per-game chances over the games his team won; LPL / LCS / First Stand series left out so no game counts twice). Two held-out checks: games and series from 1 Sep, and whole leagues (fit on LPL, judge on LCS + First Stand; series fit without LCK, judge on LCK) |

## Results (quick model, not final)
- Awards always go to the winning side (977 of 977 games; 916 of 916 series).
- Per-game role shares: jungle 32%, mid 25%, ADC 18%, top 15%, support 10% (LCS gives supports 13%, LPL 9%).
- The winning side's leader in kills gets the award 48% of the time; in KDA 39%, damage share 34%.
- Choice model: right pick 65% on later LPL games (159), 61% on LCS + First Stand (305, never fitted), against 52% for "most kills"; log loss 0.99 / 1.04 against 1.61 for a coin among five. Fitted on 381 LPL games (rows with missing stats dropped).
- LPL has both kinds of award: the series MVP won at least one game award in 95% of series; when one player had the most game awards, he was series MVP 95% of the time (153 of 246 series had a tie).
- The per-game model, summed over the games a team won, names the series MVP in 51% of 883 series (LCK 50%, LEC 55%; chance about 20%).
- Today's app ratings (400 simulated games, v43): winners 6.6, losers 2.9 on average; 6% of losers reach 5.
- Percentile ratings on real games from 1 Sep: app formula winners 7.3 / losers 2.7 (11% of losers 5+); quick model 6.4 / 3.3 (25% of losers 5+).
- BLG 3–0 DK game 1 (percentile of the quick model ÷ 10): Xun 9.2, Knight 8.9, Viper 5.8, ON 5.4, Bin 3.4; Lucid 3.6, Siwoo 3.6, Career 2.6, Smash 1.8, ShowMaker 1.1. Over the series the model names Xun; Leaguepedia's series MVP is Xun.

## Refit with the sim's stats (step 6, 6 Nov)

Held out by date (from 1 Sep: 86 games with per-game awards, LPL and LCS; 41 series, LCK, LEC, CBLOL and all 15 Worlds series):

| Model | Games: right pick | Games: log loss | Series: right pick | Series: log loss |
|---|---|---|---|---|
| A today's app formula | 47.7% | 1.320 | 41.5% | 1.711 |
| B per-game awards | 52.3% | 1.167 | 51.2% | 1.510 |
| C per-game + series awards | 52.3% | 1.181 | 46.3% | 1.503 |

Whole leagues held out (larger): per-game fitted on LPL only, judged on all 305 LCS + First Stand games; series fitted without LCK, judged on all 188 LCK series:

| Model | LCS + FST: right pick | LCS + FST: log loss | LCK series: right pick | LCK series: log loss |
|---|---|---|---|---|
| A today's app formula | 48.9% | 1.214 | 41.5% | 1.520 |
| B per-game awards | 59.3% | 1.091 | 47.9% | 1.390 |
| C per-game + series awards | 57.4% | 1.086 | 47.3% | 1.372 |

(A coin among five: 20%, log loss 1.609.)

- **Both fitted models beat today's formula on every check**, by a clear margin (log loss 0.12–0.21 better).
- **Series awards as extra training (C v B) are a wash so far:** slightly better log loss in three of four checks, slightly worse top pick in three of four; differences are within what 41–305 test cases can tell apart. Luke to decide whether to keep them in.
- Fitted weights (C, per standard deviation): kills +1.00, deaths −0.52, damage share +0.50, vision +0.35, kill participation +0.32, assists +0.30, CS lead at 15 +0.23; roles v top: jungle +0.10, mid −0.43, support −0.16, ADC −1.54 (ADCs need more numbers for the same chance, as in real awards).
- Role shares on the held-out games, model C v real: jungle 28% v 33%, mid 28% v 23%, ADC 18% v 20%, top 16% v 15%, support 10% v 9%.
- Dropping the stats the sim doesn't make (damage taken, gold share, gold lead) costs a little against the quick model (LCS + First Stand right pick 59% v 61%).

## Still to do (session 4)
- **Version C chosen (Luke, 6 Nov):** per-game + series awards.
- Ratings: percentile of the chosen model's score among real pro games in the role ÷ 10 (decision 6); recompute the reference table with the final weights.
- Build into the app with the new sim (session 4), then confirm with Luke before the final commit.
