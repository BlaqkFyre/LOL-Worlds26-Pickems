# Making comps matter: options and how to test them

Written 5 Nov 2026 (AEST) for Luke ("we want draft styles/comps to matter by the end"). Nothing here is built; it lists the ways a draft could earn a real effect on who wins, each with a held-out test. Luke picks which to try. Background: `research/sim2-report.md` (Part 2), `research/sim2/README.md` steps 11–12, `research/sim3-report.md`.

## What we know so far

- **Comp style is real but weak.** A draft's siege, objectives and pace style predicts a little of how the game goes beyond team strength (correlations 0.14, 0.18, 0.16 from 1 Sep; skirmish 0.05). Champion styles only partly carry over from one period to the next (0.28–0.29; skirmish 0.07), so each champion's style is noisy.
- **As a direct "who wins" input, every style failed** (session 2: each alone on v1, none better on all of Jul–Aug, from 1 Sep and Worlds). Team "scaling" also failed: the more-scaling side does not win more of the long games (−0.01).
- **In the game sim, how a style is used matters** (session 3, held out, 200 sims per game):

| Draft styles in the sim | From 1 Sep | Worlds |
|---|---|---|
| Decide who gets kills, monsters, towers (own minus enemy) | 0.650 | 0.675 |
| Off | 0.646 | 0.642 |
| **Timing only** (both drafts together set the pace) | 0.646 | **0.635** |
| v1 | 0.644 | 0.646 |

- **Lesson:** a style that hands one side an edge outright makes the odds worse. One that only shapes the game (how many fights, how fast sieges go) makes them a little better, because the game plays out more like the real one. So the promising options are ones where a comp changes **how the game unfolds**, and who that favours comes out of the game state, not out of a fixed bonus.

## Options (each one tested the same way)

**Test rule for every option:** fit on games before 1 Sep. Judge on games from 1 Sep and all Worlds games (held out), against the current timing-only sim. Keep the option only if it improves both, or improves one and doesn't hurt the other. The knockout games are a fixed final check, as with the v2 candidate: fix the option before the next knockout file and don't change it afterwards. Few parameters per option (1–3).

| # | Option | What it means in a game | Data and fit | Cost | Notes |
|---|---|---|---|---|---|
| A | **Comp turns a lead into results** (state-dependent style) | A siege draft that is ahead takes towers faster; an objective draft that is ahead takes dragons more surely. Behind, the style does little | Interaction terms in the tower-segment and monster-taker fits: own style × own lead. Timelines, training games | Small (2–3 terms in fits that exist) | Who it favours comes from the game state, not a flat bonus. **My first pick** |
| B | **Pro lane matchups in laning** | A champion pair's pro lane record moves the lane result (session 2: top 0.30, jungle 0.27 link with the later lane) | Add the pair's earlier pro record (16.15+) to the lane model; one weight per role | Small | Flows into gold, then into everything else. Lane inputs are a small part of the sim now (ablation) |
| C | ~~Damage and frontline balance~~ **Tested 5 Nov: not supported, not kept** | A comp with almost no magic damage, one damage type, or no frontline does worse | See "Option C result" below | — | Pro data can't measure extreme drafts (pros never draft them), so the sim gets no penalty for them |
| D | **Team habits × comp** | A team that usually sieges well gets more from a siege draft (comfort at the comp level, like jungle comfort at big events) | Each team's earlier style shares (results minus v1) × its draft's style | Medium | Session 2 found comfort effects only at big events, so expect a small effect |
| E | **Styles from the current meta only** | Champion styles learned on 16.15+ (Luke's current-meta principle) instead of the whole season | Refit `s3_comp.py` on 16.15+ training games; shrink harder | Small | Fewer games per champion, so noisier; worth one run |
| F | **Comp plan v comp plan** | Matchups between plans, not plan strength: for example the common idea that engage beats poke and poke beats slow scaling comps (not measured here) | 3 pairwise style interactions in the fight-side fit | Medium | Needs many games to see; risk of fitting noise |
| G | **Champion strength on the current patch** (role by role) | A strong ADC pick helps (session 2: ADC champion strength passed role by role, a candidate) | Patch-weighted pro win rate after v1, shrunk hard; ADC first | Small | Session 2: whole-season strength didn't carry over after the meta moved |

## Option C result (5 Nov): the "balanced comp" idea, checked against data

Luke's rule: the sim mustn't add or leave out an effect because of an AI assumption. So this common belief was tested before anything was built. Script `research/sim3/s3_dmgmix.py`, output `research/model/sim3/dmgmix.json`.

**Labels from outside sources, not judgement:**
- **Damage type and frontline:** Riot's own client tags (Magic / Physical / Mixed) and class roles (frontline = Vanguard or Warden), read from the official League wiki's `Module:ChampionData/data` (https://wiki.leagueoflegends.com/en-us/Module:ChampionData/data, read 5 Nov in the browser pane; saved as `research/model/sim3/wiki_champ_tags.csv`, wiki content CC BY-SA). Evelynn, Katarina and Renata Glasc have no damage tag there and count as unknown. Every champion played in the pro file is in the table.
- **Cross-checks:**
  - The app's hand-made `CHAMP_AP` list agrees with Riot's tags on 141 of 155 pro champions. It differs on Sion, Poppy, Smolder and Skarner (app magic, Riot physical) and on Braum, Thresh, Blitzcrank and Locke (app physical, Riot magic).
  - Riot Data Dragon's 0–10 "magic" rating (16.22.1) averages 7.2 for magic-tagged champions and 3.0 for physical ones but overlaps too much to label with (Jhin and Ezreal are rated 6).

**Results** (major-league games; each team's win compared with v1's pre-game odds; ± one standard error):

| Draft | Before 1 Sep | From 1 Sep | Worlds |
|---|---|---|---|
| Only one damage type | 0 of 4,714 sides | 0 of 476 | 1 of 160 (won) |
| At most 1 magic champion | 109 sides, +6.4 pts (± 4.8) | 4 sides | 1 side |
| No frontline (no Vanguard or Warden) | 2,074 sides (44%), **0.0 pts** (± 1.1) | 225, +1.7 (± 3.3) | 60, +12.3 (± 6.3) |

| As a who-wins input on v1 (log loss) | Before 1 Sep | From 1 Sep | Worlds |
|---|---|---|---|
| v1 | 0.6418 | 0.6504 | 0.5861 |
| + magic count | 0.6413 | 0.6478 | 0.5903 (worse) |
| + low magic | 0.6412 | 0.6521 (worse) | 0.5854 |
| + no frontline / frontline count | 0.6418 | 0.6504 / 0.6505 | 0.5860 / 0.5867 |

- **One damage type never happens in pro play**, so pro data can neither show nor disprove that it's bad.
- **Low magic and no frontline don't do worse** in the games where they happen. Nearly half of pro drafts have no frontliner, and they win exactly as expected.
- **No damage or frontline term improves who-wins on both held-out sets. Not kept.**
- **Caveat:** pros avoid lopsided drafts, so these games say nothing about how bad an *extreme* draft would be. The sim therefore gets no penalty for one: there's no data for one, and inventing one would break Luke's rule.
- **App flag:** the team hover card says "one damage type, easy to itemise against" (`js/core.js` `teamTip`, from the hand-made list). It's display only, but untested and about a situation pro games never show. Decide in session 4 whether to remove it, reword it as a note without a claim, or keep it.

**Published evidence looked for (5 Nov):**
- A University of Michigan student project (https://cram678.github.io/league-of-legends-data-analysis; about 9,600 games, type and date not stated) found class win rates near 50% and class-only models near chance (accuracy 0.52). That's consistent with the above, but it's not pro data and has no significance test.
- An article on damage-type distribution and win rate (https://esn.gg/league-of-legends/distribution-of-damage-types) **couldn't be opened** (connection closed twice), so its numbers aren't used. Its search summary suggests it measured damage dealt in finished games (an outcome, partly caused by who was winning), not drafts.
- No pro-play study of frontline drafts was found.

## Suggested order

1. **A** (state-dependent style): cheap, inside the sim, and it follows the lesson above.
2. **B** (pro lane matchups): already measured in session 2; plugs into laning.
3. **C** (damage and frontline balance): simple and easy to explain on a draft screen.
4. Then E, G, D, F if time allows.

Each option that passes becomes a visible "why" in session 4's draft review. For example: "your siege comp converts leads into towers 20% faster" or "no magic damage: fights a bit worse", with the number from the fit.
