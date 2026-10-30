# Pick'Em Lab — session notes

_Live state only. Rules, start/end-of-session steps and the code map are in `CLAUDE.md`. The simulator plan's master copy is `research/sim-plan.md` (link to it here, don't copy it). Keep full blocks for the last 3 sessions; older ones go to the Session index as one line each._

---

## Where we are

- **App:** v32 (30 Oct 2026): Swiss round 4 day 2 data, subway band restyled as an aged station sign (caption removed). App data and code are correct as they stand.
- **Real data:** Swiss rounds 1–3 plus round 4 days 1–2, 39 games, in `js/worlds-live.js` (data to 29 Oct). H2H in `js/h2h.js` (data to 29 Oct). **TES 2-1 BLG is from Leaguepedia and pickorban, not yet the Oracle's Elixir file:** re-check it when the next file arrives.
- **Sim engine plan:** written 27 Oct, committed `0929636` (29 Oct). Status: planned, not started. See `research/sim-plan.md`.
- **Draft Game:** Tier 1 built, autosave added 26 Oct. See `Draft Game/draft-card-game-handoff.md`.
- **Where work happens:** Claude Code sessions only. The claude.ai chats that built the app no longer write to the repo.

---

## What's next

| Task | Status/blocker |
|---|---|
| **Sim session 1:** ratings and the "who wins" model | Not started. Read `research/sim-plan.md` first. Starts with planning the ratings foundation with Luke (skills per role, what each is fitted from, the overall, how they feed the sim) before any fitting or code |
| Sim sessions 2–5 | After session 1, in order (see the plan) |
| Confirm TES–BLG (29 Oct) against the next Oracle's Elixir file | Waits for a file with data past 29 Oct 21:00 UTC. Compare all 3 games field by field, fill in CS@15 and `fp`, rerun `build_from_oe.py` on a scratch copy (H2H should still show TES v BLG 8-11) |
| Add Swiss round 4 day 3 (30 Oct: TL–LOS, HLE–G2) | Being played 30 Oct; then the next Oracle's Elixir file. Steps in `research/worlds-live-2026.md` |
| Add Swiss round 5 (31 Oct), then knockouts (3–14 Nov) | Waits for the games |
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
| Player of the Game isn't published by any source checked so far, so real POG isn't used. **New lead (30 Oct):** Leaguepedia's Main Event page now has an "MVP" column per series and "MVP Standings" (e.g. TES–BLG: Tian; several series show "None"). Not checked: where it comes from or whether it is the official award | Luke decides whether to look into it (also needed for sim session 4) |
| Old sim overrates BLG against TES (76–90% in all 3 games, TES won 2-1); the ceiling issue keeps showing | The new sim (sim sessions 1–4) |
| `build_from_oe.py` labels every "WLDs" row as "Worlds" in the H2H "Met at" list, including the 17–19 Sep qualifier rows its own header says aren't Worlds. Game counts aren't affected | Before the script becomes the match-day routine (sim session 5) |
| `build_from_oe.py` always overwrites `js/h2h.js` and `js/worlds-live.js`; an option to write to another folder would make test runs safer | Same as above |
| How Swiss round 4 splits across 28–30 Oct is assumed in `js/tournament.js` (`DAYS`). Leaguepedia now publishes it: 2 series a day (28: MKOI–T1, IG–LYON; 29: KC–CFO, TES–BLG; 30: TL–LOS, HLE–G2). The days in `DAYS` match; how the code assigns series to days was not checked | Check when convenient |
| Old sim quirks, left alone: odds use 300 runs (tournament), 600 (draft review) or 1500 (series); supports' CS diff is scaled by 0.3 twice in `gameStats` | If the old engine becomes a simple mode, decide with Luke whether to tidy these |

---

## Recent updates

### Session (30 Oct 2026) — v32: Swiss round 4 day 2, aged subway sign
- **Data:** KC 2-0 CFO from Luke's new Oracle's Elixir file (data to 29 Oct 21:00 UTC). It matches pickorban and Leaguepedia on every field checked. TES 2-1 BLG isn't in the file yet, so it came from Leaguepedia's scoreboards with pickorban for damage share (CS@15 null, `fp` left out). `js/worlds-live.js` now has 39 games. `build_from_oe.py` was run on a scratch copy: 34/34 OK, `js/h2h.js` rebuilt to 29 Oct, then TES–BLG added by hand. Details and sources in `research/worlds-live-2026.md`.
- **Pick/ban check:** the app's pick, ban and win counts for all 84 champions match Leaguepedia's Main Event champion statistics (39 games).
- **Out-of-sample (v31 before the update):** favourite 3 of 5, log loss 0.945, Brier 0.334. BLG was 76–90% in all three TES games. Running total: 23 of 39 (59%).
- **Subway band:** caption removed; the band now looks like an aged enamel station sign (grain texture, top white stripe, off-white Helvetica, faded bullets with scuffs, screw heads). CSS only, in `css/styles.css`.
- Cache v31 → v32. How checked: local server in a new browser-pane tab at desktop and 375 px, console clean, data counts and H2H read in the console, role-page game log for 369 renders with the missing CS@15 shown as a dash. The temporary `.claude/launch.json` was removed afterwards.
- Download link for the Oracle's Elixir file is now in the Sources section of `research/worlds-live-2026.md`.

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
