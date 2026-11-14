# Laning phase as actions: plan for slice 1 (draft for Luke, 14 Nov 2026 AEST)

Status: **plan only, nothing built.** No code or data changes until Luke OKs it.

## Why (Luke, 14 Nov)

The sim in the app (v46–v50) takes a few numbers at the start and then draws fitted per-minute rates ("x does y z% of the time"). Luke wants
pre-draft factors (teams, players, meta, champion pools), draft factors (meta, synergies, damage types, comp styles, counters, player
tendencies and skill, team meta awareness) and in-game events to drive each **action point**, so a game reflects real data through its
actions. For example, T1's bot lane wins a 2v2 against an LCS bot lane because the data supports it.

Luke's rules for this work (14 Nov; memory `sim-actions-from-data`):
1. **Every behaviour is proven by data.** Claude sets no behaviour numbers. Where the data is thin, find more; where it only leans one
   way, bring it to Luke.
2. **Success = actions between players, champions and teams that reflect real data.** Who-wins accuracy only has to stay inside the noise
   band.
3. **Worlds first.** Worlds games and the Worlds patch (16.20) come first in every test. The wider 2026 data stays for lasting
   (non-meta) factors.
4. **Minor leagues on 16.20** (LAS 161, EM 26, TCL 11, HC 6, VCS 3 games) are tested first, then used for champion and matchup data on the
   patch only if they help on Worlds games.
5. **Testing: day by day at Worlds.** For each Worlds day, fit on everything before it, test on that day, then move forward. The rest of
   2026 is a second check.
6. **One slice first, end to end, for Luke to judge in the app.** This is that slice: the laning phase.
7. The draft AI is rebuilt in the same design later. This slice gives it lane tables to draft with (see Draft link).

## Where the sim is now: a real example (Luke's game, 14 Nov, v50, seed 3725554652168835, HLE v TES)

What's wrong in the laning phase of that game, and why:
- **The draft barely mattered.** The odds were 70% before the draft and 70% after it. Expected gold at 15 was even in mid and HLE +0.1k bot,
  so Lucian–Nautilus v Ezreal–Renata and Orianna v Syndra changed nothing. Lanes get one gold number each from the draft, and nothing about
  who those players are in lane beyond a skill gap.
- **Laning has no lane actions.** There are no plates in the play-by-play. Kills are drawn per minute with no lane, matchup or jungler
  reason: Kanavi kills Tian at 11:02 and Creme at 12:03 with no gank or skirmish behind either.
- **Objectives with no contest.** Dragon at 8:13, then all 3 grubs at 8:48 on the other side of the map, with no fight and no lane
  priority. In the real IG v TES game below, the first dragon fell at 5:46, right after a 2v2+ fight in bot.
- **Later in the same game** (not this slice, but on the list): at 27:19 TES lose four players, then fight a 4–1 at 27:52 while those four
  are still dead (death timer at that time and level, estimated from the wiki table: about 52–55 s). Death timers are only in the research sim, not the app. Base structures fall
  in the same second (24:37, 28:26, 28:54). "(solo)" is shown inside teamfights. Gumayusi gets 11/0/0 with no assists across three
  teamfights.

Second example (Luke, 14 Nov, HLE v TL, end of game): Elder 33:19, one kill at 35:01, then six structures from 36:48 to 39:50 with no
fight, HLE and TL towers in the same second (37:38), and inhibitor, two Nexus towers and Nexus all at 39:50. Cause, read in
`js/sim-engine.js`:
- Each minute, each side's push is drawn on its own (lane by lane, then base), with no fight or dead players behind it, so pushes cross the
  map at the same time and the Nexus falls with no fight (real: 99.6% of Nexus kills have the winners' own kill in the 60 s before).
- Each structure gets a random second in its minute, but the event-order setting (`at()`, line 135) keeps the play-by-play in order by
  moving any event that drew an earlier second up to the last one's time. So a base push drawn in one minute stacks on one second, and a
  tower drawn for the other team just after a push lands on that push's second. The structure timing fit in the research sim (part C:
  real gaps between a team's structures, median 9 s) cut 0 s gaps from 61% to 8% (real 0.9%), but it is not in the app.
These belong to the slices after laning (pushes and endings driven by fights and dead players).

## What slice 1 changes

From 0:00 to 14:00, each game is played as actions between the actual players and champions (below). At 14:00, the state is handed to the
current sim, which carries on: each player's gold, XP and level, kills and deaths (and who is dead, with timers), plates and towers by
lane, dragons, grubs and timers. The rest of the game is unchanged until later slices.

## Inputs: pre-draft and draft, all measured from data

Each input is kept only if it passes its tests (next section). Values come from the data, never from me.

| Input | Measured from | Weighting | What it drives |
|---|---|---|---|
| **Player lane skill** (each player: gold, XP and CS edge at 10 and 15, early kills and deaths, solo kills) | Oracle's Elixir file: `golddiffat10/15`, `xpdiffat10/15`, `csdiffat10/15`, `killsat10/15`, `deathsat10/15`, every 2026 major-league game; fitted jointly with the opponent and the champions, so a player isn't credited for an easy matchup | All of 2026, recent games and Worlds weighted most (half-life chosen by test) | Who wins each lane exchange, solo kills |
| **Champion pool and comfort** (player x champion: games, results, lane edge on that champion v their usual) | The file (2026 major leagues + Worlds); `TEAMS` top-3 picks; player champion history | All of 2026 | Whether a player on a comfort pick lanes better than on a new one. **Test first**: earlier, pool depth helped jungle and ADC in who-wins; never tested on lane results |
| **Champion lane strength and matchup** (champion, and champion v champion in a role) | Worlds 16.20 first; earlier 2026 patches fill gaps, pulled toward 16.20; minor leagues on 16.20 only if they pass their test | Patch-weighted | Lane edge by matchup (Gnar v Ambessa top, Kai'Sa–Nautilus v Ezreal–Rell bot) |
| **Champion early power** (lane and jungle champions' edge at 10 and 15 across all opponents) | Same as above | Patch-weighted | Skirmish and gank strength; jungle duels |
| **Jungler habits** (which lane the jungler's early kills come from, how early, invades, dragon v grubs first) | gol.gg timelines (640 games, 96 from Worlds): kills before 14:00 with the jungler as killer or assist, by victim's lane; first objective taken | Split-half stability test across the season (habit must hold up, unlike the earlier gank test) | Where ganks go |
| **Roams** (mid and support kills in other lanes before 14:00) | Same | Same test | Mid and support roams |
| **Team early priority** (first dragon, grubs, first tower, first blood rates by team, beyond strength) | The file + timelines | Stability across splits, then held-out | Which objective a team contests first |

Not in this slice (later slices): damage types, comp styles, synergies, team meta awareness, scaling. They matter more after 14:00.

## Action points in the laning phase

Each is a contest between the named players and champions, with a measured chance; game state (gold, levels, who is dead) feeds the next
one.

1. **Lane exchanges** (each lane, by minute window): top 1v1, mid 1v1, bot 2v2. Moves the lane's CS, XP and gold edge, from both players'
   lane skill, the champion matchup and comfort. Data: lane edges at 10 and 15 per player, per champion.
2. **Lane kills**: solo kills and 2v2 kills in a lane, from the lane edge plus the same inputs. Data: timeline kills by lane, no jungler
   or roamer involved.
3. **Jungle actions**: where the jungler goes (gank, invade, objective), from his habits, which lanes are winning or losing, and timers;
   whether a gank kills, trades or fails, from the jungler and laners involved and their champions' early power. Counter-ganks when both
   junglers are on the same side. Data: timeline kills with a jungler involved. **Gap:** failed ganks leave no record in this data.
4. **Roams**: mid or support goes to another lane, same data and gap.
5. **Plates** (each lane, from the first plate time in the data until 14:00): from the lane edge, deaths in that lane (a dead laner can't
   defend), and Herald or grubs. Data: 35,763 plates by lane with times.
6. **First objectives**: first dragon, grubs, first Herald. Contest or give, decided by lane priority (mid and bot or mid and top edge
   at the time), where the junglers are, the team's early priority and who is dead. Data: 2,974 dragons and 1,920 grubs with times and
   takers, kills just before.
7. **First towers before 14:00**: from plates taken, the lane edge and deaths. Data: towers with lane and time.
8. **Deaths take players out**: death timers (League wiki, already built in the research sim) take a dead laner off the map, so the lane
   loses CS and plates, and a gank or skirmish can't use him.

## What the data has, and the gaps

- **Have:** per player at 10 and 15 (gold, XP, CS edges, kills, deaths, assists) for every 2026 major-league game (2,869) and all 94
  Worlds games; timelines with every kill (killer, assisters, victim, time), plate, tower, dragon, grub and Herald for 640 games, 96 of
  them from Worlds.
- **Every Worlds game has a timeline** (94 of 94, matched in `research/model/sim3/tl_match.csv`, 12 Nov). Corrected 14 Nov: the draft of
  this plan said timelines stopped at 4 Nov; that came from an older match file (`research/local/sim3/out/tl_match.csv`, 626 games) read by
  mistake. A fresh gol.gg pull on 14 Nov found no new pages (the final hasn't been played yet).
- **Gaps:** no positions or wards; failed ganks and flashes leave no trace; no recall timings; CS and gold only at 10 and 15 per player
  (team gold per minute in `tl_gold.csv`). Where an action needs one of these, the plan names it and either finds a source (to check:
  whether any Worlds stats feed has finer data) or leaves the action out and says so.

## Tests

**Before building (each input):** where it's a habit, it must be stable (it agrees from one half of a player's or team's season to the
other). Then it must predict its own action on held-out games better than without it, day by day at Worlds first, then from 1 Sep for
2026. Every input gets a line in the report: kept, leans (Luke decides), or no.

**The slice, against real Worlds games (day by day), then 2026 from 1 Sep:**
- Lane edges at 10 and 15 by lane: the spread, and how well the inputs line up with real results (do higher-rated lanes win their lanes
  as often as in real games?).
- Kills before 14:00 by role, by lane, by type (solo, 2v2, gank, roam, jungle duel); first blood time and role.
- Jungler kill participation by lane before 14:00.
- Plates by lane; first tower lane and time.
- First dragon, grubs and Herald: taker, time, and whether a fight came first.
- Re-deaths inside the death timer: real 0.0%.
- Gold lead at 15 (team): spread, and how tied it is to team strength (it was too tied in every earlier sim).
- Who-wins log loss on Worlds games stays inside the noise band.

**Minor leagues on 16.20:** the champion and matchup tables with and without them, judged on Worlds games.

## Worked example: IG v TES, quarter-final 1, game 1 (`LOLTMNT02_485703`, 3 Nov US, patch 16.20)

Real game, from the file and the gol.gg timeline. IG (blue) won in 31:02.

| Lane | IG | TES | Real edge at 10 / 15 (IG) |
|---|---|---|---|
| Top | TheShy Gnar | 369 Ambessa | +941 / +905 gold, +12 CS at 10 |
| Jungle | Wei Qiyana | Tian Vi | −210 / +260 |
| Mid | Rookie Syndra | Creme Cassiopeia | −119 / +336 |
| Bot | JiaQi Kai'Sa, Meiko Nautilus | JackeyLove Ezreal, Zhuo Rell | −300 / −527 (ADC) |

Real laning phase, minute by minute (timeline):
- 2:42 TheShy (Gnar) solo kills 369 (Ambessa): first blood, top.
- 5:42–5:51 bot 2v2 + junglers: Tian (Vi) and Zhuo kill JiaQi; JackeyLove kills Rookie; Meiko kills JackeyLove; Creme kills Meiko
  (both mids in a bot fight suggests both roamed; the data has no positions, so this is read from who took part). 5:46 Wei takes the
  mountain dragon in the middle of it.
- 6:10 first plate (IG, top). 8:18–8:27 grubs split 2–1 (Wei, Wei, Tian).
- 10:30 Creme, Tian, JackeyLove, Zhuo kill Wei (jungle caught). 10:57 Tian takes the chemtech dragon.
- 13:06 Rookie (Syndra) and Wei kill JackeyLove. 13:47 369 kills TheShy; 13:51 Rookie and TheShy kill 369 (Rookie in a top kill: a roam, read from who took part).
- 14:19 IG take TES's top outer tower; 14:26 TES take IG's bot outer tower: both teams pushing the lane they won.

How slice 1 would play the same draft (values to be measured; none are set here):
1. **Pre-draft:** lane skill for TheShy v 369, Rookie v Creme, JiaQi/Meiko v JackeyLove/Zhuo, Wei v Tian, from all their 2026 games
   (Worlds weighted). Champion pools: is Gnar a TheShy comfort pick (his 2026 games on it), is Ambessa 369's?
2. **Draft:** matchup edges on 16.20 for Gnar v Ambessa (top), Syndra v Cassiopeia (mid), Kai'Sa–Nautilus v Ezreal–Rell (bot), Qiyana v Vi
   (jungle early power).
3. **0:00–14:00:** each minute window, top exchanges from TheShy's and 369's lane skill, the matchup and comfort; a solo kill can happen
   when the edge is big enough by the measured chance (real game: 2:42). Bot: 2v2 exchanges; Tian's habits (does he path bot early?)
   decide whether he arrives, and Creme's roam habits whether mid follows (real game: 5:42). Dragon contest at that moment from bot and mid
   priority and who is alive (real game: Wei took it mid-fight). Plates from each lane's edge and deaths (real: IG top plates from 6:10,
   TES bot plates from 8:08). Grubs from top priority and jungler positions (real: split 2–1).
4. **At 14:00:** hand over gold, XP, kills and deaths, plates, towers, dragons and grubs to the current sim.

Checking the slice on this game: it's one game, so it can't be "right", but over the Worlds days the share of games like it (an early
2v2+ bot fight with junglers, a top solo kill by the stronger laner, dragon taken during a fight) must match real games.

## Draft link

The same tables (player lane skill, comfort, champion matchups, early power) replace the hand-set lane parts of the draft AI's
`scoreFor` in a later step, so the AI drafts lanes it can win. Not in slice 1 unless Luke wants it here.

## Steps (each reported to Luke before the next)

1. **Measure the inputs** (research only): fit player lane skill, comfort, champion matchups and early power, jungler habits, roams and
   team priority; stability and held-out tests, day by day at Worlds; minor-league test. Report: kept / leans / no for each.
2. **Luke reviews** what survived and any "leans".
3. **Build the laning module in the research sim** (`research/sim3/s3_sim.py`, as an option, off by default, so earlier runs replay
   identically), handing over at 14:00.
4. **Test the slice** (lane checks above, then who-wins), day by day at Worlds, then 2026.
5. **Port to the app** (`js/sim-engine.js`, tables in `js/sim-tables.js` via `research/sim4/s4_tables.py`), play-by-play lines for lane
   actions (gank, roam, 2v2, plates), cache bump, browser check.
6. **Luke judges it in the app.**

## Luke's answers (14 Nov)

1. Pull the gol.gg timelines for the 7 Worlds games from 6–8 Nov (QF3, QF4, semi-finals): **yes.** Done 14 Nov: they were already pulled
   and matched on 12 Nov (see the data section), so all 94 Worlds games have timelines.
2. Draft AI lane tables: **in this slice** (step 5 also replaces the lane parts of `scoreFor` with the measured tables).
3. Death timers: **yes, for the whole game**, ported with this slice.
