# Pro meta research — NerfPlz picks/bans and champion pages

Fetched 20–21 Oct 2026. Now wired into the app through `js/champions.js` (165 champions: picks/bans tables merged with 78 harvested NerfPlz champion pages and the 2026 pro game index) — it drives meta tiers, champion cards, draft scoring, the draft AI, the game sim and the tournament's starting presence.
Structured data: [`pro-meta-2026-10-20.json`](pro-meta-2026-10-20.json).

## Source and data rules

- **Source:** [NerfPlz pro picks and bans](https://www.nerfplz.com/lol-pro-meta/picks-bans/), [overview](https://www.nerfplz.com/lol-pro-meta/), [solo queue vs pro](https://www.nerfplz.com/lol-pro-meta/solo-vs-pro/), [off-meta picks](https://www.nerfplz.com/lol-pro-meta/off-meta/), [games](https://www.nerfplz.com/lol-pro-games/), [champion pages](https://www.nerfplz.com/lol-pro-builds/). Underlying data is Leaguepedia (CC BY-SA 3.0); site updated 19 Oct.
- **Priority (as requested):** latest pro patch **26.20** and **patches 26.16–26.20** are the main data; the **2026 season** is tertiary.

| Sample | Games | Use |
|---|---|---|
| Latest pro patch 26.20 | 25 | Main — freshest, but tiny (1 game = 4%) |
| Patches 26.16–26.20 | 465 | Main — the reliable core |
| 2026 season | 2,723 | Tertiary — long-run comfort and trend baseline |

- **Proposed blend for app presence:** 0.9 × (26.20 weighted 4× + 26.16–26.20 by games) + 0.1 × season. Champions only in the season table are decayed to 40% and flagged. Each table shows only its top ~30, so a champion missing from a table counts as 0 there (slight undercount).
- **Caveats found:**
  - Champion pages count far more games per patch than the picks/bans tables (e.g. Rumble "146 games on 26.20", Vi 110) — they include lower leagues and their "latest patch" window varies (Ryze's page showed 26.15–26.17). **Use champion pages for builds and player usage only, never for presence.**
  - The page doesn't print presence or sample labels on every table; samples were confirmed from pick counts (6 picks = 24% → 25 games; 465 and 2,723 stated on the overview).
  - No side win rate, game length, or first-pick data is published on these pages.

## Most contested now (blended presence)

| Tier | Champions (blended presence %) |
|---|---|
| Must-ban | Nocturne 78, Cassiopeia 77, Vi 65 |
| Priority | Orianna 57, Jarvan IV 52, Ezreal 52, Olaf 50, Akali 47, Lucian 46, Rumble 42, Lee Sin 42, Pantheon 41 |
| Meta | Nautilus 40, Jayce 40, Seraphine 40, Syndra 37, K'Sante 36, Bard 36, Renata 36, Caitlyn 35, Ryze 35, Karma 34, Lulu 34, Gnar 32, Poppy 30 |
| Situational | Naafiri, Qiyana, Viktor 29 · Locke 27 · Ambessa, Maokai, Rakan, Sylas, Yone 25 · Jhin 25 · Vayne 24 · Yunara 24 · Skarner, Xayah 22 · Milio 19 · Ashe, Zaahen 18 |
| Fading (season-only) | Varus 23, Xin Zhao 14, Neeko 12, Renekton 11, Corki 8 |

## Movement (26.16–26.20 presence vs season)

- **Rising:** Cassiopeia +47 (82% banned on 26.16–20, nerfed on 26.20 but still 24% banned and 4-0 on 26.20), Nocturne +19, Vi +16, Lucian +15, Seraphine +10, Ezreal +7, Akali +7, K'Sante +6.
- **Falling:** Rumble −18 (still 25% picked, 59% WR), Orianna −15, Bard −11, Nautilus −9, Jayce −9, Karma −7, Yunara −6.
- **Dropped out of recent top lists:** Xin Zhao (23% picked in season), Corki, Renekton, Varus (43% banned in season), Neeko. Relevant because several Worlds players list these as comfort picks (e.g. Canyon/Oner/SkewMond Xin Zhao, Hope Varus/Corki).
- **New on 26.20:** Qiyana (20% picked, 60% WR), Zaahen (20%, 80%), Rakan, Xayah, Ashe, Viktor up to 20% picks.

## Win-rate signals (show with sample flags)

| Signal | 26.16–26.20 (465) | 26.20 (25) |
|---|---|---|
| Strong | Seraphine 61%, Rumble 59%, Vi 57%, Nocturne 57%, Ezreal 54% | Vi 5-1, Seraphine 4-1, Olaf 4-1, Viktor 4-1, Zaahen 4-1, Cassiopeia 4-0, Gnar 3-0 |
| Weak | Bard 33%, Naafiri 38%, Jayce 39%, Caitlyn 39%, Locke 41%, Milio 43%, Lucian 44%, Olaf 44% | K'Sante 0-6, Renata 0-3, Pantheon 0-2, Sylas 0-2, Yone 0-2 |

Takeaways for drafting: K'Sante is still picked as a safe blind (24% on 26.20) but has lost every game since his nerf; Lucian and Jayce are popular but lose more than they win; Seraphine and Vi are high-presence *and* winning — real priority picks.

## Flex picks (roles from pick counts)

Jayce (top/jungle/mid), Ambessa (top/jungle), Zaahen (top/jungle), Yone (mid/top), Poppy (jungle/support/top), Seraphine (support/bot), Syndra (mid/bot), Varus (bot/top), Cassiopeia (mid/bot), Akali (mid/top/bot), Olaf (top/jungle). Flex picks are worth extra in early pick phases because they hide the role.

## Pro-only vs solo queue

Picked/banned far more in pro than solo queue (26.20): Rumble (28%/12% pro vs 2%/0% solo), Renata (12/28 vs 1/0), Orianna (8/28 vs 3/0), Olaf, K'Sante, Vi, Jarvan IV, Cassiopeia, Gnar. These are coordination picks — their solo-queue synergy/counter numbers in the app understate them.
Solo-queue staples absent from pro: Yasuo, Master Yi, Shaco, Zed, Teemo, Lux, Jinx, Morgana, Blitzcrank (Malphite 4% pro). Counter/synergy lists should demote these.

## Off-meta picks (2026, newest first, 61 shown: 29-32)

- **Taliyah bot** is the standout trend: 15 games (e.g. Peyz 10/0/6 win, Berserker win, Smash loss, Duduhh win, Eddie, Harky, Doggo).
- **Seraphine bot** (Ruler twice, both wins), **Kai'Sa top** (Bin, Clear), **Rumble/K'Sante mid** (Faker win, Chika at Worlds), **Akali bot** (Duduhh, Eddie, Supa, Viper), **Jayce bot/mid** (Berserker, Knight).
- Worlds players with off-meta history: Peyz, Ruler, Smash, Bin, Faker, Knight, Viper, Berserker, Duduhh, Eddie, Doggo, Supa, Harky, Chika, Ayu.

## Champion profile notes (champion pages)

| Champion | 2026 pro games (W%) | Core build / keystone | Worlds play-in users |
|---|---|---|---|
| Vi | 801 (53%) | Conqueror; Trinity Force, Mercury's Treads, Black Cleaver, Guardian Angel | Gury 2-0, Tatu, Yike, Curse (CBLOL) — undefeated at Worlds |
| Jarvan IV | 993 (51%) | Conqueror; Sundered Sky, Plated Steelcaps, Black Cleaver, Guardian Angel | Gury, Tatu, Yike, Blaber |
| Ryze | 1,026 (51%) | Deathfire Touch; Rod of Ages, Actualizer, Zhonya's | Saint 3-0, Tutsz, Feisty, Jojopyun 0-2 (recent list) |
| Rumble | 951 (52%) | Deathfire Touch; Liandry's, Bloodletter's Curse, Zhonya's | Kratos 1-1, Guigo, Thanatos, Canna, Chika (mid) |
| Ezreal | 965 (51%) | Lethal Tempo; Trinity Force, Endless Hunger, Spear of Shojin | Caliste 1-0, Harky 1-1, Tactical 1-1 |

Not published on champion pages: matchup or synergy tables, aggregate player stats (recent-games lists are truncated, so player tallies are partial).

## Gaps versus the current app data (`js/data.js`)

- `CH` (meta list) only holds the 22-game play-in table. Missing high-relevance champions from 26.16–26.20: **Karma, Jhin, Yunara, Bard, Nautilus, Poppy, Qiyana**; Ryze's estimate (42) can be replaced with real numbers (26% picked, 13% banned, 52% WR).
- Presence drives meta tiers, draft scoring, AI drafting and the game sim's champion bonus — all should switch to the blended presence.
- Win rates aren't used in draft scoring yet; add them with a sample-size discount (e.g. shrink toward 50% by n/(n+40)).
- Comfort picks for players should be checked against "fading" champions so tooltips can warn when a favourite has dropped out of the meta.

## Proposed features for the next update

1. **Champion profile card** (hover + Meta tab): presence for 26.20 / 26.16–20 / season with a trend arrow, win rate with a sample flag, roles and flex value, pro-only vs solo-queue flag, core build and keystone, Worlds users and off-meta history, plus the existing synergies/counters.
2. **Meta tier list** rebuilt on the blended presence with a "rising / falling / fading" filter and win-rate column.
3. **Draft AI**: value flex picks early, avoid blind picks with collapsing win rates (K'Sante on 26.20), weigh win rate as well as presence, and demote solo-queue-only counters.
4. **Tournament stats pool**: start from the blended presence instead of the 22 play-in games, so early simulated drafts reflect the real 26.16–26.20 meta.
5. **Off-meta flag** in champ select when a player has a pro history with an off-role pick (e.g. Peyz Taliyah, Ruler Seraphine).
