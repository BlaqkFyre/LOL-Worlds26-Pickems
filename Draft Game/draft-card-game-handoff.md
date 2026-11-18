# Draft Pick/Ban Card Game — Project Handoff

*Last updated: 18 Nov 2026, after lane structures (respawning inhibitors and nexus turrets) and pick-offs in the sim (see "The sim" below). Before that, 17 Nov: all 173 League champions as coded cards (see "Real champion cards" in section 0).*

> **Resume prompt:** "Here's my handoff file for the draft pick/ban card game. The game is in `C:\Users\Ruth\Documents\GitHub\LOL-Worlds26-Pickems\Draft Game\index.html`, and I've linked that repo folder. Read this file and the game, then help me with: ___"

**For the new chat:** link the `LOL-Worlds26-Pickems` folder so it can read and edit `Draft Game\index.html` directly. Read section 0 first; the sections after it are the original research and plan.

> **Master copy rules (for any chat working on this project)**
> 1. **Read from here.** The master copy of this file is `C:\Users\Ruth\Documents\GitHub\LOL-Worlds26-Pickems\Draft Game\draft-card-game-handoff.md`. At the start of a session, read it from that folder, even if a copy was attached to the chat. If the two differ, the folder copy wins.
> 2. **Save back here.** Whenever something changes (a feature added, a decision made, a next step done), update this file **in that same folder**, at the same file name, and update "Last updated" at the top. Don't create copies with other names, and don't leave updates only in the chat.
> 3. **Same for the game.** Edit `Draft Game\index.html` in place, then update section 0 here.
> 4. **Re-check before saving.** If the file changed on disk since you read it (for example, another window edited it), re-read it and merge your changes rather than overwriting.
> 5. **Commits:** give Luke a commit title and a short summary for each change.

---

## 0. Current status: quick concept built (Tier 1)

**Files** (in `LOL-Worlds26-Pickems\Draft Game\`):

| File | What it is |
|---|---|
| `index.html` | The playable game. One file of about 56 KB, with no libraries and no assets |
| `draft-card-game-handoff.md` | This file (the master copy; see the rules above) |
| `draft-clash-save.json` | The game's autosave. It appears after you choose this folder in the game (see "Autosave" below). Safe to delete; the game then starts fresh. It's kept out of git by the repo's `.gitignore` |

**Running it:** double-click `index.html` to open it in Chrome. Nothing needs installing.

### Autosave (added 26 Oct 2026)
- **Setup:** click **Save folder: choose…** in the toolbar and pick the `Draft Game` folder. Chrome asks to allow editing; allow it. The button then shows **Saving to: Draft Game ✓**.
- **What's saved:** `draft-clash-save.json` in that folder holds:
  - settings: sound, speed, auto-draft
  - the game in progress: your side, the draft step, bans and picks (a game that reached the board or result resumes at the CLASH! button)
  - your results history: last 50 games, with winner, your side, pre-game odds and game length
- **When it saves:** after every pick or ban, setting change and finished game.
- **Your record:** shown on the side-select screen and the result screen ("Your record: 3W – 2L · 1 upset win").
- **Loading:** when you open the game, it loads from that file. Chrome remembers the folder. If Chrome asks again after a restart, the button shows **Reconnect save folder**; one click reconnects it.
- **Backup in browser storage:** a copy is also kept in Chrome's storage, so progress isn't lost before a folder is chosen. When you connect the folder, the newer of the two is used. An empty save never overwrites a real one.
- **Other browsers:** browsers without folder access (e.g. Firefox) get **Download save** and **Load save file** buttons instead.
- **Checks on loading:** save files are checked field by field (valid champion ids, no duplicates, ban/pick counts matching the draft step). An invalid game is ignored rather than loaded.

### What's in the game
1. **Side select:** a 3D coin flip ("YOU"/"AI"). If you win the toss you pick Red (top half, last pick) or Blue (bottom half, first pick). If the AI wins, it picks for you.
2. **Draft:**
   - **Order and timer:** the 20-step pro order, Blue first, against an AI. On your turn you get a 30-second timer, with ticks for the last 5 seconds. If it runs out, the AI picks for you.
   - **Overlay:** a semi-transparent window over the board, with opaque tiles in a 10×4 grid. It also shows the phase label, whose turn it is, the 20-pill order tracker, both teams' synergy, a win% estimate bar, a champion info panel on hover (stats, synergy with your picks, lane matchup) and a "Hold to peek at board" button.
   - **Ban animation:** the tile shakes, greys and cracks, flies to that team's ban row, and slams in.
   - **Pick animation:** the tile glows in the team colour, flies to its lane slot and becomes a card, with a slam, a burst and a small screen shake.
   - **Lanes:** a pick goes to the champion's main lane, or its flex lane if the main one is filled. Tiles that can't fit are dimmed. If nothing fits, off-role picks are allowed with a stat penalty.
3. **Board:** five lanes per side (Top, Jungle, Mid, Bot, Support).
   - **Side panels:** the left team boxes show synergy, kills, towers, dragons, barons and elders. The right bar shows win% during the draft and the gold lead during the clash.
   - **CLASH! button:** shows the pre-game win chance (600 sims).
4. **Clash:** the sim's event log is played back as animation, with a clock and caption above the board.

   | Event | Animation |
   |---|---|
   | Lane kill | The lane's cards crash at the midline (Bot and Support together), and the loser is knocked back |
   | CS lead | The winner's card nudges forward |
   | Gank | The jungler crosses to the lane and hits the enemy laner |
   | Dragon / Grubs / Herald / Baron / Elder | A token pops at the midline and flies to the winner's box. A stolen objective is tagged STOLEN! |
   | Team fight | All 10 cards charge and crash, with a big burst and screen shake |
   | Towers / inhibitor | The winner's cards push forward |
   | Dragon Soul | Banner |
   | Nexus | The winner's cards charge through, and the loser's cards tilt and fade |

5. **Result:**
   - **Shows:** a "BLUE/RED WINS" banner, You win/lose, a stats table, the game time, and the winner's pre-game win chance (tagged **UPSET!** if it was under 50%).
   - **Buttons:** **Rematch (same draft)** reruns the sim, so you can see the result change. **Sim 100 games** shows the split for that draft. **New draft** starts over.

**Toolbar:**
- Sound on/off.
- Speed 1×/2×/4×.
- Auto-draft (the AI drafts your side too, which is useful for testing).
- Skip (jumps to the end of a clash).
- New game.

**Sound:** generated by the Web Audio API with no files: click, tick, whoosh, coin, slam, shatter, crash, nudge, chime, tower, fanfare, win and lose.

### Real champion cards (17 Nov 2026; Luke: "accurate enough and quick so it can be playtested, still very early ideas")
- **173 cards, one per League champion, no names:** a Riot class letter plus a number by release date within the class, so codes stay stable when champions are added: **F** Fighter, **M** Mage, **R** Marksman, **T** Tank, **S** Support, **A** Assassin. The tile shows the code and the first subclass (e.g. "M19 · Burst"). The real names are only in `research/champions/clash_cards.json` (`code_to_name`), not in the game.
- **100 on offer per draft:** a fresh random 100 each game, at least 12 per main role. The draft grid scrolls and is grouped by main role. The pool is saved with the game.
- **Data:** `Draft Game/clash-cards.js` (`window.CLASH_CARDS`), built by `research/champions/build_clash_cards.py` from the champion database (`research/champions/`), the Oracle's Elixir 2026 file and Riot's Universe site. Never hand-edit it; rebuild it. Without the file the game falls back to the 40 placeholders below.
- **Roles:** main = the champion's pro meta role (Worlds 2026 first, then 2026 majors, then Riot's lane), flex = its first off-role.
- **Stats shown as grades** (S+ S A+ A B+ B C D F; the info panel never shows numbers). Each stat is ranked across the 173 from 2026 pro games, pulled toward average for champions with few games:
  - Lane: gold edge at 15 in its meta role.
  - Teamfight: kill participation, damage share and Riot's crowd-control rating.
  - Late: win rate in 33+ minute games minus under 28 minutes.
  - Objectives: share of dragons and Barons its team took.
  - Inside the sim a grade is a number 62–92 (the placeholders' spread, so the game's balance holds).
- **Synergy** (shown in the info panel, part by part):
  - **Pair:** two champions with 8+ pro games together that won more or less than their own records predict (−2 to +4). 1,273 pairs.
  - **Style:** subclass and playstyle-tag combos a team holds that won more in pro play (66 combos, kept only where the effect had the same sign before and after 1 Sep), counted once per team, ±2 at most.
  - **Bond (flavour):** Riot's "related champions" on the Universe site, +1 (394 pairs).
  - **Region set (flavour):** 3+ cards from one Universe region on a team, +2 (unaffiliated champions don't count).
  - A team's total counts with diminishing returns in the sim (at most about ±6), because real pair records overlap.
- **Lane matchups:** pro matchups with 3+ games, only the part specific to the pair (each champion's usual lane strength is already in its Lane grade), range about 32–62%.
- **Info panel** (fits without scrolling, checked with 4 picks and with 6 pills):
  - Header: code and subclass, lanes, the lane matchup against the enemy in that lane ("vs F22 52%").
  - One line: class, subclasses, damage type, range, region (playstyle tags on hover).
  - A strip of the four grades (LANE, FIGHT, LATE, OBJ), coloured by grade.
  - **Synergy · Rivals panel** (Luke, 17 Nov): one pill per synergy that exists, coloured by value: crimson −2 or worse, purple −1, green +1/+2, yellow +3 or better. Pills cover each of your picks with a pair or bond synergy, the team style change, and a region set the card completes. Riot-related champions on the enemy team show as grey "Rival" pills (flavour, no score). With none of these, one grey pill: "No synergy or rivals".
  - The draft's win-chance box is now a slim bar with both teams' synergy totals under it.
- **Saves:** version 2. A version 1 save (placeholder cards) keeps its settings and history; its game in progress is dropped.
- **Balance check** (400 random drafts, browser, 17 Nov): favourite wins 64%, 2.75% of drafts above 80% (max 90%), average game 33.2 min (median 32), first Baron team wins 83%. Placeholders: 62%, 2% (max 87%), 33 min, 86%. Before the fixes (number spread, matchup double count, style counted per pair, all in `build_clash_cards.py`; synergy stacking, the cap in `teamStr`), 17% of random drafts were above 80%, and one AI-drafted game reached 95% on +17 synergy (71% with the cap).
- **Draft AI (17 Nov):** a card's value = its power in the role it would play + the change in its team's synergy as the sim counts it (pairs, style combos, region sets, with the same diminishing returns) + its lane matchup against the enemy already in that lane. Weights follow how the sim uses them: one synergy point ≈ 2.1 power, one matchup point ≈ 0.8 power. Bans: the card's value to the enemy plus how badly it would beat our laner. Still no ban planning or denial of comfort picks.
- **Timer option (17 Nov):** toolbar **Timer: On / Off (practice)**. Off = no 30-second pick timer (shows ∞). Saved with the settings.
- **Hover panel, enemy side (17 Nov):** under your team's pills, **ENEMY TEAM · IF THEY TAKE IT** shows the same for the enemy: their pair/bond synergies with the card, their style and region-set change, and rivals on your team. One grey pill when there is nothing.
- **Layout (17 Nov):** the draft window now sits between the team boxes (left) and the win bar (right), full board height (x 150–904, y 62–698), so synergy totals, kills and the win/gold bar stay visible during the draft. The grid is 7 columns; the tracker pills are 30 px wide.
- **Objective calls (concept, 17 Nov; toolbar Objective calls: On / Off):** when a Dragon, Baron or Elder comes up in the clash, the game pauses and you choose for your team:
  - **Fight for it:** the normal contest; the panel shows your estimated fight odds (from the sim's own fight formula: team strengths, gold, buffs).
  - **Give it up:** the enemy takes it unopposed, no fight and no push that turn, and your team regroups: a bonus to your next fight of 1 + 1.5 × (your late-game strength minus theirs) + 1 per 3k gold behind, between 0.5 and 4. So scaling comps and teams behind gain more from conceding.
  - How it works: the clash runs from a seed; at a call it stops, asks, and re-runs the same seed with your answer, so everything before the call is identical. Choosing "fight" every time gives exactly the no-calls game (checked). Skip answers "fight". Only your side is asked for now; the enemy and AI calls come later. The early objectives (first Dragons, Grubs, Herald) are not calls yet.
- **Series (17 Nov):** the coin-toss screen has **FORMAT: Bo1 / Bo3 · Fearless / Bo5 · Fearless** (saved as a setting). Series are always Fearless: every champion picked in an earlier game of the series is locked for both teams (hidden from the grid). The pool is drawn once per series: 100 + 10 per extra game (Bo3 120, Bo5 140), at least 12 + 2 per extra game per main role. The loser of a game takes Blue in the next (no coin flip after game 1). The result screen shows the series score and **Next game (game N)**; Rematch is hidden in a series. **New game** in the toolbar starts a new series. The series is saved with the game (`series` in the save; checked field by field like the rest).
- **Grid shows only what you can pick (17 Nov):** banned, picked and Fearless-locked champions are hidden, and on your pick turn so are champions that can't fill an open role. The tile is hidden after its ban/pick animation.
- **Picked and banned champions can still be looked at (17 Nov):** each tracker pill shows the code of the champion banned or picked at that step; hovering it shows the champion in the info panel (its real team's synergies for a pick). Board cards and ban slots show a hover card (code, lanes, matchup, grades, the team's synergy and rivals; "Banned by …" for bans). The "Hold to peek at board" view now lets the mouse through to the board, so picked cards can be hovered while peeking.
- **Portraits (concept, 17 Nov; toolbar Portraits: On/Off):** 10 random cards per game show Riot's loading-screen art (Data Dragon `img/champion/loading/<id>_0.jpg`) faintly behind the card colour, on tiles, board cards and ban slots. Off removes them. Cards carry their Data Dragon id (`dd`) for this.
- **End screen lane table (17 Nov):** for each lane, both cards (code, subclass, lane grade), how laning went in this game (kill, CS lead or even; the jungle row shows a gank), and Blue's matchup %. The sim doesn't track per-champion K/D/A yet.
- **Synergy v card strength (Luke, 17 Nov: the best synergy shouldn't always be a mega advantage):** a team's synergy now counts at most about ±4 in the sim and in the AI's scoring (`SYN_CAP`, was 6). Example: a draft with +17 synergy but weaker cards (79.5 v 81.2 average strength) against −2 synergy: 64% now, 71% at the old cap, 95% with no cap. 400 random drafts: favourite wins 58%, 3.75% above 80% (max 90%), average game 33 min, first Baron team wins 85%.
- **Arena mode (concept, 17 Nov; FORMAT: Arena · 8 wins / 3 losses):** one Fearless run against the AI until you win 8 games or lose 3. Each run draws 150 of the 173 champions (at least 24 per main role); every game's 10 picks are locked for the rest of the run, so up to 100 of the 150 get used. The result screen shows wins needed and losses left, then "ARENA VICTORY!" or "Arena run over". **Leaderboard:** finished runs are saved (last 30) and the best three show on the coin-toss screen. Seasons with one shared pool for all players are an idea for later.
- **Arena preview:** open `Draft Game/index.html?arena=7-2` (any W-L up to 7-2) to start an Arena run at that record; the AI drafted both sides of the games already played. Nothing is saved while previewing. Check (17 Nov, one run at 7-2): 90 of 150 locked, 60 left; the average strength of each game's 10 picks fell 82.5 → 80.9 → 80.8 → 79.3 → 78.5 → 77.3 → 77.8 → 76.9 → 74.1; used champions averaged 78.7, the 60 left 74.5. Left by main role: Top 12, Jungle 23, Mid 11, Bot 9, Support 5, so late Arena games push teams into flex and off-role picks.
- **Flex lanes (17 Nov):** when you pick a flex card and both its main and flex lanes are open, the footer asks which lane (or Cancel). The YOUR LINEUP strip under the synergy totals, or your own cards on the board, swap two lanes or move a card into an empty lane at any point until CLASH. Synergy and the win chance update straight away, and the save keeps the new lanes. A card outside its main and flex lanes plays OFF-lane with the usual stat penalty. Enemy cards can't be clicked.
- **Not done yet:** grades and synergies are a first pass for playtesting; enemy and AI objective calls; per-champion game stats; Arena rewards beyond the best-runs list.

### Champions (placeholders, used only when `clash-cards.js` is missing)
- **40 champions**, "Champ 01–40" (tiles show "C01"). They are generated from a fixed seed (2026), so they're the same every run.
- **Roles:** each has a main role cycling Top/Jg/Mid/Bot/Sup, and about 30% have a flex role.
- **Stats:** Lane, Teamfight, Late, Objectives, each 55–95, with small role tweaks.
- **Synergy pairs:** about 7% of pairs, with values from −2 to +4.
- **Lane matchups:** 42–58%, from a hash of the two champions.
- **No Riot names or art yet**, which keeps the fan-policy question (section 8) out of the way.

### The sim (ported from the Pick'Em `simGame`)
- **Structures and picks (18 Nov 2026, Luke; research in the main repo, `research/memory/`):**
  - Each lane's outer, inner and inhibitor towers fall in order; an inhibitor needs its lane's three towers down; nexus turrets can only
    be hit while an inhibitor is down; the Nexus needs both nexus turrets and an inhibitor down, and still only falls in the push after a
    won fight. Inhibitors respawn after 5 minutes and nexus turrets after 3 (League wiki), so a base can close again. Pushes take towers
    in any standing lane.
  - Picks: before each mid/late step's fight, a chance of one player caught alone (event type `pick`, one-card clash animation), set so
    picks are 24% of fights before 25:00 and 13% after (98 Worlds games); top laners and mids are caught most. A pick pushes towers but
    can't end the game.
  - Checked on 40 random drafts × 50 games (old v new): blue's win share unchanged (44.9% v 46.4%), game time median 32 → 30 min,
    45+ min 4.1% → 2.8%, kills 20.7 → 20.1, about 1.1 picks and 1.8 nexus turret events a game. The draft screen animations were not
    play-tested (browser pane hidden).
- **Card stats feed team strengths:**
  - Lane: Top, Mid, and Bot+Support.
  - Jungle.
  - Objectives: Jungle, Support and Mid.
  - Teamfight: all 5 cards, plus synergy × 0.25.
  - Late: Top, Bot, Support and Mid.
- **Off-role penalties:** a flex role costs −4 Lane and −2 on other stats; off-role costs −10.
- **Same constants as Pick'Em:** strength scale `K = 0.15`, fight noise `SIM_SD = 5`, and the same `LATE` table (buffs, push, comeback bounty, gold fade).
- **Phases:** laning, then early objectives, then the fight loop. The Nexus only falls after a won fight with an inhibitor down and enough push.
- **Win% is an estimate** from repeated runs: 300 after each pick and 600 before the clash. **The actual game is one separate run**, so the favourite can lose.

**Calibration** (400 random drafts, run in headless Chromium):

| Check | Result | Pro target |
|---|---|---|
| Favourite wins | 62% | Close calls in the 50–70% range |
| Drafts called above 80% | 2% (max 87%) | Rare |
| Average game | 33 min (median 31) | About 32–33 min |
| First Baron team wins | 86% | About 83–85% |
| First Elder team wins | 68% (only 37 of 400 games had an Elder) | About 74–76% |

### Code map (`index.html`, all inline)
| Section | Key names |
|---|---|
| Constants | `ROLES`, `LN`, `COLX(role)` (lane centre x), `HOME` (card y per side), `ORDER`, `KIND`, `PHASE` |
| Champions | `CH[]`, `SYN`, `syn(a,b)`, `matchup(a,b)`, `statOf(cid,role,stat)`, `power`, `teamSyn` |
| Sim | `teamStr`, `simGame(bluePicks, redPicks, quiet)` (returns `{winner,time,ev[],k,tw,dr,ba,el,…}`; each event carries a score snapshot `s`), `winChance(b,r,n)`, constants `K`, `SIM_SD`, `LATE` |
| Sound | `tone()`, `noise()`, `SFX.*` |
| Helpers | `A(el,keyframes,ms,opts)`: a Web Animations wrapper that respects `SPEED` and `SKIP`. Also `sleep`, `rectIn` (stage coordinates), `burst`, `shakeIt`, `bigText` |
| Board | `buildBoard`, `placeCard`, `setWin`, `applySnap` |
| Draft | `newGame`, `flip`, `chooseSide`, `startDraft`, `nextTurn`, `aiChoose` (power + synergy + matchup + flex + noise), `doAction`, `animBan`, `animPick`, `endDraft` |
| Clash | `startClash`, `playEvent`, `clashAnim`, `nudge`, `gank`, `token`, `pushAnim`, `nexus`, `finish`, `sim100` |
| Autosave | `SAVE` (`{v:1, savedAt, settings, game, history}`), `persist()` (called after each draft step, setting change and result; writes browser storage, then the folder after a short debounce), `writeFolder`, `readFolder`, `sanitize`, `applySave`, `restoreGame`, `useFolder`, `folderStatus`, `renderRecord`, `boot()`. The folder handle is stored in IndexedDB (`draftClash`/`kv`/`dir`). Game phases are tracked in `G.phase`: side → draft → ready → clash → result |
| Debug | `window.__dc` exposes `CH`, `simGame`, `winChance`, `teamStr`, `matchup`, `syn` and `SAVE` for console testing |

**Layout:** a fixed 1000×760 "stage" scaled to fit the window. Red cards sit at y 150, Blue cards at y 460, the midline at y 380, and the lane centres at x 225 + 150 × lane.

### Known limits
- Sounds and animation feel haven't been judged by ear or eye yet. They were only checked for errors in a headless browser.
- On a phone it scales down to fit; landscape works much better.
- The AI draft is simple: no counter-picking strategy and no ban planning.
- Single game only (no best-of series or Fearless).
- The stats are invented, so balance is only checked statistically.

### Next steps (pick one)
- [ ] **Play it and list feel tweaks:** animation timings, sound choices, speed.
- [ ] **Real data:** swap the placeholders for Pick'Em `js/champions.js` + `js/data.js` (presence, win rates, real synergy/counters), with an art on/off switch (see section 8).
- [ ] **Tier 2 polish:** GSAP + Howler as local files.
  - Sound packs: Kenney packs need to be **downloaded by Luke** into `Draft Game\assets\`, because Claude's cloud workspace can't reach kenney.nl or opengameart.org.
  - The npm packages for GSAP, Howler and jsfxr *are* reachable from the cloud workspace.
- [ ] **Smarter draft AI:** reuse Pick'Em `draftScore`/`autoStep` logic, or add difficulty levels.
- [ ] **Best-of series** with a Fearless option.

---

## 1. What the game is

- **Style:** a basic 2D card game in the style of Hearthstone, built around League of Legends-style pick/ban.
- **Board:** split in two. The **top half is Red** and the **bottom half is Blue**. Each half has **5 lanes**: Top, Jungle, Mid, Bot and Support.
- **Turn order:** the game follows the standard pro pick/ban order, and **Blue picks first**.
- **Start:** a fun intro animation for the Red/Blue side choice (coin flip).
- **Draft:** a **semi-transparent overlay window** sits over the board, so the board stays visible behind it. Champion portrait tiles inside it are **opaque**. The player picks or bans from that window.
  - **Ban:** the card plays a discard/ban animation.
  - **Pick:** the card animates into its lane on the Red or Blue side.
- **Overlay extras:** a synergy counter and a win% chance.
- **After the draft:** the cards ready up in their lanes, then **bash each other**, moving up and down and crashing at the midline. Then the result is shown.
- **What matters most:** card animations need to be fun and engaging. Sound is a nice extra.
- **Hard rule:** the better win% must **not** decide the game on its own. The result comes from a phase-by-phase simulation (section 6).

**Mockup** (5-state storyboard: side select → draft → board → clash → result): https://claude.ai/artifact/6P3So6DV3MCgcKyuZoLkSB
The mockup fixes where each element sits. The visual style is still open.

---

## 2. What's on this PC (checked 23 Oct 2026, folder names only)

| Found | Not found in the standard install locations |
|---|---|
| Python, VS Code, Git, Google Chrome, Notepad++, DB Browser for SQLite | Node.js, Godot, Unity |

**So the lightest path needs nothing new installed.** A browser game runs from a single HTML file. Python's built-in web server (`python -m http.server`) can serve it, and VS Code edits it. The LOL-Worlds26-Pickems repo already uses this setup (plain HTML/CSS/JS, hosted on GitHub Pages).

---

## 3. Three build tiers (all free and light on disk/CPU)

### Tier 1: Quick test mode, playable right away
**Goal:** a running game in one sitting, so you can test whether the gameplay is fun.

- **Stack:** one `index.html` with plain JS and CSS. Animations use CSS transitions and the browser's built-in **Web Animations API**, so there's no library.
- **Sound:** generated in code with the built-in **Web Audio API**: short oscillator "whoosh/thud/shatter" blips. No sound files.
- **Art:** coloured placeholder tiles with initials, as in the mockup.
- **Flow:** Side select → Draft (20 steps vs a simple AI opponent) → Board → Clash (plays back the sim's event log) → Result.
- **Data:** a small champion list with simple stats, or reuse `js/champions.js` from the Pick'Em repo.
- **Size and running:** under 1 MB, no install. Double-click to open in Chrome.
- **Test mode switches:** "auto-draft both sides", "skip animations", and "run 100 games and show the win split" to check balance.

### Tier 2: Mid quality
Everything in Tier 1, plus:

- **GSAP** (free, about 70 KB, saved as a local file) for punchy timelines: card flips, squash and stretch, staggered lane entries, and screen shake on the crash.
- **Howler.js** (about 30 KB) for sound, using **Kenney audio packs** and **ChipTone**-made effects (CC0, so no credit needed).
- **Kenney UI and Boardgame packs** for card frames and buttons (CC0).
- **Particles:** a small canvas particle effect for the ban shatter and clash sparks.
- **Size and hosting:** about 5–20 MB including assets. It can go on GitHub Pages like the Pick'Em app.

### Tier 3: Higher quality
- **Phaser 4 (recommended):** a single JS file of about 1–2 MB, still with no install. It has built-in tweens, particle emitters, camera shake, audio, scenes and input. It's the best quality for the weight, and you keep the same browser and GitHub Pages workflow.
- **Godot 4.6 (optional alternative):**
  - **Pros:** GDScript reads like Python, it has the strongest animation editor (AnimationPlayer plus Tween), and it can export a Windows .exe or a web build.
  - **Cons:** it's a separate app of roughly 100–150 MB (portable, no installer), plus a new editor to learn.
- **Skip for this project:**
  - **Unity:** a multi-GB install, C#, and slow for a one-person prototype.
  - **Streamlit:** reruns the whole script on every click and has no animation loop.

**Suggested route:** start with Tier 1. Upgrade the same codebase to Tier 2 by adding GSAP, Howler and assets. Only move to Phaser if you need more than that.

---

## 4. Draft order (20 steps, Blue first)

| Steps | Phase | Order |
|---|---|---|
| 1–6 | Ban phase 1 | B R B R B R |
| 7–12 | Pick phase 1 | B R R B B R |
| 13–16 | Ban phase 2 | R B R B |
| 17–20 | Pick phase 2 | R B B R |

- **First Selection (2026 pro rule):** the team that earns it chooses either its side or first/last pick, so Blue doesn't always pick first. The sequence itself is unchanged. This game uses the classic "Blue picks first" version.
- **Fearless Draft** only matters for best-of-3 or best-of-5 series: a champion picked earlier in the series can't be picked again by either team. Possible later mode.

---

## 5. Reusable pieces from the LOL-Worlds26-Pickems repo
These are in `C:\Users\Ruth\Documents\GitHub\LOL-Worlds26-Pickems`:

| File | What to reuse |
|---|---|
| `js/champions.js` | Pro data for 165 champions: presence, win rates, roles, flex picks |
| `js/data.js` | Synergy pairs (`SYN`), counters/matchups, meta tiers |
| `js/core.js` | `simGame()`, `teamStr()`, `champMod()`, `draftScore()`, draft AI (`autoStep`), win% from repeated sims (`analysis()`) |
| `js/assets.js` | Data Dragon portrait loader with an on/off switch (`ASSETS.icons = false` shows initials instead) |
| `research/backtest-2026.md` | Calibration lessons (below) |

---

## 6. How to simulate a game (based on the Pick'Em sim research)

### Key principle: win% is shown but doesn't decide the result
- **The overlay number:** run the full sim a few hundred times in the background (the Pick'Em app uses 600) and show the share of wins. That's the "win% chance" overlay.
- **The real result:** one **separate** run of the same sim, with its own randomness. A 60% favourite loses about 4 games in 10. That's intended.

### Lessons from the back-test (711 real 2026 pro series)
- **Keep favourites honest.** The first version of the sim called many matchups 90%+, but those favourites won only 68% of the time. Shrinking the strength scale (`SIMK` 0.3 → 0.15) fixed it.
  - **Rule of thumb:** almost no matchup should sim above about 80%.
  - Calls in the 50–70% range should land close to how often the favourite really wins.
- **Fights are noisy on purpose.** Each fight has random spread (`SIM_SD = 5`) on top of the strength difference.
- **Gold leads fade.** A lead counts for less after about 28 minutes, and the team that's behind earns **bounty gold** when it wins a fight. One lucky late fight shouldn't decide the game, and neither should an early lead.
- **Targets to tune to** (LCK 2026):
  - Average game about 32–33 minutes.
  - Team taking the first Baron wins about 83–85%.
  - Team taking the first Elder wins about 74–76%.

### Card stats (one champion card = one lane)
The Pick'Em sim gives each player and pick a few strength ratings. For the card game, the champion card carries them directly:

| Stat | Used in |
|---|---|
| **Lane** | the laning duel in that lane (Bot and Support average together as the bot 2v2) |
| **Jungle / gank** | jungle duel, and a gank bonus added to one random lane |
| **Objective control** | dragon, grubs, Herald and Baron contests (from the Jungle, Support and Mid cards) |
| **Teamfight** | mid-game fights, plus **synergy × 0.25** from the drafted pairs |
| **Late game** | late fights (from the Top, Bot, Support and Mid cards) |

**Card modifiers:**
- Meta strength from presence (+0.5 to +2).
- Win rate shrunk toward 50% for small samples (n/(n+40)), capped at ±1.5.
- **Counter/matchup bonus** in its own lane.
- Fading champions count for less.

### Game phases → clash animation beats
1. **Laning (0–14 min):** each lane rolls *lane difference + random spread + matchup*.
   - A big win gives a solo kill, which plays as a **lane crash animation**.
   - A small win gives a CS lead, which plays as a **nudge**.
   - The jungle duel can add a gank to one lane.
2. **Early objectives:** dragons, Void grubs and Herald. Odds come from objective control plus the gold lead.
3. **Fight loop (from 15 min until someone wins, or 62 min):**
   - Each fight happens at whichever objective has been up longest: dragon, Baron, or Elder after a dragon soul.
   - The fight roll is *teamfight/late mix + fading gold lead + Baron/Elder/soul bonus + random spread*.
   - The winner takes kills, gold and the objective, with a small steal chance. Then it pushes towers.
4. **Ending:** a team can only destroy the Nexus by **winning a fight while an inhibitor is down and it has enough push** (gold lead, Baron or Elder buff). So the losing team always gets comeback chances.
5. **Event log → animation:** each sim event (lane win, gank, objective, fight, inhibitor, Nexus) is one animation beat. The "bash" sequence plays the log back lane by lane, then the result banner shows.

---

## 7. Free assets and sound

| Source | What | Licence |
|---|---|---|
| Kenney (kenney.nl) | UI pack, Boardgame pack, audio packs | CC0, no credit needed |
| ChipTone (sfbgames.itch.io/chiptone) | Make your own effects in the browser | Output is CC0 |
| jsfxr / sfxr | Retro effect generator | Free |
| Freesound (freesound.org) | Real recorded effects | CC0 / CC-BY / CC-BY-NC, so use the licence filter |
| OpenGameArt / itch.io free assets | Card frames, effects | Varies per item, so check each one |
| Pixabay Music / Incompetech | Background music | Pixabay needs no credit; Incompetech is CC-BY (credit required) |

---

## 8. Champion art and the legal catch

- **Data Dragon** (Riot's free CDN) has every champion's name, portrait and splash art:
  - `ddragon.leagueoflegends.com/api/versions.json`
  - `/cdn/{ver}/data/en_US/champion.json`
  - `/cdn/{ver}/img/champion/{id}.png`
  - Note that Wukong's id is `MonkeyKing`.
- **Riot's fan-project policy ("Legal Jibber Jabber") says: "We prohibit the use of our IP in games and apps."** A free fan *game* using champions isn't covered, even if it's free.
  - A **private prototype only you play** is low-risk in practice, but it's still not permitted.
  - **If it's ever shared, swap in original names and art.** Build it with an art on/off switch from day one (like `ASSETS.icons` in the Pick'Em app).

---

## 9. Open decisions

- [x] Which tier to start with: **Tier 1, built** (see section 0)
- [ ] Champion pool: placeholders (current), the Pick'Em data, or original characters
- [ ] AI opponent strength for the draft (currently simple greedy + noise; option: the Pick'Em draft AI)
- [ ] Where the project lives: currently `LOL-Worlds26-Pickems\Draft Game\`, so it publishes with the Pick'Em GitHub Pages site. Could move to its own repo later
- [ ] Single game only, or best-of series with a Fearless option

## 10. Sources

- Engines: phaser.io (Phaser 4.2.1, Jul 2026), Godot 4.6 release notes (gamefromscratch.com), GSAP free licence (webflow.com/blog/gsap-becomes-free), Unity Personal terms (unity.com).
- Draft order: LoL Wiki "Team drafting". First Selection: esports.gg and GosuGamers. Fearless: lolesports.com.
- Riot policy: riotgames.com/legal-jibber-jabber. Data Dragon: hextechdocs.dev/data-dragon.
- Assets: kenney.nl, freesound.org, opengameart.org, sfbgames.itch.io/chiptone.
- Sim research: `README.md` (repo root), `research/backtest-2026.md`, `research/pro-meta-findings-2026-10-20.md`, `js/core.js` (simGame).
