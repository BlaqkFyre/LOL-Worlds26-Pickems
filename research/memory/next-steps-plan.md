# Game memory, next steps: what v51's play-test showed and the agreed plan (21 Nov 2026 AEST)

The plan for the next session(s). Agreed with Luke on 21 Nov after he play-tested v51 (a Bo5, LYON 3–1 LOS, and three games that turned
out to be v50 from a cached page). Background: `game-memory-report.md` (what real games do after a fight), `final-g3-positions.md`
(pick-offs, side-laners, objectives), the v51 entry in `SESSION_NOTES.md`.

## Where the app is (v51, commit `d1d23f3`)

`js/sim-engine.js` with `cal.game_memory` on: death timers (official respawn), nexus turrets respawn after 3 min, the Nexus falls only
after a won fight and before the losers are back, structures spaced by real gaps, no same-second stacks. `cal.game_memory = "off"`
replays v50 exactly. The research sim (`research/sim3/s3_sim.py`) does **not** have these rules yet. Not calibrated: on the final game 4
draft (1,000 seeds) games ran long (45+ min 24.7% against a real 4.3%) and kills high (33 a game against about 26).

## What the play-test showed (LYON v LOS Bo5, v51)

| Game | What happened | Problem |
|---|---|---|
| 1 (LOS, 36:14) | LYON lost a fight at 35:39 (two dead), then took the mid inhibitor and both nexus turrets 5 s later | The side that just lost a fight pushes the enemy base |
| 2 (LYON, 38:06) | LYON opened every inhibitor and both nexus turrets by 33:42 and had Baron, but no fight came for 4 minutes; the turrets respawned; LYON ended after a 5–1 at 37:46 | Nothing pushes a fight when a base is open (the fight count was fitted without this state) |
| 3 (LYON, 26:11) | At 19:33–19:38, with all 10 alive and no kill since 15:22 (LOS +1.7k at 15), LYON took a tower, an inhibitor tower, the inhibitor and both nexus turrets, 1 s apart | The base push ignores the map state; pushes that start behind already-placed events chain at 1 s |
| 4 (LYON, 43:11) | Nami (support) got four kills in one teamfight, all "solo"; LOS won 4–1 at 37:11 and 2–0 at 39:16 and took nothing before LYON respawned | Kill and assist credit ignore fight size; won fights take too little late (the sim takes about half the real response) |
| Series | Player of the Game went to junglers 3 of 4; Saint had the best average rating (5.9) and best game (9.8) but no POG. 129 kills in 4 games (32 a game) | The same jungle skew as the final replay; kills high |

What worked: inhibitors and nexus turrets respawned and stalled ends; the Nexus fell inside the window after a won fight (20–49 s after
the last kill); base structures in a push came real gaps apart.

## Luke's decisions (21 Nov)

1. **Fix kill and assist credit in fights first**, then re-check Player of the Game by role ("perhaps that recognises mid/ADC a bit more"),
   before touching the rating formula.
2. **Keep the per-minute base push** that was just put in; don't replace it and **don't add a block rule**. Instead it learns the game
   state from real games: "teams with e.g. 4 dead players don't base push while their base is being attacked; surely code can consider
   this in the state min-by-min updates." The behaviour must come out of the fit, not be set.

## The plan (each step stops for Luke's OK)

All fitting on games before 1 Sep (the gol.gg timelines: 411 games); the 98-game Worlds feed is a check only (Worlds are test games).
Scripts go through `research/lib` with run records; report tables generated from results.

**1. Kill and assist credit by fight size (first).**
- Measure on the timelines (each kill's killer, victim and assisting champions; roles from the Oracle's Elixir file; a fight = kills
  less than 20 s apart): killer role, number of assists and solo share, by fight size and phase.
- Check the same on the feed (Worlds).
- Fit the sim's killer and assist choice on fight size; test; then re-check Player of the Game by role (and damage share against kills:
  game 2's Nami had 5 kills and 3% damage).

**2. The per-minute base push learns the game state.**
- Keep the push model and all its inputs. Add, fitted on real minutes: each team's players alive (from kills and the official respawn
  timer, role level from XP by minute as in `SIM_TABLES.memory`), whether the team's own base is under attack (its base structures falling
  this minute or the last), and who won the last fight and how long ago.
- Expected (to be shown, not set): a team with most players dead doesn't push; the side that just lost a fight doesn't take inhibitors;
  a no-fight base collapse at 19 minutes becomes rare.
- Possibly the lane-tower push too, if alive counts matter there in the data.
- Check on the feed (exact alive counts each second).

**3. Open-base fights and push timing.**
- Measure the time from the second nexus turret down to the Nexus (timelines label nexus turrets), whether a fight comes first, how often
  turrets respawn before the end; fit the fight chance with an open base as an input.
- Start pushes from a real time so there are no 1-second chains.

**4. Calibrate and test** with everything in (the research sim gets v51's rules first, as an option): fit the overall strength and the
fight count; the 1,000-sim who-wins tests (Worlds day by day, fixed and walk-forward; must stay inside the noise band); shape checks
against real games (kills a game, length and 45+/50+ shares, Nexus gap, same-second events, what a fight's winner takes, picks v big
fights, Player of the Game by role); scorecard artifact for Luke.

**5. Port to the app (v52)**: JS engine and tables, averages checked against the research sim, browser checks; Luke play-tests.
Draft Clash only if Luke wants the same kill-credit tables there (its structures and picks are done, v51 commit).

Rough size (not measured): step 1 about a session, steps 2–3 about a session, step 4 about a session, step 5 about half.
