# Worlds 2026 Pick'Em Lab

A browser app for League of Legends Worlds 2026: simulate the whole event on the real format and draw, draft games yourself in a competitive champ select, and track Player of the Game, MVP points and awards. It also has player power bars, role tier lists, and a meta / synergy / counter reference.

No build step and no server: it's plain HTML, CSS and JavaScript.

## Run it

- **Locally:** open `index.html` in a browser.
- **Online (GitHub Pages):** see below.

## Publish with GitHub Desktop + GitHub Pages

1. In GitHub Desktop: **File → Add local repository…** and choose this folder (`LOL-Worlds26-Pickems`). If it says the folder isn't a repository, click **create a repository** and keep the name.
2. Commit the files (summary e.g. `Initial version of Worlds 2026 Pick'Em Lab`), then click **Publish repository**. Untick "Keep this code private" if you want a free public Pages site.
3. On github.com, open the repo → **Settings → Pages** → under *Build and deployment* choose **Deploy from a branch**, branch **main**, folder **/ (root)** → **Save**.
4. After a minute the site is live at `https://<your-username>.github.io/LOL-Worlds26-Pickems/`.

Later changes: edit files, commit in GitHub Desktop, **Push origin** — Pages updates automatically.

## Tabs

| Tab | What it does |
|---|---|
| Tournament | Worlds 2026 from Swiss round 1 (23 Oct) to the final (14 Nov). Three modes: **My teams** (draft for 1–4 teams, AI plays the rest), **Sim run** (all AI), **My team + guest picks** (your team plus a random side in every other match, with a switch to let the AI play until your team is up). |
| Champ select | Free-play draft in competitive order, Bo1 or Fearless, optional AI opponent (2 s per action), suggestions, draft review, and a simulated game with a Player of the Game. |
| Teams / Top–Support | Player power bars, head-to-head and tier lists. Hover a player for their champion pool. |
| Meta | Champion tier list from Worlds pick/ban presence, bot-lane duo grid, best partners, counters. |

## How the tournament works

- **Schedule:** Swiss R1 23 Oct, R2 24 Oct, R3 25–26 Oct, R4 28–30 Oct, R5 31 Oct; quarter-finals 3–6 Nov, semi-finals 7–8 Nov, final 14 Nov. How multi-day rounds split between days isn't published, so that split is assumed.
- **Format:** 16-team Swiss; 3 wins advance, 3 losses out. Round 1 uses the real draw. Advancement and elimination matches are Bo3 (Fearless), others Bo1. Quarter-finals: the two 3-0 teams play 3-2 teams on opposite halves; knockouts are Bo5 Fearless.
- **Sides:** game 1 blue side goes to the higher seed (round 1) or higher-rated team; after that the loser of each game takes blue (First Selection, picking first).
- **Live data pool:** every simulated game adds champion picks, bans and wins, and each player's champions and stats. Draft suggestions, champion presence and player comfort picks blend this with the pre-Worlds data, weighting the tournament more as games are played.
- **Player of the Game:** one per game, from the winning side, using a 0–10 game rating built from what separates LCK POG winners — the result, KDA and deaths, kill participation, damage share against the role's norm, CS lead at 15, solo kills, vision (supports) and objectives (junglers and supports). Each POG earns 100 POG points, as in the LCK.
- **Awards:** Swiss stage MVP (most Swiss POG points), Tournament MVP (most POG points overall), Finals MVP (best rating on the winning team in the final), All-Tournament team (best average rating per role).
- **Saving:** progress saves automatically in your browser (localStorage), so you can close the page and continue later on the same browser. Use **Download run file** / **Import run file** to move a run between devices or browsers.

## Project structure

```
index.html          page markup
css/styles.css      styles (light and dark themes)
js/data.js          teams, ratings, champion pools, meta, synergy, counters, play-in drafts
js/tournament.js    tournament engine, stats pool, POG and awards, tournament UI
js/core.js          views, tier lists, meta, champ select, draft AI, game simulation
```

To update data (e.g. real results or new stats), edit `js/data.js`.

## Data sources

- Format, dates, teams: Wikipedia (2026 League of Legends World Championship), Inven Global, accountshark.net; round 1 draw: Dot Esports, Insider Gaming.
- Player rankings: Hotspawn and Strafe role rankings; Sheep Esports "meet the players".
- Champion pools: mid.gg player pages; Sheep Esports player pages (LOS).
- Meta: NerfPlz Worlds 2026 picks and bans (patch 26.20); DPM.LOL.
- Synergy: metabot.gg duos and METAsrc duo/synergy pages (patch 26.20, ranked solo queue).
- Counters: METAsrc counter pages (ranked solo queue, patches 26.17–26.20).
- Draft rules: Sheep Esports and esports.gg on First Selection; Nerdbot on first vs last pick.
- POG / MVP: Namuwiki (LCK Awards: POG points), LeagueLab metrics guide, Team Liquid "statistical standouts".

Ratings, simulations and awards are estimates for fun and Pick'Em research, not predictions.
