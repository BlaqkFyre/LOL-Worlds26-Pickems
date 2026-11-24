# research/memory: game memory measurements (17 Nov 2026)

What real games do after a fight, measured from the whole-game lolesports feed of the 98 Worlds games (`lib.feed.full()`), with gol.gg
timelines as a second check. Report: `game-memory-report.md`. Results go to `research/model/memory/`; run records to `research/runs/`.
Run from the repo root, in this order (each takes seconds, except m5):

| Script | Step | What it does |
|---|---|---|
| `m0_clock.py` | 1 | Pause-cutting rules against the file's lengths and gol.gg's kill times (the rule used is `lib.feed.clock`) |
| `m1_fights.py` | 2–3 | Deaths, fights at death gaps of 5–45 s, gap histogram, gold v kills winner; writes `fights_G<gap>.csv` |
| `m2_responses.py` | 4 | What each side takes until the losers respawn; baseline rates outside the windows; writes `responses.csv` |
| `m3_state.py` | 5 | Snowball (fit with a bootstrap over games), dead time by role, health and numbers going in |
| `m4_timelines.py` | 6 | The step 4–5 responses on the 640 gol.gg timelines (kills winner) |
| `m5_sim_compare.py` | 7 | The same reading of the current research sim (1,000 sims a game on 94 Worlds games, about an hour) |
| `app_sim_check.js` | 7 | The app sim (v50) on the final game 4 draft, pasted into a locally served app tab; results copied to `app_sim_check.json` |
| `m6_fight_kinds.py` | 9 | The game 3 positioning leads tested on the 98 games: fight kind by phase and gold gap, pick victims by role, vision, fights before objectives, late joiners, towers with no fight |
| `m7_kill_credit.py` | next 1a | Kill and assist credit by fight size and phase (killer role, assists, solo kills, one player's kills in a fight, side B), on the timelines (training, from 1 Sep, Worlds) and the Worlds feed; executions left out; writes `m7_kill_credit.json` |
| `m7_sim_check.js` | next 1a | The same tables from the v51 app sim (72 Worlds drafts x 100 seeds), pasted into a locally served app tab; results copied to `m7_sim_check.json`. Since 24 Nov `window.M7_CAL` adds settings (e.g. `{kill_credit: "v2"}`) and it reports Player of the Game by role and each draft's blue win share |
| `m8_credit_diag.py` | next 1b-0 | Real fights replayed through the v51 fight draws one part at a time (assists only; + killer and victim; + who is in the fight), plus assists by players already killed in the fight and joiners; writes `m8_credit_diag.json` |
| `m9_fit_credit.py` | next 1b-1 | Fits kill credit v2: who is in a fight (kills groups 1, 2, 3-4, 5+), assists (players killed earlier in the fight can assist; fight size, side B), who wins each kill (+ players alive as steps); research copy before 1 Sep with held-out log loss and replays (`m9_fit_credit.json`), app copy to 10 Nov written to `research/local/sim4/app_params` and the `SIM_TABLES.credit` block of `js/sim-tables.js`. The app check (v51 v v2, 7,200 games) is `m9_app_check.json` |
| `next-steps-plan.md` | – | **The agreed plan for the next sessions** (21 Nov): v51 play-test findings, Luke's decisions, steps 1–5 |
| `final-g3-positions.md` | – | Worlds final game 3 read by hand from the broadcast minimap and the feed: who was in each fight and where, and leads for the sim |
| `build_memory_tables.py` | – | Writes the `SIM_TABLES.memory` block at the end of `js/sim-tables.js` (role XP for death timers; real gaps from the last kill to the Nexus, between structures and between kills; timelines before 1 Sep) |
| `common.py` | – | Shared code: deaths with measured respawns and the official timer, fights, the gold winner, the event-list reader |
| `report_tables.py` | – | Report tables from the result files (`python -I research/lib/report.py research/memory/game-memory-report.md research/memory/report_tables.py`) |
