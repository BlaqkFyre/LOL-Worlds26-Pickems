# Pick'Em Lab — session notes

_Live state only. Rules, start/end-of-session steps and the code map are in `CLAUDE.md`. The simulator plan's master copy is `research/sim-plan.md` (link to it here, don't copy it). Keep full blocks for the last 3 sessions; older ones go to the Session index as one line each._

---

## Where we are

- **App:** v30, last app commit `94d176e` (27 Oct 2026): new menu, card pages, power rankings with 2026 head-to-head, city editions. App data and code are correct as they stand.
- **Real data:** Swiss rounds 1–3, 29 games, in `js/worlds-live.js` (data to 26 Oct). H2H in `js/h2h.js` (data to 26 Oct).
- **Sim engine plan:** written 27 Oct, committed `0929636` (29 Oct). Status: planned, not started. See `research/sim-plan.md`.
- **Draft Game:** Tier 1 built, autosave added 26 Oct. See `Draft Game/draft-card-game-handoff.md`.
- **Where work happens:** Claude Code sessions only. The claude.ai chats that built the app no longer write to the repo.

---

## What's next

| Task | Status/blocker |
|---|---|
| **Sim session 1:** ratings and the "who wins" model | Not started. Read `research/sim-plan.md` first. Needs open decision 1 (below) before ratings replace anything on screen |
| Sim sessions 2–5 | After session 1, in order (see the plan) |
| Add Swiss round 4 games (28–30 Oct) to `js/worlds-live.js` | Not started. Steps in `research/worlds-live-2026.md`; bump the cache version |
| Add Swiss round 5 (31 Oct), then knockouts (3–14 Nov) | Waits for the games |
| Test `research/build/build_from_oe.py` on a scratch copy | Not run on this PC. Check Python + pandas, run on a scratch copy, compare with the current files (expected: same data; two lists re-ordered, `h2h.js` header comment changes, `h2h_2026.json` event labels change from "WLDs" to "Worlds"). Only with Luke's OK |
| Draft Game next steps | Pick one when wanted (feel tweaks, real data, Tier 2, smarter AI, Bo series); see the handoff file |

**Parked:** Custom tournament (Play → Custom). Planned feature, not being worked on yet (Luke, 29 Oct).

---

## Open decisions (Luke)

From this session (29 Oct):
1. **Ratings:** when sim session 1 fits ratings from results, do they replace the ratings shown on player cards, power rankings and tier lists, or only feed the sim?
2. **Draft AI:** rebuild `scoreFor()` (hand-weighted) from data as part of the plan, or keep it?
3. **Draft review:** move "Before draft" (`winP` on the rating gap) and "After draft" to the new who-wins model?

From `research/sim-plan.md`:
4. Keep the old engine as a "Classic" mode, or remove it once the new one passes its tests?
5. Show the match-day scorecard in the app, or keep it in the research notes?
6. Confirm the minor leagues stay out of fitting.

---

## Watch-items

| Watch-item | Trigger |
|---|---|
| Player of the Game isn't published by any source checked so far, so real POG isn't used | A source for official POG appears (also needed for sim session 4) |
| `build_from_oe.py` labels every "WLDs" row as "Worlds" in the H2H "Met at" list, including the 17–19 Sep qualifier rows its own header says aren't Worlds. Game counts aren't affected | Before the script becomes the match-day routine (sim session 5) |
| `build_from_oe.py` always overwrites `js/h2h.js` and `js/worlds-live.js`; an option to write to another folder would make test runs safer | Same as above |
| How Swiss round 4 splits across 28–30 Oct is assumed in `js/tournament.js` (`DAYS`), not published | A published day-by-day schedule |
| Old sim quirks, left alone because the sim is being replaced: odds use 300 runs (tournament), 600 (draft review) or 1500 (series); supports' CS diff is scaled by 0.3 twice in `gameStats` | Only if the old engine is kept as "Classic" |

---

## Recent updates

### Session (29 Oct 2026) — set up for carrying work between sessions
- Read all md docs, all of `index.html` and the 8 JS files, the CSS section structure, and the Draft Game function list (matches its handoff code map).
- Added `CLAUDE.md`: start/end-of-session steps, NEVER-DO rules, repo rules, sim engine rules, files, code map. A first draft went out in Luke's commit `0929636`; this session fixed it (points at `research/sim-plan.md`, WLDs exclusion rule, build-script rule, code map).
- Added `research/build/build_from_oe.py`, saved unchanged as pasted from the claude.ai chat that wrote it. Not run on this PC.
- Added this file.
- Decisions: `research/sim-plan.md` is the master copy of the plan; work stays in Code sessions; Custom tournament is parked.
- No app files changed, no cache bump (still v30). How checked: text check only; the app wasn't loaded.

---

## Session index

| Session | Summary |
|---|---|
| 20–27 Oct 2026 (claude.ai chats) | App built from v20 to v30 (see `git log`): player and champion cards, tournament, series mode, real Worlds data, power rankings, themes. Sim back-tested on 711 series (22 Oct). Sim plan written 27 Oct. No notes file then |
| 29 Oct 2026 | CLAUDE.md, SESSION_NOTES.md and the build script added (block above) |
