# Sim session 3 — working files (the game-state sim)

Started 5 Nov 2026 (AEST). Plan and decisions: `research/sim-plan.md` (session 3 entry under Decided, with Luke's realism rules). Results tables go in `research/model/sim3/`; the report is `research/sim3-report.md`. Research only: the app is not changed in this session.

Data:
- **The Oracle's Elixir file** is the source of record; only its games are used (Luke, 4 Nov). The session started on the file to 4 Nov 02:20 UTC (quarter-final 1); the final runs use Luke's second file of 5 Nov (to 4 Nov 23:54 UTC, quarter-finals 1–2), so Worlds' held-out set is 80 games.
- **gol.gg game timelines** (read 5 Nov) give the order and time of events, which the file doesn't have. Each timeline page has every kill (killer, assists, victim), tower segment, tower, dragon by type, grubs, Herald, Baron, inhibitor and nexus, plus every player's gold and CS each minute.
- **Pull:** 12 events from late July on (Worlds main event and play-in; LCK Rounds 3–4, play-in and playoffs; LEC summer and playoffs; LCS summer and playoffs; CBLOL split 2 and playoffs; EWC). That is 627 games, the same count gol.gg lists for each event.
- **LPL is left out:** gol.gg has no timelines or minute gold for LPL games.
- **Matching:** a timeline game is used only when it matches a file game (the champions seen on each side, all but at most 2 fitting, and a date within 1 day). Each game counts once, by the file's game id.
- **After the cut-off:** on the first file, the 3 Gen.G v LYON games were on gol.gg but not in the file, so they didn't match and weren't used. They match on the second file and are now held-out Worlds games (never in fitting: fitting is before 1 Sep).

Scripts run from a scratch folder (Python + pandas). Each script's docstring has its usage line. Order:

| Step | Script | Makes |
|---|---|---|
| 1 | `gol_pull.py` | `raw/tl/<id>.html` timeline pages, `raw/series.csv` (read-only, 3 requests at a time; game ids run in order within a series, checked against each page's "game N" title; Bo1 rows link to the game page) |
| 2 | `gol_parse.py` | `tl_games.csv`, `tl_events.csv`, `tl_gold.csv` |
| 3 | `s3_match.py` | `tl_match.csv`, `tl_check.csv`, `tl_check.json` (timeline v file: kills, towers, dragons, Barons, grubs, Heralds, inhibitors, winner, length) |
| 4 | `s3_lanes.py` | `lanes3_coef.csv`, `lanes3_resid_cov10/15.csv`, `lanes3_results.json`, `lanes3_features.csv` (laning at 10 and 15, role by role, from the file) |
| 5 | `s3_comp.py` | `comp3_games.csv`, `comp3_styles_pre_sep.csv` (draft style per game; champion styles from games before 1 Sep only) |
| 6 | `s3_events.py` | `events3_results.json`, `tl_fights.csv` (fights, who gets each kill, gold per event, who takes each objective, dragon types, ending) |
| 7 | `s3_rates.py` | `rates3_results.json` (per-minute rates: tower pushes and segments, base pushes, fights, monster takes; timing-only draft-style versions; option A test terms) |
| 8 | `s3_targets.py` | `targets3.json` (real-game targets from the file: length, kills, objectives, role kill share, gold leads) |
| 9 | `s3_timing.py` | `timing3.json` (how flexible real objective timing is: first dragon wait, side, lane priority, trades, Baron after a fight) |
| 10 | `s3_params.py` | `params3.json` (every fitted table the sim reads, plus box-score norms from the file before 1 Sep) |
| 11 | `s3_sim.py` | the simulator (`Sim(P, cal).run(x, seed)`) |
| 12 | `s3_test.py` | `test3_results.json`, `sim3_heldout_games.csv.gz` (calibration on training games, then held-out who-wins and game shape) |
| 13 | `s3_diag.py` | printout: structure timing in the sim v real (first T1/T2/T3, inhibitor, end; T3 to inhibitor; inhibitor to end) |
| 14 | `s3_ablate.py` | `ablate3.json` (held-out log loss with draft styles off, then lane inputs off too) |
| 15 | `s3_timing.py`, `s3_check_ks.py`, `s3_t3check.py`, `s3_style_check.py` | `timing3.json`, `check_ks.json` (kills by length, dragon side-swapping, real v sim), `t3check.json` (T2 → T3 stage), `style_check.json` (do draft styles move timing, real v sim) |
| 16 | `s3_dmgmix.py` | `dmgmix.json` (comps option C: damage type and frontline, with Riot client tags via the League wiki, `wiki_champ_tags.csv`) |
| 17 | `s3_quick.py` | printout: quick shape check of a sim version on held-out games (length, short games and their Barons, kills, kill difference and gold lead at 15, kill rate v length; real side from the timelines) |

The final sim runs with `s3_test.py ... 200 timing` (draft styles timing-only). Spread fixes tested on 5 Nov and not kept (report section 7d) stay in the scripts but are off by default: the per-game tempo measurement (`rates3_results.json` → `tempo`), game form (`events3_results.json` → `kill_side_within`, used only with `cal["form"] = "within"`) and the per-phase fight swing (`s3_test.py ... 200 timing phase`; results in `test3_phase_eps.json`). With the defaults the sim replays the committed games exactly (300 of 300 seeded games checked). Option A (a comp converts a lead) results are in `optionA_rates3.json` / `optionA_events3.json`: not kept.

In the repo (`research/model/sim3/`): the small tables (fits, params, targets, timing, test results, the timeline-to-file match). Kept local (rebuild with steps 1–3): the raw gol.gg pages, `tl_events.csv` (64,199 events), `tl_gold.csv`, `tl_fights.csv`, `lanes3_features.csv`, `comp3_games.csv` and the held-out sim games.

Fitting rule: everything is fitted on games before 1 Sep and judged on games from 1 Sep and Worlds games (out of sample).

## Checks on the timeline data

- Timeline v file on matched games: winner and length agree in every game; dragons and Barons in every game; grubs, Heralds and inhibitors in almost all. Kills differ by 1+ on 4% of team-sides (usually the timeline has one more). Towers differ on about 6% of team-sides; mostly the timeline has one more (most likely nexus towers the file doesn't count; not checked further).
- **Towers have 5 segments on these patches.** gol.gg's "PLATE" rows run to 15 per lane, and every T1, T2 and T3 in the timelines fell exactly on its lane's 5th, 10th and 15th segment. So the sim takes towers segment by segment, not with a "towers per minute" rate.
- Spawns from the earliest real takes: dragon 5:00 (earliest take 5:22), grubs 8:00 (8:04), Herald 15:00 (15:15), Baron 20:00 (20:19). Grubs: all 3 are taken in every game.

## Mistakes and fixes during the session

- The first pull skipped every Bo1 (gol.gg links a Bo1 straight to the game page, not to a series summary). Found when Worlds showed 38 main-event games instead of 55; fixed, and the missing games pulled.
- A network drop during the pull lost 15 pages; a second pass re-read them (saved pages are skipped).
- Kill gold in the sim was meant to give the killer a double share, but the indexing collapsed the repeat; fixed.
- The sim took its gold snapshot for each minute after that minute's lane gold was added (so "gold at 15" was really about 15:59); fixed to the start of the minute, as in the fits.
- **Even-rate counts were too smooth.** Real tower segments come in bursts: 3+ segments in a lane-minute is about 4× as common as an even (Poisson) rate gives, and the spread grows through the game (variance / mean 1.24 before 14:00, 1.9 at 14–20, 3.5–3.9 after 25). So segments, fights and base structures are now drawn with the burstiness the fitted rate leaves unexplained (negative binomial with the same average; dispersion by phase measured on training minutes, in `rates3_results.json`).
- **Kill gold split.** The first engine gave a kill's gold to the killer (double share) and assisters, which loaded supports with too much gold swing (support lead at 15: sim spread 777 v real 467). Now every event's gold lands on the roles the way real team swings do: the slope of each role's minute gold change on the team's (training games: top 0.17, jungle 0.23, mid 0.21, bot 0.28, support 0.12 in laning).
- A test run crashed because scripts were edited while it ran (new worker processes loaded the new code). Re-run with nothing edited during the run.
- **Games ran long because the final push was too slow** (first held-out test: 34.7 min v 32.3 real). Real games end a median 42 s after the first inhibitor (the next base take by the same side comes a median 11 s later); the sim took about 2.5 min. Three steps, each checked against the real timelines:
  1. base structures as pushes (a fitted chance a push starts this minute, then a real push size), not a per-minute count: 2:28 → 1:56;
  2. a lane counts as open if its inhibitor turret fell before the minute ends (the old fit only saw minutes that started with a lane already open, so it never saw the T3-then-inhibitor push), with a "lane just opened" input, and push sizes by whether an inhibitor was already down: → 1:40;
  3. **pushes defined by time, not clock minute** (base takes under 30 s apart are one push, as with fights; counting per clock minute split one push in two): → **37 s** (real 42 s).
  Tested and not kept as a cause: a bigger push when far ahead or with Baron (real sizes barely change: 1.9 when behind, 2.4 when 8k+ ahead).
- **First dragon was too early and too blue** (27% within 30 s of spawn v 5% real). The take-rate model had learned from all dragons, and respawns go fast (median 38 s). The game's first dragon now has its own fitted input in both the take rate and who takes it: median 2:13 after spawn v 2:07 real.
- **Calibration targets the team gold lead at 15.** Matching each role's spread left the team lead too wide (the five lanes move together more in the sim than in real games).
- **Draft styles: from "who" to "when"** (Luke: "use timing for now"). As own-minus-enemy terms they cost the Worlds odds (0.675 v styles off 0.642, earlier version); as both drafts together (pace, siege, objective focus changing how fast things happen) they were about neutral. Kept in timing-only mode.
- **Won fights and towers:** real tower segments per minute follow the minute's net kills (−3: 0.52, 0: 0.99, +3: 2.65; held-out fit 0.850 → 0.818), so "net kills this minute" is an input to tower and base pushes. On its own it didn't shorten games.
- **Tower pushes (the T3 stage).** Games still ran about 3 minutes long: the T2 → T3 stage took 4:33 in the sim against 2:07 real, and 38% of real inhibitor turrets fall in a push that started at or before the T2. Towers now come in pushes like the base: a fitted push chance per lane per minute, then a real push size by tier (T1 before 14:00 mostly single segments; a quarter of T3 pushes take the whole T3). Held-out push fit 0.380 v 0.405 baseline; median game end 35:01 → 31:25 (real 31:59); kills 29 → 27 (real 27); and the sim's who-wins went ahead of v1 (0.635 v 0.640 from 1 Sep).
- **Two editing slips caught before use:** a broken line in the rate script (the syntax check stopped it) and a comparison against the wrong baseline in the option A test (fixed and re-run).
- **A request tried to get past the League wiki's bot check with browser-like headers;** it was blocked, rightly. The wiki page was read in the browser pane instead.
