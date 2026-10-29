# Pick'Em Lab — session notes

_Live state only. Rules, start/end-of-session steps and the code map are in `CLAUDE.md`. The simulator plan's master copy is `research/sim-plan.md` (link to it here, don't copy it). Keep full blocks for the last 3 sessions; older ones go to the Session index as one line each._

---

## Where we are

- **App:** v31 (29 Oct 2026): Subway and Arcade Smash themes, role-page game-log hover, ticker fix, side-coloured pick/ban tags. App data and code are correct as they stand.
- **Real data:** Swiss rounds 1–3 plus round 4 day 1, 34 games, in `js/worlds-live.js` (data to 28 Oct). H2H in `js/h2h.js` (data to 28 Oct).
- **Sim engine plan:** written 27 Oct, committed `0929636` (29 Oct). Status: planned, not started. See `research/sim-plan.md`.
- **Draft Game:** Tier 1 built, autosave added 26 Oct. See `Draft Game/draft-card-game-handoff.md`.
- **Where work happens:** Claude Code sessions only. The claude.ai chats that built the app no longer write to the repo.

---

## What's next

| Task | Status/blocker |
|---|---|
| **Sim session 1:** ratings and the "who wins" model | Not started. Read `research/sim-plan.md` first. Starts with planning the ratings foundation with Luke (skills per role, what each is fitted from, the overall, how they feed the sim) before any fitting or code |
| Sim sessions 2–5 | After session 1, in order (see the plan) |
| Add Swiss round 4 games to `js/worlds-live.js` | Day 1 (28 Oct, 5 games) added in v31. Days 2–3 (29–30 Oct: KC–CFO, TES–BLG, TL–LOS, HLE–G2) wait for a newer Oracle's Elixir file; steps in `research/worlds-live-2026.md` |
| Add Swiss round 5 (31 Oct), then knockouts (3–14 Nov) | Waits for the games |
| Theme top band wording | Subway band says "the subway lines that stop at this Brooklyn station". If Luke confirms the final is at Barclays Center, it can name the venue |
| Draft Game next steps | Pick one when wanted (feel tweaks, real data, Tier 2, smarter AI, Bo series); see the handoff file |

**Parked:** Custom tournament (Play → Custom). Planned feature, not being worked on yet (Luke, 29 Oct).

---

## Open decisions (Luke)

None open right now.

Decided 29 Oct (details in `research/sim-plan.md`):
- **Ratings:** fitted ratings replace what's shown on the cards. Keep the idea: readable role skills + overall that are interesting and feed the match sim. **Plan the foundation with Luke first** (sim session 1).
- **Draft AI:** rebuilt from data (comfort, team composition, meta, synergy, counters, plus whatever else the data shows).
- **Draft review:** based on the new model. **Plan the foundation with Luke first** (sim session 4).
- **Old engine:** kept. The app uses it until the new one passes its tests, then it stays as a reference, fallback and possible simple mode.
- **Minor leagues:** out of fitting for now; used for player history and pools (e.g. 369).
- **Scorecard:** not in the app for now. Show it to Luke as an artifact in the chat each session or match-day update; keep the numbers in the research notes.

---

## Watch-items

| Watch-item | Trigger |
|---|---|
| Player of the Game isn't published by any source checked so far, so real POG isn't used | A source for official POG appears (also needed for sim session 4) |
| `build_from_oe.py` labels every "WLDs" row as "Worlds" in the H2H "Met at" list, including the 17–19 Sep qualifier rows its own header says aren't Worlds. Game counts aren't affected | Before the script becomes the match-day routine (sim session 5) |
| `build_from_oe.py` always overwrites `js/h2h.js` and `js/worlds-live.js`; an option to write to another folder would make test runs safer | Same as above |
| How Swiss round 4 splits across 28–30 Oct is assumed in `js/tournament.js` (`DAYS`), not published | A published day-by-day schedule |
| Old sim quirks, left alone: odds use 300 runs (tournament), 600 (draft review) or 1500 (series); supports' CS diff is scaled by 0.3 twice in `gameStats` | If the old engine becomes a simple mode, decide with Luke whether to tidy these |

---

## Recent updates

### Session (29 Oct 2026, later) — v31: themes, role-page hover, ticker fix, side colours, round 4 day 1
- **Themes:** Brooklyn · Subway now uses the same clipped buttons as the other themes: route-sign green with an enamel gloss, white selected section, N/Q/R yellow selected page and main buttons, black sign band on panels, explained station band. "Brooklyn Final" renamed **Arcade Smash** (saved value still `brooklyn`): CRT scanlines, pixel-type title (Press Start 2P), neon glow, INSERT COIN, arcade-yellow labels and note bars, dull amber "In the mix".
- **Role pages:** hovering a player name on a card shows a Worlds game log (date, opponent, champion v lane opponent, K/D/A, CS@15, W/L) plus ban risk (`playerLogTip` in `js/core.js`). Elsewhere the hover is unchanged.
- **Ticker fix:** notes scroll only when they don't fit (`fitTicks`, run after render, after fonts load and on width change via ResizeObserver); speed follows length.
- **Draft cards:** pick and ban tags use blue / red side colours (`sideCol`), never team badge colours.
- **Data:** Swiss round 4 day 1 (28 Oct: T1 2-0 MKOI, IG 2-1 LYON) added from Luke's new Oracle's Elixir file, cross-checked with pickorban. `build_from_oe.py` run on a scratch copy: 34/34 games OK, `js/h2h.js` rebuilt to 28 Oct (only new pairs changed). Out-of-sample: favourite 3 of 5, log loss 0.508.
- Previews were built and approved on a scratch copy first. How checked: browser pane at 1440 and 375 px, console clean, hover and draft cards tested.

### Session (29 Oct 2026) — set up for carrying work between sessions
- Read all md docs, all of `index.html` and the 8 JS files, the CSS section structure, and the Draft Game function list (matches its handoff code map).
- Added `CLAUDE.md`: start/end-of-session steps, NEVER-DO rules, repo rules, sim engine rules, files, code map. A first draft went out in Luke's commit `0929636`; this session fixed it (points at `research/sim-plan.md`, WLDs exclusion rule, build-script rule, code map).
- Added `research/build/build_from_oe.py`, saved unchanged as pasted from the claude.ai chat that wrote it. Not run on this PC.
- Added this file.
- Decisions: `research/sim-plan.md` is the master copy of the plan; work stays in Code sessions; Custom tournament is parked; the draft AI gets rebuilt from data; fitted ratings replace the shown ones (concept kept); the draft review uses the new model. Ratings and draft review foundations are planned with Luke first. All added to the plan's decisions.
- No app files changed, no cache bump (still v30). How checked: text check only; the app wasn't loaded.

---

## Session index

| Session | Summary |
|---|---|
| 20–27 Oct 2026 (claude.ai chats) | App built from v20 to v30 (see `git log`): player and champion cards, tournament, series mode, real Worlds data, power rankings, themes. Sim back-tested on 711 series (22 Oct). Sim plan written 27 Oct. No notes file then |
| 29 Oct 2026 | CLAUDE.md, SESSION_NOTES.md and the build script added (block above) |
