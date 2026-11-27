# Push continuation after a won fight (plan, 27 Nov 2026 AEST; not built)

Follows `base-push-plan.md`. Part B of that plan (v55, uncommitted) made games slightly longer: the fitted per-minute draw learns that
a new push rarely starts in a minute that begins with the Nexus exposed, and the sim restarts the push every minute
(`research/model/memory/m18_app_check.json`). Luke (27 Nov): "Plan a push continuation". Each part below stops for Luke's OK.

## What changes from Luke's 21 Nov rule

The rule was: keep the per-minute base push and all its inputs, add no block rule, the behaviour comes out of the fit. This plan **keeps
the per-minute base push and all its inputs**. It adds one more fitted step: after a won fight with a lane open, the winner's push goes
structure by structure, and each next structure is a fitted chance. No outcome is set by hand. The real share of 0-left won fights that
end in the Nexus (94%, all 640 timelines) is the test, not a setting.

## The measured problem (v55 v v54 v real; 72 Worlds drafts x 100 large seeds; real from `m16_nexus_push.json`, all 640 timelines)

| Won fight, structures left to the Nexus at its start | v54 takes the Nexus | v55 | Real |
|---|---|---|---|
| 0 | 40% | 30% | 94% |
| 1 | 34% | 31% | 84% |
| 2 | 26% | 29% | 56% |
| 3 | 18% | 18% | 30% |

Game length median: v54 39.0, v55 39.5, real 32.2 min. 45+ min: 28.0%, 30.1%, real 2.8%.

## The model

**A push after a won fight** (the fight's winner has a lane open at the fight's start, as `m16_nexus_push.py` counts it):

1. Step 0 starts at the fight's last kill. Each step asks: **does the push take the next base structure?** (inhibitor, nexus tower or the Nexus,
   whichever the engine's existing order gives next).
2. If yes, the structure falls at a real time: the first one from the last kill (`SIM_TABLES.push.first_base_q`, as now), later ones its
   pair's real gap (the v2 tables), the Nexus from the last kill by structures left at the fight's start (the v2 table). Then the next step.
3. If no, the push stops. The Nexus still needs the losers not to be all back (the existing check stays).

**Each step's inputs** (measured at the step's moment: the last kill for step 0, else the previous structure's time):
- structures left to the Nexus now (0–3);
- enemies dead now, own dead now (each death lasts its official timer, as m17);
- seconds since the fight's last kill;
- the step number (0, 1, 2+);
- gold lead, v1 logit, baron, elder (as the per-minute draw has them);
- step 0 only: kills the winner got in the fight minus the loser's.

That is about 11 terms on a few thousand step rows (not counted; part A counts them). Same small ridge (`logit_fit`, l2 = 1). Every input
stays even if small (Luke, 12 Nov); each one is reported with its held-out score.

**The per-minute base push is refitted without the fight-push minutes.** Today its rows include the minutes of pushes that run from a
won fight, which the new step now plays. So the per-minute rows leave out the winner's team-minutes inside a real fight push (from the
fight's start to its push's last structure). Otherwise each push would be counted twice. Same inputs as v2 (today's plus the m17 terms).
In the engine, the per-minute draw is skipped for a side while its fight push is live, the same way.

**Push window** (real rows, as m16): a push runs until the next fight starts or 120 s after the fight's last kill, whichever comes first.
A step's y = 1 if the next base structure falls inside that window.

## Worked example: IG v T1, v54 series 1 game 1 (seed 1716133153739033)

Its AI draft was not saved (m15), so this traces the engine's path; the numbers at each step come out of the fit (not checked yet).

- **28:49–29:02:** IG take the mid inhibitor and both nexus towers. That's a per-minute push (no won fight just before it: not checked).
  Structures left to T1's Nexus = 0.
- **29:00–30:52:** no won fight. The per-minute draw runs as in v2 (its refit decides how likely a new push is with 0 left and no fight).
- **30:53:** IG win a fight with the lane open and 0 left. **New:** step 0 asks "does IG's push take the next structure (the Nexus)?" with
  left = 0, T1 dead now (from the fight's kills, each on its timer), IG dead now, 0 s since the last kill, step 0, the fight's kill margin,
  gold lead, v1 logit, baron and elder.
  - If yes, the Nexus falls the real 0-left time after the last kill (median 7 s), if T1 aren't all back by then. The game ends near 31:00.
  - If no, the push stops. IG's per-minute draw resumes once the push window ends (the next fight or 32:53).
- **In v54** this game ran to 61:23 (fights at 44:24 and 47:03 won, base broken again twice).

## Through each file

| File | What changes |
|---|---|
| `research/memory/m19_push_continue.py` (new, through `research/lib`) | Real fight pushes (m16's reading) to step rows with the inputs above; per-minute rows from `s3_rates.py` (as m17) with the fight-push minutes left out. Research copy fit before 1 Sep, held-out log loss from 1 Sep and on Worlds; app copy to 10 Nov. Port check: with nothing left out, the per-minute refit reproduces the v2 coefficients in `SIM_TABLES.base`. Writes `research/model/memory/m19_push_continue.json`, a run record, and with `--app` a `SIM_TABLES.base.continue` block (and the per-minute refit) between generated markers in `js/sim-tables.js` |
| `research/memory/base_push_report_tables.py` or a new `push-continue-report.md` | Report tables generated from the result file |
| `js/sim-engine.js` (the v2 base push block) | After a won fight with a lane open, the winner's push runs step by step with the fitted chance (seeded draws, as now). Its times use the v2 tables. The per-minute draw is skipped for that side while the push is live. `base_push: "off"` still plays v54 exactly |
| `index.html` | Cache v55 (still unreleased) or v56 if v55 is committed first |
| `research/memory/m18_app_check.js`, `m16_nexus_sim.js` (reused) | Replay against the v54 engine; the table above, length, kills, blue win, Player of the Game by role |
| Docs | `research/memory/README.md`, `SESSION_NOTES.md`, the CLAUDE.md Code map line for the data sim |

## A. The fit (research only; stops for Luke's OK before B)

- Count the step rows and fight-push minutes; report how many per structures left and step number.
- Held-out log loss for the step model by input group; the per-minute refit's held-out log loss against v2's.
- **Replay check:** replay the real won fights through the fitted step chances (no sim) and compare the share that take the Nexus by
  structures left with real (94 / 84 / 56 / 30%), on training and held-out games.
- If a group of rows is too thin (0 left before 1 Sep: 55 won fights), say so and ask Luke before pooling anything.

## B. The app (after Luke OKs A)

- Engine as above, on by default, `"off"` = v54 (replay identical, 72 x 20, default and alt).
- Shape checks (72 Worlds drafts x 100 large seeds) against real: the structures-left table, first T3 to the Nexus, length (45+, 50+), kills,
  blue win, Player of the Game by role. Then a new tab at desktop and 375 px, console checked, and the 100-series play-test (m15) on the result.
- Who-wins (1,000 sims per game) stays step 4 of `next-steps-plan.md`.

## Open

- **What happens to the uncommitted v55 (v2 without continuation)?** This plan builds on it, so it stays uncommitted until B is done.
  The alternative is putting the app files back to v54 now and rebuilding v2 together with B.
- **Lane-tower pushes after won fights** (outer and T3 towers) keep today's draw. A continuation for them could follow the same pattern later.
