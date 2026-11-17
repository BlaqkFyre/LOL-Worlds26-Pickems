# Worlds 2026 final (BLG 3–1 GEN) against the app's sim (v50), 17 Nov 2026 AEST

**Sources.** Drafts and scoreboards: pasted by Luke game by game in the chat (not opened from a source page by Claude, and not yet in the
Oracle's Elixir file; cross-check when a newer file has the final). Sim: the app's data sim v50 run in the browser (`SIM_ENGINE.inputs` +
`SIM_ENGINE.Sim`, calibration `default`), 2,000 games per draft with seeds 1–2,000. "Before draft" = v1 (team-and-player model, as the
draft review shows it); "after draft" = the share of simulated games won. Roles read in the order the picks were listed.

| Game | Sides (blue v red) | Before draft | After draft | Draft move | Biggest paper lane edge (gold at 15) | Real result | Real kills, length |
|---|---|---|---|---|---|---|---|
| 1 | GEN v BLG | GEN 62.6% | GEN 66.0% | +3.4 GEN | mid +349 GEN (Syndra v Locke) | GEN won | 19–4, about 39 min* |
| 2 | GEN v BLG | GEN 62.6% | GEN 59.9% | +2.8 BLG | support +135 BLG (Camille v Karma) | BLG won | 14–19, 53:21 |
| 3 | GEN v BLG | GEN 62.6% | GEN 59.1% | +3.6 BLG | mid +163 BLG (Viktor v Annie) | BLG won | 8–20, 37:44 |
| 4 | BLG v GEN | BLG 46.0% | BLG 57.1% | +11.1 BLG | mid +576 BLG (Twisted Fate v Akali) | BLG won | 21–11, 43:04 |

**Real Finals MVP: Knight** (per Luke, 17 Nov; not yet checked on a source page).

\* Game 1's length worked out from CS per minute; no game time was given.

Simulated games barely changed shape between drafts: kills about 15–13, towers about 6.6–5, dragons 2.2–2.3, Barons about 0.8–0.7,
median length 33–34 minutes in all four.

## Takeaways (to test on the 16.20 data, not changes to make)

1. **The draft's direction matched the winner in all four games**, but its moves were small (3–4 points) except game 4 (+11, almost all
   Twisted Fate's mid lane value). Four games prove nothing about the draft model.
2. **The before-draft model kept GEN favourites** (62.6% on blue, 54% on red) while BLG won three straight. The model is built on the 2026
   season; it has no way to see form inside a series, and shouldn't (rule: real Worlds data never changes simulated standings).
3. **Every draft plays out as the same game.** Scaling, dive, poke and pick comps all gave about 28 kills in 33 minutes. Real games:
   23 kills in 39 min, 33 in 53 min, 28 in 38 min, 32 in 43 min. Draft styles, champion power over time and the game state need to change
   the kind of game, not only the odds (game memory).
4. **Real games snowball; the sim's fights stay even.** Games 1 and 3 were blowouts (losers on 4 and 8 kills); the sim makes games that
   lopsided 2.5–4% of the time. Test: after a won fight, how often does the winner win the next one, real v sim.
5. **Mid edges came through the map, not the farm.** Syndra (game 1) and Twisted Fate (game 4, 2/1/17) were the sim's big mid edges as
   gold at 15; both mids won through kills and assists while the losing mid matched or beat them on CS (Locke 374 v 285, Akali 385 v
   364). Twisted Fate's lane value is a farm number (+303) with a negative kill value. Test: whether a mid's (and jungler's) edge shows up
   as farm or as kill participation in other lanes, by champion.
6. **The ADC carried the winner, against paper lanes that said even.** Ruler's Corki (39% damage, 7/0/8) in game 1, Viper's Ziggs (47%,
   94.6k) in game 2; the sim had those bot lanes even or slightly the other way at 15. Champion power curves (late-game scaling) aren't in
   the lane values. Test: damage share and fight wins after 25 minutes by champion.
7. **Long games are rare in the sim:** 2.4% of game 2's simulated games reached 50 minutes (real: 53:21). Check the real share of 45+ and
   50+ minute games on 16.20 and 2026.
8. **Paper lane edges missed twice in game 4 and once in game 2:** top was GEN's only edge in game 4 (Aurora v Gwen) and Bin went 8/2/9;
   jungle was even on paper in game 2 and Xun's Naafiri went 8/1/9. One series is too few to read anything into single lanes.
9. **A support dying a lot didn't lose the game** (ON's Camille 1/8/10 in a BLG win). Test whether a support's deaths cost less than a
   carry's.
10. **The sim's ratings and awards miss the carrying ADC** (17 Nov, Luke asked who the sim gives MVP to). Replaying the series (only
    simulated games the real winner won) the sim's Finals MVP is **Xun** (BLG average rating 5.92, Knight 5.67); its Player of the Game goes
    to junglers and mids every game (jungle 30-34%, mid 26-31%), ADCs only 13-16%, and Ruler is GEN's *lowest*-rated player (3.12). The
    app's rating formula on the real scoreboards (CS diff at 15 not given, set to 0) picks **Knight** (7.75, the real Finals MVP), with
    Player of the Game Ruler, Xun, Knight, Bin and Ruler GEN's best (7.22). The formula reads real games well; the sim's box scores (damage
    shares, kill participation by role) don't make an ADC carry, so the ratings built on them can't reward one. Same root as takeaway 6.

**Sources to use (Luke, 17 Nov):** NerfPlz for champion data where relevant, e.g. its scaling tier list
(https://www.nerfplz.com/lol-scaling-tier-list/) for champion power over time (takeaway 6); the site has more pages. Not yet read in full (the fetch
tool got a 403 on 17 Nov; open it in the browser pane), and like every outside label it gets tested on held-out games before the sim uses it.
Per Luke's excerpt (patch 26.22): it is **solo queue** data, each champion scored against its own role on win rate in games past 32 minutes
and the gain over games under 22. Pro play, meta, players and pro champion data lead this sim; solo queue fills holes in champion data and
matchups.
