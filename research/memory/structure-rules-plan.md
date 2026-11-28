# v56 plan: structure rules (+ the outside-window model) — built as v56 (28 Nov)

28 Nov 2026 AEST. Status: **built as v56** (Luke: "Yes, build v56"), not committed; results in `research/model/memory/m27_app_check.json` and
SESSION_NOTES (Update 28 Nov). Changes made in the build beyond this plan: the window block keeps m21's tables at its top level and puts
the refits under `outside` (so "off" replays v55); an inhibitor needs its lane's T3 down by that second (`t3T`); the rules read a full
Nexus-tower history `nxHist`, because the minute-start respawn prunes `nxDown` while the push clock can place a take before the minute.

## The bug (traced this session)

A Nexus tower can fall when no inhibitor is down at that second. That shouldn't be possible: a Nexus tower can only be hit once an
inhibitor is down. In 72 Worlds drafts × 50 seeds, this happens in 12.6% of v55 games (553 Nexus towers) and 16.1% of v54 games
(939). Two causes:

1. **Take times inside a window go backwards** (`js/sim-engine.js:275`, `let tk = ta + quant(q, rng.random())`). The take-time
   quantiles (`FW.take_q`) include negative values, which is real for the first take (real takes can land before the fight's last kill).
   After a take, though, the next draw can land before it. m21's research replay clamps this (`extra.append((max(ta, tk), ...))`);
   the app doesn't.
2. **The per-minute base push checks state at the minute's start** (`sim-engine.js:506–545`). `down`, `upInh` and the Nexus-tower
   respawns are read at `t0`, but the takes land later in the minute (`TT()` adds real base gaps). If an inhibitor respawns, or a
   Nexus tower comes back, between `t0` and the take, the take still happens. Separately, `fwAvail` (line 235) counts an inhibitor as
   down while `inhibBack > t`, which includes one whose fall time is still in the future.

## Worked examples

**Game 2 of the T1 v TES export** (seed 3187772510790416; T1 Jayce / Jarvan IV / Viktor / Xayah / Poppy v TES K'Sante / Pantheon /
Syndra / Kalista / Seraphine; replayed: red win, 2148 s, 11–22, matches the export).
- TES won the fight with t0 2112 and last kill at 2117 (35:17). Alive then: 5 TES, 0 T1. Window took [inhib, nxt, nxt, nexus].
- Step 0: an inhibitor at 35:22 (2122), so `ta` = 2122.
- Step 1: a Nexus tower. `tk` = 2122 + a draw from `take_q.nxt["ahead 3+"]` landed about 13 s early, at 35:09. That is before the
  inhibitor (cause 1).
- **With part 1:** step 1's draw comes only from the part of the same quantile table at or after 0 s, so the Nexus tower lands at or
  after 35:22. The exact second isn't checked yet; the new draw uses a rescaled random number, so it will differ.

**WORLDS_LIVE.games[0], seed index 0, window off** (v54 behaviour).
- The mid inhibitor fell at 33:00, which sets its respawn to 38:00.
- In minute 37 (`t0` = 2220) the base push read the mid inhibitor as down (2280 > 2220). The takes it then placed with `pt +=` base
  gaps landed at 38:10 and 38:18, both after the respawn (cause 2).
- **With part 2:** at 38:10 the helper reports no inhibitor down, so the Nexus tower can't be hit. What happens next depends on
  decision B below: the push stops, or the outside-window model chooses the next step.

## Changes

One setting, `structure_rules: "v1"`, on by default (Luke: new versions go into the app switched on). Setting it to `"off"` replays
v55 exactly.

**Part 1: take times keep their order** (`fwRun`, line 275).
- For step j ≥ 1, draw the take time from the part of the same quantile table at or after `ta` (the previous take or the last kill).
  It is one draw, rescaled: `u' = F(lo) + u·(1 − F(lo))`, where `F(lo)` is the table's share below 0 s.
- No number is hand-set: the times are still the real ones, just limited to times after the previous take.
- Step 0 is unchanged (real first takes can come before the last kill).

**Part 2: rules that check the second a structure falls.**
- New helpers in `Sim.run`:
  - `inhibFall[s][li]`: the fall time, recorded next to `inhibBack`.
  - `inhibDown(s, li, t)`: `inhibFall ≤ t < inhibBack`.
  - `nxUp(s, t)`: 2 minus the Nexus towers with `x ≤ t < x + NEXUS_TURRET_BACK` (from `nxDown`).
- `fwAvail` (lines 233–237) uses these helpers instead of `inhibBack > t` and the `nxTowers` counter.
- Base push (lines 511–545): each step's take time is drawn first (`TT()`), then the rules are checked at that second:
  - a Nexus tower only if an inhibitor is down then;
  - the Nexus only if an inhibitor is down and no Nexus tower is up then;
  - an inhibitor only if it is up then.
  If the drawn step can't be taken at that second, see decision B.
- `nxTowers` stays as the running count for tallies; gating reads the helpers instead.

**Part 3: the outside-window model** (only if m25 passes; see decision A).
- `SIM_TABLES.window` gains an `outside` block: the stage 1 shifts (21 terms) and stage 2 shifts (24 terms), fitted on the app copy
  (games before 10 Nov).
- `fwRun(w, tf, t1)` becomes `fwRun(w, tf, t1, outside, j0)`:
  - stage 1: `x1 += outside · (the same terms × FW.outside.stage1)`;
  - stage 2: `u += outside · (the same terms × FW.outside.stage2)`.
  The linear part moves into one function called with either coefficient set, so the window path is unchanged.
- Take times stay m21's window quantiles. They are not refitted outside windows (m23 / m25 use the same quantiles).

## How the joint model would plug into the engine (read-only map)

| Where | Today (v55) | Change |
|---|---|---|
| `sim-engine.js:187` | `FW` = `SIM_TABLES.window` when `fight_window` is v1 | add `SR` = `structure_rules` v1 flag; `FWO` = `FW.outside` when present |
| `:233–237` `fwAvail` | inhibitor down = `inhibBack > t`; Nexus towers from the counter | `inhibDown` / `nxUp` at `t` (part 2) |
| `:252` `fwTake` inhib | sets `inhibBack` | also sets `inhibFall` |
| `:254`, `:533` nxt takes | push to `nxDown`, `nxTowers--` | unchanged (`nxUp` reads `nxDown`) |
| `:257–283` `fwRun` | window model only; step from 0 | `outside`, `j0` arguments; shift terms; part 1 draw |
| `:414` after a won fight | `fwRun(w, tf, lastKT)` | unchanged (outside = 0) |
| `:506` Nexus-tower respawn | at the minute's start | kept for the counter; rules read `nxUp` at the take second |
| `:526–545` base push steps | `npush` steps, state at `t0` | part 2 checks at the take second; then decision B |
| `research/memory/m26_…` (new) | none | fits the joint model on the app copy and writes `SIM_TABLES.window.outside` (like `m21 --app`) |
| `index.html` | `?v=55` | `?v=56` on all 12 tags |

## Decisions for Luke (asked before building)

**A. Which "what next?" model outside windows.** **Decided (Luke, 28 Nov): the fixed joint model** (m25: window terms held at m21's, outside shifts on take-or-reset; the stage-2 shifts' ridge came out at 10,000, so which-option is the window model's; outside replay closeness 0.064 / 0.052 v window 0.078 / 0.067; known overshoot on Nexus towers and the Nexus from 1 Sep). This waits on m25's replay: the window model (today), the free joint model, or the
fixed joint model (window steps identical to v55 by construction).

**B. Where the outside model runs.** **Decided (Luke, 28 Nov): B2.**
1. *Only when a step can't be taken.* The base push keeps its `npush` draws. When a drawn step fails a part 2 rule, the outside model
   picks what happens from that second, or a reset. This is a small change, but it uses the model only in the states left after a
   respawn, which is a narrower set than the one tested.
2. *Every base structure outside a window starts an outside chain.* The first structure still comes from today's per-minute draw (or a
   T3 from the segment draws). Every later step is the outside model's choice, as in the rows m23 / m25 fitted and replayed. This
   matches what was tested, but it replaces `npush` beyond the first step and will move inhibitor counts, Nexus-tower counts and game
   length. My pick, if m25 passes.

**C. Double counting under B2.** **Decided (Luke, 28 Nov): option 1, refit the tables.** Outside chains can take dragon or baron, and those minutes still have per-minute monster and base
draws, which were fitted including them. m21 solved the same problem for windows by refitting those tables without window minutes. For
outside chains, the options are:
1. refit the base push and monster tables without the outside-chain minutes too (in m26; the same method as m21);
2. keep outside chains to base structures only.
Not checked yet: how often real outside chains take a monster. m23's counts (all splits): dragon 17, baron 7, elder 2 of 528 steps.

*Prepared for option 1 (28 Nov, not run):* `research/memory/m26_outside_tables.py --model free|fixed [--app]`. It won't run until a
model is named. It refits the joint model on both copies, and refits the base push and monsters without window minutes and
outside-chain minutes, keeping the app's order inside a minute:
- **Base push:** leave out the chain's minutes after the anchor's minute, and also a T3 anchor's own minute. An inhibitor or
  Nexus-tower anchor's minute stays in, because it is the push that starts the chain.
- **Monsters:** leave out the minutes after the anchor's minute.
- **Port check:** as m21. `--app` refuses to write if the check fails.

The engine must skip the same minutes. An outside chain adds its minutes after the anchor's minute to `winM[s]` and `winAny` (as
`fwRun` does for windows), and a T3 anchor also adds its own minute to `winM[s]`. Without this, the tables and the engine would
disagree.

## Drafts (28 Nov, not in the app)

- **Parts 1–2:** `research/local/memory/sim-engine_v56draft.js`. The diff against `js/sim-engine.js` is
  `research/local/memory/v56draft_parts12.diff`, and the v55 snapshot is `research/local/memory/sim-engine_v55.js`.
  - **Setting:** `SR` (`structure_rules`, default "v1", needs game memory).
  - **New pieces:** `qcdf` (the inverse of `quant`), `inhibFall`, and `inhibDown` / `nxStanding` / `nxLeft`.
  - **fwAvail:** reads those under SR.
  - **fwRun:** after a take, draws take times at or after it (one draw, rescaled). It checks that the structure is hittable at the
    take second, otherwise the window resets, and re-checks the Nexus after the event clock moves it.
  - **Base push:** under SR a separate loop draws the take time first, then applies the rules at that second. If nothing is hittable,
    the push stops; part 3 replaces this.
  - **Off path:** "off" keeps the old loop and the same random draws.
  - **Not yet checked:** not run (no Node; it gets checked in a page tab).
- **Check script:** `research/memory/m27_app_check.js`.
  - Loads the draft as `window.M27_V56` before the build.
  - Runs the replay fingerprints, rule-break counts from the play-by-play, shape v56 v v55, and both worked examples.
  - **Not yet checked:** that the game 2 champion names match the app's spelling. The script's own first line checks it, because v55
    has to reproduce the export.

## Checks before reporting done

- **Replay fingerprints:** `structure_rules: "off"` reproduces v55's fingerprints; with `fight_window` off as well, it gives v54's
  cb7225e9 / c993b12b.
- **Rule-break counts** over 72 Worlds drafts × 50 seeds should all be 0: Nexus towers with no inhibitor down, the Nexus with a Nexus
  tower up, an inhibitor taken while already down, take times going backwards in a window.
- **Game shape:** v56 v v55 v real for game length, inhibitors, Nexus towers and base structures per game, and the share of games
  ending inside a window.
- **Both worked examples** re-traced with the setting on.
- **Page check** in a new tab: desktop and 375 px, console clean, a series played, export read. Then cleanup.
