# Draft Pick/Ban Card Game — Project Handoff

*Last updated: 23 Oct 2026. To pick up where we left off, paste or attach this file in any new chat.*

> **Resume prompt:** "Here's my handoff file for the draft pick/ban card game. Read it, then help me with: ___"

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

- [ ] Which tier to start with (Tier 1 recommended)
- [ ] Champion pool: placeholders, the Pick'Em data, or original characters
- [ ] AI opponent strength for the draft (random, meta-greedy, or the Pick'Em draft AI)
- [ ] Where the project lives (new repo next to LOL-Worlds26-Pickems?)
- [ ] Single game only, or best-of series with a Fearless option

## 10. Sources

- Engines: phaser.io (Phaser 4.2.1, Jul 2026), Godot 4.6 release notes (gamefromscratch.com), GSAP free licence (webflow.com/blog/gsap-becomes-free), Unity Personal terms (unity.com).
- Draft order: LoL Wiki "Team drafting". First Selection: esports.gg and GosuGamers. Fearless: lolesports.com.
- Riot policy: riotgames.com/legal-jibber-jabber. Data Dragon: hextechdocs.dev/data-dragon.
- Assets: kenney.nl, freesound.org, opengameart.org, sfbgames.itch.io/chiptone.
- Sim research: `LOL-Worlds26-Pickems/README.md`, `research/backtest-2026.md`, `research/pro-meta-findings-2026-10-20.md`, `js/core.js` (simGame).
