# Sim session 1 — working files (ratings and the who-wins model)

Built 3 Nov 2026 (AEST) in one Claude Code session. **The report is not written yet** (next session). Decisions are in `research/sim-plan.md`; results tables are in `research/model/sim1/`.

All scripts are read-only on the Oracle's Elixir CSV and were run from a scratch folder with intermediate files next to them. To re-run, copy this folder somewhere outside the repo and run in this order (each script's docstring has its usage line):

| Step | Script | Makes |
|---|---|---|
| 1 | `prep.py` | `games.csv` — one row per major-league / international game (2,845), WLDs rows before 1 Oct dropped |
| 2 | `teamfit.py` | team ratings, tuning (90-day half-life, ridge 2, temperature 1.125), tests a/b/c → `teamfit_results.json`, `team_ratings_now.csv` |
| 3a | `playerprep.py` (n0 = 6) | per-game skill values `prow.csv`, pre-game estimates `gfeat.csv`, estimates now `pnow.csv` (includes the pre-set replacement candidates) |
| 3b | `playerfit.py` | team + player model, ADC Positioning v Late game, unadjusted cards → `playerfit_results.json`, `player_cards_now.csv` |
| 3c | `leaguefit.py` | league shift per role from international games, recheck of weights, replacement candidates, league-adjusted cards → `leaguefit_results.json`, `player_cards_league_adjusted.csv` |
| — | `scales.py` | card-scale options S0–S4 → `card_scales.csv` (S5 adopted; computed inline, saved as `player_cards_S5.csv`) |
| — | `deeper.py`, `faker.py` | league gaps by game time and role, "wins beyond stats", weak skills by game length, Faker's 2026 stats |
| — | `idmap.py` | fixed ID lookup → `id_teams.csv`, `id_players.csv` (16/16 teams, 80/80 players) |
| — | `columns.py` | data-file column coverage |
| — | `lp_players.json`, `gol_players.json` | Leaguepedia Worlds Main Event player stats and gol.gg S16 season stats (read 3 Nov) used for the source checks |
| — | `exp_rows.json`, `exp_save.py`, `experience_progress.md` | pre-2026 career facts from Leaguepedia's data export (read 3 Nov) → `player_experience_pre2026.csv` |
| — | `exptest.py` | experience test (titles, Worlds titles, international games, veterans) |
| — | `compare_app.py` | new model v the app's recorded pre-update odds on the 51 Swiss games |
| — | `score_v37.txt` | round 5 out-of-sample scoring of the app (v37) |

Headline results (details for the report):
- Team ratings alone: log loss 0.649 on games from 1 Sep (311), 0.649 on Worlds (73); blue side only 0.685; coin flip 0.693.
- Team + league-adjusted player skills: 0.646 from 1 Sep, 0.645 on Worlds.
- Against the current app on the 51 Worlds Swiss games: new 0.639 v app 0.679 (favourite 32 v 33 of 51); new model uses no drafts.
- Extra Worlds weight made predictions worse (decision 6 changed). Experience: right direction, inconsistent; re-test after the knockouts.
- Sources: all 80 Worlds players' Swiss stats match Leaguepedia exactly; gol.gg season stats agree closely (damage share, damage per minute 1.000; kill participation 0.998; gold at 15 0.975; CS at 15 0.84; XP at 15 0.73).
