# Fight windows: after a won fight, the winners take what fits before the losers respawn (plan, 27 Nov 2026 AEST; not built)

Luke (27 Nov): "ideally the sim tracks deaths, objectives, and can tell if a dragon/baron/elder or inhib/tower/base push is the best
option left for the winning fight team (noting how many are left alive and death timers for both sides) ... whatever you can take in
that space ... that would determine the push or base and reset and wait for next obj". He also said the patches on the per-minute draw
(v51-v55) were getting overdone. This plan replaces those patches with one model. Each part stops for Luke's OK.

## What real games show (counted, `research/memory/m20_fight_windows.py`, `research/model/memory/m20_fight_windows.json`)

640 gol.gg timelines, 7,271 won fights (kills under 20 s apart; the side with more kills wins), 976 of them at Worlds. Players alive
and respawns from the official death timer at each victim's level (as m17).

- **The window.** From a won fight's last kill until the losers dead at that moment are all back: median 38 s (10–90%: 14–55 s);
  51 s with all five dead.
- **Players alive decides the base**:

  | Lane open, structures left | Winners 3+ players up | Winners 1–2 up | Even or behind |
  |---|---|---|---|
  | 0 | 99% Nexus (74 fights) | 85% (20) | 1 of 3 |
  | 1 | 95% (79) | 58% (31) | 0 of 1 |
  | 2 | 86% (228) | 12% (149) | 0 of 6 |
  | 3 | 51% (88) | 10% (96) | 0 of 2 |

- **Monsters after a won fight**, taken before the losers are all back, when up:

  | Monster | Winners 3+ up | Winners 1–2 up | Even or behind |
  |---|---|---|---|
  | Baron | 40% (539 fights) | 22% (1,202) | 2% (54) |
  | Dragon | 40% (315) | 26% (1,185) | 23% (39) |
  | Elder | 21% (47) | 57% (42) | – |

  The elder numbers are thin.
- **When it falls.** Base structures and the Nexus mostly fall before the first loser is back. The Nexus fell after the losers were
  all back only 2 times in 567. Dragons and outer towers mostly fall after: a separate action, not the fight's window.
- **How much of the game this covers.** 6,009 of 15,692 objectives (38%) fall inside a won fight's window:
  - most base objectives: the Nexus 91%, nexus towers 89%, inhibitors 70%, T3 towers 63%;
  - baron 60% and elder 70%;
  - few early ones: dragons 21%, outer towers 28%, herald 16%, grubs 6%.

  The other 62% happen with no won fight just before them.

## The model

**After every won fight in the sim** (the engine already plays fights kill by kill and tracks each death's respawn time):

1. **State at the last kill:**
   - players alive on each side, and when each dead player is back;
   - what's available: dragon, elder or baron up, the next tower or inhibitor in each lane, nexus towers, the Nexus;
   - gold lead and game time.
2. **Choose the next action:** one of the available objectives, or **reset**. The choice is fitted on real won fights (what the
   winners took next, or that they took nothing more). Its inputs:
   - players alive on each side;
   - time until the next loser is back, and until all are back;
   - what's up, and structures left;
   - gold lead and game time.
   Nothing is set by hand: the table above is the test, not a setting.
3. **When it falls:** a real time from the last kill (or the previous action), by action and players alive (measured, e.g. the
   Nexus: median 15 s with 3+ up). The timelines record only when an objective finished, not when the team started on it.
   So this time includes walking there; it is measured, not a hit-point sum.
4. **Repeat** until reset is chosen. The Nexus keeps its check: it falls only before the losers are all back (real: 2 of 567 after).
5. **Reset:** the game goes back to its normal flow (the next fight, objectives with no fight).

**Objectives with no won fight before them** (62%, mostly dragons, outer towers, grubs and herald) keep today's per-minute draws in
this first build. They're refitted on the objectives outside fight windows, so nothing is counted twice (Luke's point 2). The same
choose / take / reset idea could replace them later, using "no one dead" as the state. That's a second plan, after this one works.

**What this replaces:** the per-minute base push for pushes after a fight, the v55 base push v2 additions, the push continuation
(`push-continuation-plan.md`), the push chain timing (`SIM_TABLES.push`), and the after-fight part of the monster draws.

**Not in scope:** when fights start (still the fitted fight count each minute) and how fights play out (kill credit v2).

## Worked examples (real, Worlds play-ins 15 Oct, from `m20_fight_windows.json`)

- **MVK Esports v FURIA, fight ends 22:13 (1-0), 5 v 3 alive:**
  - the first FURIA player is back 3 s later, all of them 30 s later;
  - MVK take baron at +14 s, then outer towers at +84 and +133 s;
  - the model's steps: choose baron (5 v 3, baron up, 30 s to all back), it falls at a real "baron, 3+ up" time, then reset.
    The towers later belong to the normal flow.
- **MVK Esports v FURIA, fight ends 23:51 (4-1), 4 v 1 alive:**
  - FURIA are back at +30 / +44 s;
  - MVK take dragon at +11 s, then baron at +49 s, 5 s after FURIA are all back;
  - this is why being back is an input to the choice, not a block: real teams sometimes finish an objective as the defenders return.

## Steps (each stops for Luke's OK)

**A. Fit (research only).**
- **Rows:** real won fights and each "next action or reset" step: the fit before 1 Sep, held-out from 1 Sep and on Worlds, and an
  app copy to 10 Nov.
- **The choice model:** first take something or reset, then which one, so there are fewer terms than one big choice. It's shrunk
  toward averages (about 7,000 fights; few parameters).
- **Take times** by action and players alive.
- **Replay check (no sim):** real won fights through the fitted steps; the share that take the Nexus, baron and dragon by players
  alive against the tables above.
- **The per-minute draws refitted** without the objectives inside real fight windows.

**B. App** (new setting `fight_window: "v1"`, on by default; `"off"` replays v54 exactly):
- the engine runs the window after each won fight;
- checks against real (72 Worlds drafts × 100 large seeds): the tables above, game length (45+), kills, blue win, Player of the Game
  by role;
- a new browser tab at desktop and 375 px with the console checked; then the 100-series play-test.

**C. Who-wins** (1,000 sims a game) stays step 4 of `next-steps-plan.md`.

## Open for Luke

- **v55 (base push v2, uncommitted)** and the push continuation fit (running now): this plan replaces both. Proposed: keep their
  research results, put the app files back to v54 before B.
- **The 62% outside fight windows:** keep the per-minute draws for them in this first build (above), or plan their replacement first.
