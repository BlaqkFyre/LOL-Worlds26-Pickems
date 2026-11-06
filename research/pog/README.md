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

## Still to do (session 4)
- Refit with only the stats the new sim produces (no damage taken), add series awards as training data, hold out games from 1 Sep and the Worlds series.
- Compare with today's formula on the same games; it ships only if it is better there.
