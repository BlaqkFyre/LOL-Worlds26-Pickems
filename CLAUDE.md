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
   - Sim engine work → the "Sim engine plan" section of `SESSION_NOTES.md`, plus `research/backtest-2026.md`.
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

13. **When Luke asks a question, just answer it.** No edits until he replies.
14. **Do exactly the step Luke OK'd**, then stop and report.
15. **One-line update at each step** of long work. Stop after 5 failed tries at a check and report what *was* verified.
16. **Never leave things half-done:** stop test servers, remove temp changes, report what's still open.

## Repo rules

- **Cache version:** every change to `js/` or `css/` bumps `?v=N` on ALL 9 tags in `index.html` (8 scripts + `styles.css`). The version also goes in the commit title.
- **Gitignored, never commit:** `research/*OraclesElixir*.csv` (78 MB raw data) and `Draft Game/draft-clash-save.json` (autosave).
- **Odds ceiling:** almost no matchup should sim above about 80% (see `research/backtest-2026.md`).
- **Riot limits:** no Riot logos or artwork, free and non-commercial, keep the `ASSETS.icons` on/off switch in `js/assets.js` working.
- **Imported run files are untrusted:** keep the field-by-field checks described in the README.

## Sim engine rules (from the 27 Oct plan, see SESSION_NOTES.md)

- **The app only changes in sim session 4.** Sessions 1–3 produce research reports and fitted tables, not app edits.
- **Count each real game once,** matched by game ID. Once the Oracle's Elixir file covers a day, it is the source of record over `js/worlds-live.js`. Same rule for the NerfPlz patch tables (they already include play-in games).
- **Judge only on held-out games** (train before 1 Sep, test after, plus Worlds games as they're played). The new sim ships only if it beats the current one on those games.
- **Few parameters, shrink toward averages.** About 2,800 major-league games supports a simple model, not hundreds of free parameters.
- **Ship small tables only.** The raw file stays local; the app gets small JS tables built from it.
- **Seeded randomness:** the same seed must replay the same game.
- **Minor leagues stay out of fitting** (player history only) unless Luke decides otherwise.

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
| `Draft Game/` | Separate pick/ban card game (`index.html`) and its handoff file |
| `SESSION_NOTES.md` | Live state, what's next, sim engine plan |

## Git

- Give Luke a commit title + short summary for each change. Title style: `Thing changed, thing changed (vN)`.
- Commit only when Luke asks. Show `git status`/`git diff` first. New commits, never amend.
- After every commit, ask before pushing. One OK = one push.

## End of session

1. Update `SESSION_NOTES.md`: add a "Session (date)" block under Recent updates (what changed, cache version, commits, how it was checked) and refresh What's next. Keep full blocks for the last 3 sessions only; move older ones to the Session index as one line each.
2. Update `README.md`, the `research/` docs or the Draft Game handoff if what they describe changed.
3. Tell Luke what's uncommitted or unpushed.
