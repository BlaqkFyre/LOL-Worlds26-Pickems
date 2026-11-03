# Sim session 1 report: ratings and the who-wins model

Written 3 Nov 2026 (AEST) from the session 1 working files. Fitting and tests were done on 3 Nov (AEST) in an earlier session; this report only reads their saved results. Nothing was re-run for it.

- Plan and decisions: `research/sim-plan.md` (session 1, decisions 1–8).
- Scripts and how to re-run: `research/sim1/README.md`.
- Result tables: `research/model/sim1/` (file names given with each section below).
- Data: Oracle's Elixir 2026 file downloaded 2 Nov AEST (data to 1 Nov 11:42 UTC). Major leagues and internationals only: 2,845 games, with the file's "WLDs" rows before 1 Oct dropped. No knockout games.

**App change: none.** The app is still v38 and still uses the old engine. The app only changes in sim session 4.

---

## 1. Summary

- **The new model beats the app on the 51 Worlds Swiss games:** log loss 0.639 against 0.679, using no draft information. The app used the real drafts. The favourite won 32 of 51 for the new model and 33 of 51 for the app.
- **It beats the simple baselines on held-out games from 1 Sep:** log loss 0.646 (team + players) and 0.649 (teams only), against 0.685 for "blue side wins" and 0.693 for a coin flip.
- **Most of the gain comes from team results.** Player skills add a little (0.649 → 0.646 from 1 Sep; Worlds 0.649 → 0.645). Player skills alone do worse than team results alone.
- **League strength is measured, not set.** LCK +1.49, LPL +0.95, LEC +0.14, LCS −0.12, LCP −0.72, CBLOL −0.79 (log-odds, linked through First Stand, MSI, EWC and Worlds).
- **Calibration is good on the 311 games from 1 Sep.** At Worlds (73 games) it is off by 10–12 points in the 60–80% bands. That sample is small (n = 23 and 16).
- **Changed from the plan:** extra weight for Worlds games made predictions worse, so it was dropped (decision 6). Experience (titles, international games) points the right way but did not help consistently, so it is not used for now and is re-tested after the knockouts.
- **Team order is close to the app's:** 15 of 16 teams within 2 places; AL is the exception (app 5th, new 8th).
- **Open:** Faker's card (S5 overall 72) must not stay a mid rating; four skills carry almost no weight; the S5 card step has no saved script. Details in section 9.

---

## 2. Scorecard

Log loss: lower is better (coin flip 0.693). Brier: lower is better (coin flip 0.250). "Fav won" = share of games the model's favourite won. Every row is on games the model was not fitted to.

| Test | Games | Model | Log loss | Brier | Fav won |
|---|---|---|---|---|---|
| (a) fit at 1 Sep, predict from 1 Sep | 311 | Teams only | 0.649 | 0.230 | 59.2% |
| (a) same | 311 | Teams + league-adjusted players | **0.646** | — | 63.7% |
| (a) same | 311 | Blue side only | 0.685 | 0.246 | 56.3% |
| (a) same | 311 | Coin flip | 0.693 | 0.250 | — |
| (b) Worlds, refit day by day | 73 | Teams only | 0.649 | 0.231 | 63.0% |
| (b) Worlds play-ins | 22 | Teams only | 0.647 | 0.229 | 68.2% |
| (b) Worlds Swiss | 51 | Teams only | 0.650 | 0.231 | 60.8% |
| (b) Worlds | 73 | Teams + league-adjusted players | **0.645** | — | 61.6% |
| (c) rolling, refit monthly | 2,220 | Teams only | 0.645 | 0.227 | 62.4% |
| (c) rolling, Sep–Oct only | 311 | Teams only | 0.651 | 0.230 | 60.5% |
| **Against the app**, Worlds Swiss | 51 | Teams + players, refit day by day | **0.639** | — | 32 of 51 |
| same games | 51 | App (old engine, real drafts) | 0.679 | — | 33 of 51 |

Sources: `teamfit_results.json` (teams only, baselines, rolling), `leaguefit_results.json` → `adjusted_base` (teams + league-adjusted players), `research/sim1/README.md` (against the app; from `compare_app.py`).

Notes on the app comparison:
- The app's odds are the ones recorded before each match day's data was added (`research/worlds-live-2026.md`). For the first 23 games only the combined log loss (0.697) was recorded; the other 28 have per-game odds.
- `compare_app.py`'s per-game output was printed, not saved, so the per-game table is not in the repo.
- The app hit 89% several times (KC, LYON, BLG). The new model's highest odds on Worlds games were T1 90% v CFO and GEN 86% v LYON (teams only, `worlds_games` in `teamfit_results.json`). Decision 7 says no hand cap; the calibration table below is the check.

Tuning (games before 1 Sep only, 1,909 validation games): log loss 0.644, Brier 0.226, favourite 62.7%.

### Calibration (teams only)

When the model says X%, how often the favourite won. Target: each band within about 5 points.

| Band | From 1 Sep: games | Said | Won | Worlds: games | Said | Won |
|---|---|---|---|---|---|---|
| 50–60% | 177 | 55.3% | 50.8% | 24 | 54.0% | 58.3% |
| 60–70% | 82 | 66.2% | 63.4% | 23 | 66.7% | 56.5% |
| 70–80% | 37 | 74.3% | 75.7% | 16 | 74.5% | 62.5% |
| 80–90% | 14 | 84.4% | 92.9% | 9 | 82.5% | 88.9% |
| 90–100% | 1 | 93.2% | 100% | 1 | 90.2% | 100% |

- From 1 Sep: the three bands with 37+ games are within 5 points. The 80–90% band is 8.5 points under-confident on 14 games.
- Worlds: the 60–70% and 70–80% bands are 10 and 12 points over-confident, on 23 and 16 games. Too few games to call; recheck when the knockouts are added.

### By league (test a, teams only)

| League | Games | Log loss | Fav won |
|---|---|---|---|
| Worlds | 73 | 0.620 | 58.9% |
| LCK | 33 | 0.634 | 54.5% |
| CBLOL | 64 | 0.651 | 56.3% |
| LEC | 31 | 0.656 | 61.3% |
| LCS | 70 | 0.660 | 62.9% |
| LPL | 40 | 0.685 | 60.0% |

LPL is the hardest league to call (0.685, close to a coin flip). The model frozen at 1 Sep did better on Worlds (0.620) than the day-by-day refit (0.649); with 73 games this difference is within noise (not tested).

---

## 3. Team ratings

Model: P(blue wins) = sigmoid((side + team rating(blue) − team rating(red)) / T). Team rating = league strength + the team's own strength in its league, pulled toward its league average when it has few games (ridge).

Chosen by the tuning test (games before 1 Sep):

| Setting | Chosen | Tried |
|---|---|---|
| Recency half-life | 90 days | 30, 60, 90, 180, none |
| Pull toward league average (ridge) | 2 | 0.5, 1, 2, 4, 8 |
| Temperature T (softens odds) | 1.125 | fitted on validation only |
| Extra weight for the same event's earlier games | ×1 (none) | ×1 0.659, ×1.5 0.666, ×2 0.672, ×3 0.683, ×5 0.700 |
| Blue side | +0.233 log-odds | blue won 55.5% of training games |

The top settings were close: 90 days / ridge 2 gave 0.6446, 60 days 0.6449, 180 days 0.6454.

### League strength (log-odds, now)

| LCK | LPL | LEC | LCS | LCP | CBLOL |
|---|---|---|---|---|---|
| +1.49 | +0.95 | +0.14 | −0.12 | −0.72 | −0.79 |

### The 16 Worlds teams, now (fitted on all games to 31 Oct)

"Win % v average" = chance to beat an average team of the 16 on a neutral side. Source: `worlds16_now` in `teamfit_results.json`; all 71 teams in `team_ratings_now.csv`.

| Rank | Team | League | Rating | Win % v average | App overall (v38) | App rank |
|---|---|---|---|---|---|---|
| 1 | GEN | LCK | 2.37 | 76% | 94.0 | 1 |
| 2 | HLE | LCK | 1.96 | 69% | 91.8 | 2 |
| 3 | T1 | LCK | 1.90 | 68% | 90.8 | 4 |
| 4 | DK | LCK | 1.85 | 67% | 87.0 | 6 |
| 5 | BLG | LPL | 1.82 | 66% | 91.0 | 3 |
| 6 | IG | LPL | 1.24 | 54% | 83.0 | 8 |
| 7 | TES | LPL | 1.23 | 54% | 81.6 | 9 |
| 8 | AL | LPL | 1.20 | 53% | 87.4 | **5** |
| 9 | G2 | LEC | 1.00 | 49% | 84.4 | 7 |
| 10 | KC | LEC | 0.94 | 47% | 81.6 | 10 |
| 11 | LYON | LCS | 0.80 | 44% | 81.6 | 12 |
| 12 | TL | LCS | 0.70 | 42% | 81.6 | 11 |
| 13 | MKOI | LEC | 0.37 | 35% | 77.6 | 13 |
| 14 | LOS | CBLOL | 0.16 | 31% | 71.8 | **16** |
| 15 | TSW | LCP | 0.03 | 29% | 72.6 | 14 |
| 16 | CFO | LCP | −0.59 | 19% | 72.6 | 15 |

App column: each team's `t.ov` as the app shows it on Power Rankings (`js/core.js` line 19: player overall = rounded average of 3 attributes, team = average of the 5, after the Worlds form update from `js/worlds-live.js`). Read on 3 Nov from the running app (v38) on a local server, console clean. The app's rank breaks ties (TES, KC, LYON, TL all 81.6) by list order. The two scales are different, so compare ranks, not sizes.

- The ranks are close: same place for GEN, HLE, KC and MKOI; 15 of 16 teams within 2 places.
- The one bigger difference is **AL**: app 5th, new 8th (the AL miss the plan named). Moved 2 places: DK, IG, TES and LOS higher in the new model; BLG and G2 lower.
- Because the order is so similar, the gain on the Swiss games may come more from how far apart the teams are than from their order. Not tested.
- Before the Worlds form update the app's overalls were within 1.6 of these (e.g. T1 89.2, DK 85.6, KC 80.2), worked out by taking each player's form change back off; clamping at 50/99 was not undone (not checked whether any player hit it).

Three teams not at Worlds rate above IG (1.24): KT Rolster 1.52, Ninjas in Pyjamas 1.39, BNK FEARX 1.27.

---

## 4. Player skills

Per role, 3 skills from the table agreed on 2 Nov (`research/sim-plan.md`, decision 2). Each game's value is measured against the lane opponent or role average and adjusted for game length; a player's skill is a recency-weighted average pulled toward the role average (n0 = 6 games). The team + player model then fits how much each skill adds to winning beyond the team rating.

Chosen by the tuning test:
- **Pull on player weights (ridge):** 80 (tried 1–640; 80 best at 0.6364).
- **ADC third skill: Late game** (gold/XP lead at 20–25, damage share in long games). Test from 1 Sep: Late game 0.6468, neither 0.6476, both 0.6477, Positioning 0.6485.

What each part is worth (test from 1 Sep, `playerfit_results.json`):

| Model | Log loss from 1 Sep | Worlds (73) |
|---|---|---|
| Teams only (refit in this step) | 0.653 | 0.651 |
| Players only | 0.656 | 0.677 |
| Teams + players | 0.647 | 0.647 |
| Teams + league-adjusted players | **0.646** | **0.645** |

### League shift

A player's per-game numbers come from games against their own league. In international games, players from weaker leagues fall short against stronger-league opponents. The shift per role (skill z per 1.0 of league strength):

| Top | Jungle | Mid | ADC | Support |
|---|---|---|---|---|
| 0.138 | 0.141 | 0.119 | 0.205 | 0.082 |

All are well clear of zero (standard errors 0.016–0.020). The ADC gap between leagues is the largest, support the smallest.

### Skill weights (how much each skill predicts winning)

Fitted weights on the league-adjusted skills (`adjusted_base.weights` in `leaguefit_results.json`). These make the Overall (decision 4).

| Role | Skill | Weight |
|---|---|---|
| Top | Consistency: side pressure | **0.145** |
| Top | Laning | 0.046 |
| Top | Consistency: durability | 0.047 |
| Top | Consistency: steadiness | 0.002 |
| Top | Teamfight | −0.001 |
| Jungle | Objectives | **0.092** |
| Jungle | Early game | 0.069 |
| Jungle | Teamfight | 0.031 |
| Mid | Laning | **0.126** |
| Mid | Damage | 0.084 |
| Mid | Map impact | −0.002 |
| ADC | Late game | **0.114** |
| ADC | Laning (own) | 0.036 |
| ADC | Laning (bot duo) | 0.035 |
| ADC | Damage | −0.006 |
| Support | Map presence | 0.044 |
| Support | Reliability | 0.035 |
| Support | Playmaking | 0.032 |

- Biggest: top side pressure, mid laning, ADC late game, jungle objectives.
- **Four skills add nothing** (weight within ±0.006): top Teamfight, top steadiness, mid Map impact, ADC Damage. They still show on cards but do not move the Overall.
- Replacement candidates were tested (`candidates` in `leaguefit_results.json`). None changed the test log loss by more than 0.0006. The largest weight was mid "kills + assists by 15" (0.113, test 0.6459 v 0.6461). Not adopted; see section 9.

### Card scale (S5, decision 3)

Card = 70 + 10 × (standard deviations above the role average, league-adjusted), clipped 40–99, over all 442 major-league players (10+ games for the reference pool). 70 = average major-league player. The card is display only; the sim will use the fitted effects. All cards: `player_cards_S5.csv`; the scales that were turned down (S0–S4): `card_scales.csv`.

S5 Overall for the app's 80 players (2026 major-league games):

| Team | Top | Jungle | Mid | ADC | Support |
|---|---|---|---|---|---|
| GEN | Kiin 93 | Canyon 90 | Chovy 94 | Ruler 89 | Duro 90 |
| HLE | Zeus 87 | Kanavi 90 | Zeka 85 | Gumayusi 85 | Delight 82 |
| T1 | Doran 85 | Oner 81 | Faker 72 | Peyz 94 | Keria 92 |
| DK | Siwoo 85 | Lucid 85 | ShowMaker 84 | Smash 92 | Career 87 |
| BLG | Bin 89 | Xun 86 | Knight 99 | Viper 87 | ON 82 |
| IG | TheShy 85 | Wei 85 | Rookie 89 | JiaQi 92 | Meiko 68 |
| TES | 369 77 | Tian 76 | Creme 86 | JackeyLove 74 | Zhuo 73 |
| AL | Breathe 71 | Tarzan 84 | Shanks 80 | Hope 77 | Kael 87 |
| G2 | BrokenBlade 73 | SkewMond 77 | Caps 83 | Hans Sama 77 | Labrov 61 |
| KC | Canna 79 | Yike 73 | kyeahoo 76 | Caliste 78 | Busio 70 |
| LYON | Dhokla 62 | Inspired 67 | Saint 77 | Berserker 75 | Isles 73 |
| TL | Morgan 79 | Josedeodo 76 | Quid 73 | Yeon 80 | CoreJJ 70 |
| MKOI | Myrwn 63 | Elyoya 71 | Jojopyun 70 | Supa 73 | Alvaro 77 |
| LOS | Zest 85 | Curse 60 | Feisty 74 | Duduhh 67 | Ackerman 77 |
| TSW | Pun 67 | Hizto 75 | Dire 64 | Eddie 74 | Bie 75 |
| CFO | Rest 59 | Shad0w 68 | Pout 63 | Doggo 65 | Kino 65 |

Faker's S5 skills: Laning 73, Map impact 67, Damage 71, Overall 72. The 2026 file has him behind in lane at 15 on average (−129 gold, 9th of 10 LCK mids with 30+ games) with the lowest damage share and kill participation of those 10, while T1 won 63% (`research/sim-plan.md`, follow-up of 3 Nov).

---

## 5. Experience test (not adopted)

Career facts before 2026 from Leaguepedia's data export (read 3 Nov): titles, Worlds titles, international games, Worlds appearances, for all 442 players (`player_experience_pre2026.csv`). Added on top of teams + league-adjusted players:

- Every version points the right way: about +0.6 win-% per title of difference, +2.6 per veteran.
- All of them made the July–August tuning games worse, and gains on later sets were small and inconsistent.
- Decision (Luke, 3 Nov): not in win odds for now; **re-test after the Worlds knockouts**.

The per-version numbers were printed by `exptest.py`, not saved to a results file.

Note: `research/sim1/experience_progress.md` still lists player matching as "not done"; that file is a mid-session progress note and was not updated after the matching finished (the CSV has all 442 players).

---

## 6. Sources checked

- **Leaguepedia Worlds Main Event player stats** (read 3 Nov, saved as `research/sim1/lp_players.json`): all 80 Worlds players' Swiss stats match the file exactly.
- **gol.gg S16 season stats** (read 3 Nov, `gol_players.json`): agreement with the file's season numbers as recorded in `research/sim1/README.md`: damage share and damage per minute 1.000, kill participation 0.998, gold at 15 0.975, CS at 15 0.84, XP at 15 0.73. The comparison code was not saved, so which agreement measure these are is not checked. The lower CS and XP figures were not followed up.
- **ID lookup:** 16 of 16 teams and 80 of 80 players matched to the app's IDs (`id_teams.csv`, `id_players.csv`).

---

## 7. Against the plan's test targets

| Check | Target | Session 1 result |
|---|---|---|
| Win odds | Better than the current sim (0.68–0.70 at Worlds) and a coin flip (0.693) | **Met:** 0.639 v 0.679 on the same 51 Swiss games; 0.646 from 1 Sep |
| Calibration | Each band within about 5 points | **Met from 1 Sep** for bands with 37+ games; **not met at Worlds** (60–80% bands 10–12 points over, small samples) |
| Accuracy | About 60–65% at Worlds level | 61.6–63.0% at Worlds; 32 of 51 Swiss |
| Length, kills, objectives, kill share, POG | Simulated v real | Not part of session 1 (sessions 3 and 4) |

---

## 8. What feeds the next sessions

- **Session 2 (champions and comps):** measure champion and matchup effects after taking out the team and player ratings here, so a strong team's picks don't look better than they are. Champion pools as a player-rating factor (judge players against others on similar champions) starts here, including Faker's.
- **Session 3 (game-state sim):** the sim's overall win odds must match this model.
- **Session 4 (app):** cards switch to S5 and the fitted Overall; Power Rankings use the team ratings; draft review "Before draft" uses this model.

---

## 9. Open items for Luke

1. **Faker (open requirement, 3 Nov):** S5 Overall 72. To be resolved through session 2's champion-pool context, the experience re-test after the knockouts, and how team "wins beyond stats" is shared, not by setting a number.
2. **Four skills with no weight** (top Teamfight, top steadiness, mid Map impact, ADC Damage): keep them on cards as descriptive skills, or swap in a tested alternative (e.g. mid "kills + assists by 15")? The test can't tell them apart, so this is a display choice.
3. **"Wins beyond stats" as a team stat:** the idea is agreed (decision 3 note); how it is computed and shown is not decided. `deeper.py` looked at it, but its output was not saved.
4. **S5 has no saved script:** the S5 cards were computed inline in the earlier session and saved as `player_cards_S5.csv`. Before session 4 the S5 step should be added to `scales.py` so it can be re-run.
5. **Knockouts:** add each knockout match day as a Worlds test row (and re-test experience after the final).
