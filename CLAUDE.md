# Pick'Em Lab — guide for Claude (read this first)

Worlds 2026 Pick'Em Lab: plain HTML/CSS/JS, no build step, no server.
Repo: BlaqkFyre/LOL-Worlds26-Pickems · Live on GitHub Pages · Local master: `C:\Users\Ruth\Documents\GitHub\LOL-Worlds26-Pickems`

If anything here disagrees with what Luke says in the chat, Luke wins — then update this file.

## New-session prompt (for Luke — copy and paste this)

```
I'm continuing work on my Worlds 2026 Pick'Em Lab. Follow CLAUDE.md in this repo: do its start-of-session steps, then wait for what I want to work on.
```

## Start of session (before anything else)

1. Read `SESSION_NOTES.md` (live state + what's next).
2. Read `README.md` and `research/worlds-live-2026.md`. Read others only when the task needs them:
   - Sim engine work → `research/sim-plan.md` (the master copy of the plan; the Claude doc of the same name is only a snapshot), plus `research/backtest-2026.md`.
   - Code work → the Code map below, then the actual lines you'll change.
   - Draft Game work → `Draft Game/draft-card-game-handoff.md` (the folder copy is the master; follow its master copy rules).
3. Run `git status` and `git log --oneline -8`, and check file mtimes. Another session may have edited files: trust disk, not old notes.
4. Reply with: (a) a table of open tasks (Task | Status/blocker) from `SESSION_NOTES.md`, (b) what's uncommitted, (c) the current cache version (`?v=N` in `index.html`). Then wait.

## NEVER-DO rules (cannot be broken)

**Truth**
1. **Never guess.** No estimates or uncounted numbers stated as fact. If it isn't checked, say "not checked", then check or ask.
2. **Never agree with a premise before checking it**, including Luke's notes, your own notes and search summaries. Read the code or source first.
3. **Never trust a search summary.** Open the actual page and give its URL and date. Real match data (picks, bans, K/D/A, lengths, objectives, POG) only from a source page you opened; cross-check against the Oracle's Elixir file when it has the game.
4. **Never infer an official stat.** If no source publishes it (e.g. Player of the Game), leave it out and flag it for Luke.
5. **Real Worlds data never changes simulated standings.** Every tournament run starts at 0-0. Back-test results are for calibration only.

**Actions**

6. **Never run scripts or commands without Luke's OK**, even read-only ones (the start-of-session `git status`/`git log` is fine). Describe it first and wait.
7. **Plan first for any multi-file change.** Trace ONE concrete example (a real team, player or champion) through each file you'll touch. Write code only after Luke OKs the plan.
8. **Never edit from memory.** Read the exact lines before editing. Confirm a function or variable exists before using it.
9. **Verify in the browser pane in a NEW tab**, never one Luke is using, at desktop and phone width, with the console checked for errors. Close it when done.
10. **Never report something as done without saying how it was checked** ("console clean", "clicked through", "headless test", "not checked").
11. **Fix causes, not pixel nudges.**
12. **Never push without asking.** One OK = one push.

**Working style**

13. **When Luke asks a question, just answer it.** No edits until Luke replies.
14. **Do exactly the step Luke OK'd**, then stop and report.
15. **One-line update at each step** of long work. Stop after 5 failed tries at a check and report what *was* verified.
16. **Never leave things half-done:** stop test servers, remove temp changes, report what's still open.

## Repo rules

- **Cache version:** every change to `js/` or `css/` bumps `?v=N` on ALL 9 tags in `index.html` (8 scripts + `styles.css`). The version also goes in the commit title.
- **Gitignored, never commit:** `research/*OraclesElixir*.csv` (78 MB raw data) and `Draft Game/draft-clash-save.json` (autosave).
- **Odds ceiling:** almost no matchup should sim above about 80% (see `research/backtest-2026.md`).
- **Riot limits:** no Riot logos or artwork, free and non-commercial, keep the `ASSETS.icons` on/off switch in `js/assets.js` working.
- **Imported run files are untrusted:** keep the field-by-field checks described in the README.
- **App data is correct as it stands.** Don't change data or code without a reason Luke has agreed to.
- **`research/build/build_from_oe.py` overwrites app files** (`js/h2h.js`, `js/worlds-live.js`) on every run, even without `--fix`. Run it only on a scratch copy of the repo, with Luke's OK, and compare its output with the current files before anything is copied back. Needs Python 3.9+ and pandas.
- **Work stays in Claude Code sessions.** The earlier claude.ai chats that built the app don't write to this repo any more.

## Notes sessions (display review)

When Luke wants to leave notes on the app ("notes session", "notes window"):
1. Make a temporary `.claude/launch.json` (python `http.server` on port 8765, `--directory` the repo root), start it with `preview_start`, and open the app in a new tab at the page Luke names. For phone width use `resize_window` preset mobile, and tell Luke to pick Mobile in the pane's Viewport menu so it stays after the turn ends.
2. Paste `tools/qol-notes-overlay.js` into that tab with `javascript_tool`. Re-paste it if the page is reloaded (notes survive in localStorage `qol-review-notes`).
3. Tell Luke how it works (Note mode on → click → type → Save; Notes (N) lists them) and wait for "notes are done".
4. Read all notes, look at each spot and its code, then give ONE grouped change list (note → change → files, plus anything that's a bigger job). Build nothing until Luke OKs it.
5. Build the whole batch, one cache bump, check in a new tab (all Worlds mode themes, light mode, desktop and 375 px, console), then clean up: stop the server, close tabs, delete `.claude/launch.json`, clear `qol-review-notes` and any theme settings the test changed from localhost storage.

## Sim engine rules (master plan: `research/sim-plan.md`)

- **Plan each foundation with Luke before building it** (ratings, draft AI, draft review, the simulator): agree what it shows, what it's built from and how it feeds the rest, with a worked example, then build.
- **The app only changes in sim session 4.** Sessions 1–3 produce research reports and fitted tables, not app edits.
- **Count each real game once,** matched by game ID. Once the Oracle's Elixir file covers a day, it is the source of record over `js/worlds-live.js`. Same rule for the NerfPlz patch tables (they already include play-in games).
- **Judge only on held-out games** (train before 1 Sep, test after, plus Worlds games as they're played). The new sim ships only if it beats the current one on those games.
- **Few parameters, shrink toward averages.** About 2,800 major-league games supports a simple model, not hundreds of free parameters.
- **Ship small tables only.** The raw file stays local; the app gets small JS tables built from it.
- **Seeded randomness:** the same seed must replay the same game.
- **Minor leagues stay out of fitting** (player history and champion pools only, e.g. 369) unless Luke decides otherwise.
- **Scorecard as an artifact:** once the new model exists, each session or match-day update shows Luke the scorecard as an artifact in the chat (not in the app for now).
- **Exclude the file's "WLDs" rows dated before 1 Oct** (17–19 Sep): they are a regional qualifier, not Worlds. Worlds play-ins are 15–18 Oct, Swiss from 23 Oct (the file's dates are UTC, a few hours ahead).
- **The sim is one replaceable part of the app.** Draft, series, tournament, awards and stats screens only read the game record `pack()` stores (see Code map). Keep that shape, or change those readers on purpose.

## Files

| File | What it is |
|---|---|
| `index.html` | Page markup; loads the js/css with `?v=N` |
| `css/styles.css` | Styles (light and dark themes) |
| `js/ui.js` | Theme toggle, Worlds mode, info popover |
| `js/data.js` | Teams, ratings, champion pools, meta, synergy, counters, play-in drafts |
| `js/champions.js` | Pro data for 165 champions (presence, win rates, roles, builds, play-in users) |
| `js/assets.js` | Champion icons (Data Dragon, on/off switch) and team colours |
| `js/worlds-live.js` | Real Worlds 2026 Swiss games (picks, bans, player stats) |
| `js/h2h.js` | Real 2026 head-to-head between the 16 Worlds teams, for Power Rankings |
| `js/tournament.js` | Tournament engine, stats pool, POG and awards, tournament UI |
| `js/core.js` | Views, tier lists, meta, champ select, draft AI, game simulation (`simGame`) |
| `research/` | Data notes and sources: `worlds-live-2026.md`, `backtest-2026.md` (+ `backtest/`), `pro-meta-findings-2026-10-20.md` |
| `research/sim-plan.md` | **Master copy** of the data-built simulator plan (5 sessions, test targets, risks, open decisions) |
| `research/build/build_from_oe.py` | Rebuilds `js/h2h.js`, `research/model/h2h_2026.json` and the play-in tables in `js/worlds-live.js` from the Oracle's Elixir CSV, and checks the Swiss games (see Repo rules before running) |
| `research/model/` | Tables built from the Oracle's Elixir file (`h2h_2026.json`) |
| `Draft Game/` | Separate pick/ban card game (`index.html`) and its handoff file |
| `tools/qol-notes-overlay.js` | Note-taking overlay for notes sessions (pasted into a browser tab; not loaded by the app) |
| `SESSION_NOTES.md` | Live state, recent updates, what's next, open decisions |

## Code map

Scripts load in this order (`index.html`): `ui.js` → `data.js` → `champions.js` → `assets.js` → `worlds-live.js` → `h2h.js` → `tournament.js` → `core.js`. Everything is global; `core.js` runs last and ends with `loadRun()` then `show(start)`. Views render as template strings into four sections: `#v-tour`, `#v-draft`, `#v-teams`, `#v-role`.

| Area | File | Key names |
|---|---|---|
| Page chrome | `ui.js` | theme toggle, `setWorlds` (Worlds mode themes), ⓘ popover. localStorage keys `lolw26-theme`, `lolw26-worlds` |
| Team and player data | `data.js` | `TEAMS` (per player: name, 3 attributes, top-3 picks `[champ,games,wr]`, KDA, note), `PRES`, `CH` (play-in tier list), `DUOS`, `PARTNERS`, `COMPS` (play-in drafts), `CTR_RAW` (METAsrc counters) |
| Champion data | `champions.js` | `CHAMP_DB` (per champion: `g/w`, `roles`, `p20/rec/sea` [pick%, ban%, win%], `bl` blended presence, `tr`, `fade`, `po`, `so`, `pin`), `CHAMP_ROLE_FALLBACK`, `CHAMP_AP`, `CHAMP_ARCH` |
| Real Worlds games | `worlds-live.js` | `WORLDS_LIVE.games` (rows: `pl` = [role, player, champ, K, D, A, cs, csd15, dmg share, KP], `obj`, `bans`), `pinTeam`/`pin` (play-ins). Built at load: `champ`, `pchamp`, `players`, `mates`, `lane`, `form`. **Form writes straight into `TEAMS` attributes** (±1 per game, ±3 total, clamped 50–99) |
| Head-to-head | `h2h.js` | `H2H_2026.g[A][B] = [wins, losses, [events]]` (real games only) |
| Icons and colours | `assets.js` | `ASSETS.icons` switch, `icon()`, `splashUrl()`, `TEAM_COL`, `REGION_COL`, `regDot()`. Data Dragon cache in localStorage `lolw26-dd` |
| Navigation | `core.js` | `SECTIONS`, `VIEWS`, `show(v)`, `drawNav`. `runCtx()` returns the tournament run only on tournament screens (or a draft started from one), so simulated numbers never show elsewhere |
| Real-data views | `core.js` | `metaView`/`metaTiers`/`synergyView`, `champRoleView`/`champCard`, `roleView`/`playerCard`, `drawPower` (+ H2H matrix), roster grid, `drawCmp` |
| Champion helpers | `core.js` | `metaOf`, `wrOf` (shrunk win rate `adj`), `trendOf`, `proPres` → `basePres` (blends Worlds presence, share = games/(games+60)) → `presOf` (+ `tourPres`), `worldsPool` → `poolOf` (+ `tourPool`), `matchup`, `countersOf`, `SYN`, `ROLEMAP`, `POOL`, `primaryRole` |
| Hover cards | `core.js` | `playerTip`, `teamTip`, `champTip`; touch screens open them as a bottom sheet (`openSheet`) |
| Draft engine | `core.js` | `SEQ` (20 steps), `DS` (draft state), `scoreFor(c, actor, kind)` (hand-weighted pick/ban score with reasons), `recs()`, `doPick`, `queueAI` (AI picks top 3 at 60/25/15%, 2 s delay), `bestMatch` (typed search), `renderDraft`, `teamPanel`, `nextBest` |
| Draft review | `core.js` | `draftScore`, `analysis()`: "Before draft" = `winP(ov gap / 9)`; "After draft" = 600 runs of `simGame` |
| Game sim (to be replaced) | `core.js` | `champMod` → `teamStr` (uses `SIMK`, `STAR`) → `simGame(quiet)` (laning, early objectives, fight loop with `fight`/`push`, Nexus; constants `SIM_SD`, `SIM_GOLD`, `LATE`, `KW`). `runGame` (1500 runs for series odds), `simView` (result screen, gold chart, play-by-play) |
| Box score and POG (to be replaced) | `tournament.js` | `gameStats(g)` adds `g.ps` (K/D/A, dmg share, CS diff, vision, rating `rt`) and `g.pog`; constants `ROLE_DMG`, `ROLE_SHARE`, `DMG_CAP`, `OBJ_W`, `ROLE_ADJ`, `POG_CLOSE`, `LOSER_POG_GAP` |
| **Sim → app boundary** | `tournament.js` | `pack(g)` stores `{blue, red, winner, time, sec, kills, steps, ps[side][role] = {c,k,d,a,kp,dmgS,csd,vis,solo,rt}, pog, dr, ba, g15}`. Series, tournament, stats, awards and import all read this record. `simView` and `analysis` read the sim directly |
| Series mode | `core.js` | `startSeries`, `seriesGame` (loser takes blue), `playSeriesGame`, `seriesPlayers`, `seriesPanel` (shared with tournament Bo3/Bo5) |
| Tournament | `tournament.js` | `RUN` (localStorage `lolw26-pickems-run-v1`), `DAYS`, `R1_DRAW`, `MODES`, `newRun`, `createSwissRound`, `pairUp`, `createQF`, `drawDay`, `ctrlOf` (who drafts), `blueFor`, `playAIGame` (via `withDS` + `autoStep`), `tourPlay` (300 runs for odds), `recordGame` → `addGameStats` + `settleMatch`, `simToNext`/`advanceDay` |
| Run stats pool | `tournament.js` | `RUN.stats` (`champ`, `pchamp`, `players`, `crole`), `tourPres` (blend weight `BASE_GAMES` = 40), `tourPool`, `tourPlayerLine` |
| Awards and winners | `tournament.js` | `awardsData` (Swiss MVP, Tournament MVP, Finals MVP, All-Tournament team), `winnersView`, `champTeam`, `storylines`, `cupSVG` |
| Run import safety | `tournament.js` | `sanitizeRun` → `cleanGame`: every field type-checked and clamped, standings and stats recomputed from the games |

## Git

- Give Luke a commit title + short summary for each change. Title style: `Thing changed, thing changed (vN)`.
- Commit only when Luke asks. Show `git status`/`git diff` first. New commits, never amend.
- After every commit, ask before pushing. One OK = one push.

## End of session

1. Update `SESSION_NOTES.md`: add a "Session (date)" block under Recent updates (what changed, cache version, commits, how it was checked) and refresh What's next. Keep full blocks for the last 3 sessions only; move older ones to the Session index as one line each.
2. Update `README.md`, the `research/` docs or the Draft Game handoff if what they describe changed.
3. Tell Luke what's uncommitted or unpushed.
