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
| Champ select | Series mode: pick your team, opponent, Bo1/Bo3/Bo5, Fearless or standard and game 1 side; the AI drafts the opponent by default (2 s per action). Competitive draft order, suggestions, draft review and a simulated game with Player of the Game. The series ends at 1/2/3 wins; a series panel shows the score, every game, each player's champions, K/D/A, KDA, average rating and POG points, the Series MVP race and series stats. Hover a player for their pool and lane risk, a team name for its comp, or a champion for its pro card. |
| Teams / Top–Support | Player power bars, head-to-head and tier lists. Hover a player for their champion pool. |
| Meta | Champion tier list from blended pro pick/ban presence (26.20 + 26.16–26.20) with win rate and rising / falling / fading filters, bot-lane duo grid, best partners, counters. |

## Themes

The look is an "Arena HUD" style (Chakra Petch and Rajdhani type, clipped panels, thick stat bars). Top-right of the page: the **ⓘ** icon shows how ratings are made and every source; the sun/moon button switches light and dark mode; **Worlds mode** swaps in one of three event colour themes — *Hextech Gold*, *Brooklyn Final* or *Summoner's Cup*. Choices are remembered in the browser.

Champion square icons load from Riot's Data Dragon CDN; set `ASSETS.icons = false` in `js/assets.js` to turn them off (tiles then show initials). Teams are shown as colour badges; the app uses no team or Riot logos. The trophy on the winners screen is an original design.

## How the tournament works

- **Schedule:** Swiss R1 23 Oct, R2 24 Oct, R3 25–26 Oct, R4 28–30 Oct, R5 31 Oct; quarter-finals 3–6 Nov, semi-finals 7–8 Nov, final 14 Nov. How multi-day rounds split between days isn't published, so that split is assumed.
- **Format:** 16-team Swiss; 3 wins advance, 3 losses out. Round 1 uses the real draw. Advancement and elimination matches are Bo3 (Fearless), others Bo1. Quarter-finals: the two 3-0 teams play 3-2 teams on opposite halves; knockouts are Bo5 Fearless.
- **Sides:** game 1 blue side goes to the higher seed (round 1) or higher-rated team; after that the loser of each game takes blue (First Selection, picking first).
- **Live data pool:** every simulated game adds champion picks, bans and wins, and each player's champions and stats. Draft suggestions, champion presence and player comfort picks blend this with the pre-Worlds data, weighting the tournament more as games are played.
- **Game simulation:** each game plays laning, dragons/grubs/Herald, then fights over dragons, Baron and (after a dragon soul) Elder Dragon. Winning fights takes towers and inhibitors; a team ends the game only by winning a fight with an inhibitor down and enough push (gold lead, Baron or Elder buff). Gold leads count for less as games go long and the team behind earns bounty gold, so one lucky late fight doesn't decide a game. Tuned to LCK 2026: about 32-minute games, the Baron team wins about 85%, the Elder team about 75%. Win odds are calibrated against 711 real 2026 pro series (see `research/backtest-2026.md`); those results are used only for that test, not for Worlds stats.
- **Player of the Game:** one per game, normally from the winning side (a losing player can take it if their rating beats the winners' best by 1.1+, under 1% of games), using a 0–10 game rating built from what separates LCK POG winners — the result, KDA and deaths, kill participation, damage share against the role's norm, CS lead at 15, solo kills, vision (supports) and objectives (junglers and supports). Each POG earns 100 POG points, as in the LCK. The rating is role-balanced: in testing, mid wins about 28% of POGs, top and jungle about 20% each, ADC about 20% and supports about 10%.
- **Awards:** Swiss stage MVP (most Swiss POG points), Tournament MVP (most POG points overall), Finals MVP (best rating on the winning team in the final), All-Tournament team (best average rating per role).
- **Winners screen:** after the final — trophy, the world champions' roster card, the champion team of the tournament (best win rate per role, with a minimum number of games), storylines (biggest upset, Cinderella run, longest game, most banned and picked, flawless runs, best single game) and award cards.
- **What's shown vs what's used:** player and champion cards show this tournament's numbers first, with 2026 pro numbers dimmed in brackets. Draft suggestions, the AI and the simulation use the full pro research (blended presence, sample-adjusted win rate, flex picks, trends).
- **Saving:** progress saves automatically in your browser (localStorage), so you can close the page and continue later on the same browser. Use **Download run file** / **Import run file** to move a run between devices or browsers.

## Project structure

```
index.html          page markup
css/styles.css      styles (light and dark themes)
js/ui.js            theme toggle, Worlds mode, info popover
js/data.js          teams, ratings, champion pools, meta, synergy, counters, play-in drafts
js/champions.js     pro data for 165 champions (presence, win rates, roles, builds, play-in users)
js/assets.js        champion icons (Data Dragon, with on/off switch) and team colours
js/tournament.js    tournament engine, stats pool, POG and awards, tournament UI
js/core.js          views, tier lists, meta, champ select, draft AI, game simulation
```

To update data (e.g. real results or new stats), edit `js/data.js`.

## Data sources

- Format, dates, teams: Wikipedia (2026 League of Legends World Championship), Inven Global, accountshark.net; round 1 draw: Dot Esports, Insider Gaming.
- Player rankings: Hotspawn and Strafe role rankings; Sheep Esports "meet the players".
- Champion pools: mid.gg player pages; Sheep Esports player pages (LOS).
- Meta: NerfPlz pro picks and bans (26.20, 26.16–26.20, 2026 season), NerfPlz champion pro-build pages, NerfPlz Worlds 2026 picks and bans; DPM.LOL. Details in `research/`.
- Champion icons: Riot Data Dragon.
- Synergy: metabot.gg duos and METAsrc duo/synergy pages (patch 26.20, ranked solo queue).
- Counters: METAsrc counter pages (ranked solo queue, patches 26.17–26.20).
- Draft rules: Sheep Esports and esports.gg on First Selection; Nerdbot on first vs last pick.
- POG / MVP: Namuwiki (LCK Awards: POG points), LeagueLab metrics guide, Team Liquid "statistical standouts".

Ratings, simulations and awards are estimates for fun and Pick'Em research, not predictions.

## Licence and legal

- **Code:** MIT licence (see `LICENSE`) — free to reuse with credit.
- **Data:** stats belong to their sources (credited above and in the app's ⓘ panel). Leaguepedia data is used under CC BY-SA 3.0. The MIT licence covers the code, not third-party data.
- **Riot Games:** Worlds 2026 Pick'Em Lab is a free fan project. It isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games and all associated properties are trademarks or registered trademarks of Riot Games, Inc. The app uses no Riot logos or artwork and must stay free and non-commercial.

## Privacy and safety

- No accounts, analytics, cookies or server: tournament runs and theme choices stay in each visitor's own browser (localStorage).
- Fonts load from Google Fonts and champion icons from Riot's Data Dragon CDN, so browsers contact Google and Riot.
- Imported run files are treated as untrusted: every field is checked against known teams, roles, champions and match ids, numbers are clamped, display text is regenerated, and standings and stats are recomputed from the games. Files over 2 MB or that don't fit are rejected.
