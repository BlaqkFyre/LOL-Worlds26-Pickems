"""Game memory, steps 1-3 (17 Nov 2026 AEST; Luke OK'd the plan: fights tested over several windows with the data picking, winner by gold
swing with kills as the backup, responses until the losers respawn, gol.gg timelines as a second check).
Data: the whole-game lolesports feed of the 98 Worlds games (lib.feed.full(): pauses cut from the clock, checked against the file).

1. Deaths: every rise in a player's deaths counter is a death at that game second; the player's respawn is the first later frame with
   health above 0 (read from the feed, not the death-timer formula).
2. Fights: deaths of either side closer together than G seconds are one fight, G in GAPS. The gap between deaths is reported as a
   histogram so the data shows where fights separate. Fights with no death: seconds where at least 2 players on each side lose 5%+ of
   their health at once, grouped the same way, with no death in them (counted, step 5 uses them).
3. Winner: gold swing = the change in (blue team gold - red team gold) from G s before the first death to 5 s after the last
   (team gold in the feed is gold earned, so buying doesn't move it). Backup: the side with more kills; equal kills = a trade.
Outputs: research/model/memory/fights_G<g>.csv (one row per fight) and m1_fights.json (results); the run record in research/runs/.
usage (repo root): python -I research/memory/m1_fights.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from lib import config, feed
from lib.runlog import Run

GAPS = [5, 10, 15, 20, 30, 45]
OUT = config.MODEL_DIR / "memory"
from common import deaths, contact, fights, HP_DROP, HP_PER_SIDE, AFTER

def summary(F, ngames):
    F = F.sort_values(["gameid", "n"]); nxt = F.groupby("gameid").win_gold.shift(-1)
    dec = F[F.win_gold != "even"]; nd = nxt[F.win_gold != "even"]; ok = nd.notna() & (nd != "even")
    kills = F.deaths_blue + F.deaths_red
    return {"fights per game": round(len(F) / ngames, 2), "deaths per fight": round(float(kills.mean()), 2),
            "share with 1 death": round(float((kills == 1).mean()), 3), "share with 4+ deaths": round(float((kills >= 4).mean()), 3),
            "trades by kills (equal kills)": round(float((F.win_kills == "trade").mean()), 3),
            "gold and kills agree (kills not a trade)": round(float((F.win_gold == F.win_kills)[F.win_kills != "trade"].mean()), 3),
            "gold winner of a trade = side with the higher swing; median |swing| of trades": round(float(F.swing[F.win_kills == "trade"].abs().median()), 0),
            "winner wins the next fight (gold)": round(float((dec.win_gold[ok] == nd[ok]).mean()), 3),
            "gold winner of the fight wins the game": round(float((F.win_gold == F.winner_game).mean()), 3)}

with Run("memory_fights", params={"gaps": GAPS, "hp_drop": HP_DROP, "hp_per_side": HP_PER_SIDE, "after_s": AFTER, "clock": [feed.GAP_S, feed.FROZEN_S]},
         inputs=[config.OE_CSV]) as run:
    games = feed.full(); R = {"games": len(games), "deaths": 0, "by gap": {}, "no-death contact episodes per game": {}}
    allev = {g["gameid"]: deaths(g) for g in games}
    # check the deaths against the file's kills
    R["deaths"] = sum(len(v) for v in allev.values()); R["kills in the feed's final team totals"] = int(sum(g["T"][-1, :, 4].sum() for g in games))
    R["deaths with no respawn seen (game ended)"] = sum(e["game_over"] for v in allev.values() for e in v)
    gaps = np.concatenate([np.diff([e["t"] for e in v]) for v in allev.values() if len(v) > 1])
    edges = [0, 2, 4, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 90, 120, 180, 300, 1e9]
    h = np.histogram(gaps, bins=edges)[0]
    R["gap between consecutive deaths (s): count per bin"] = {f"{edges[i]:g}-{edges[i + 1]:g}": int(h[i]) for i in range(len(h))}
    R["gap between consecutive deaths: count per second of bin width"] = {f"{edges[i]:g}-{edges[i + 1]:g}": round(h[i] / (min(edges[i + 1], 600) - edges[i]), 1) for i in range(len(h))}
    for G in GAPS:
        F = pd.DataFrame([r for g in games for r in fights(g, allev[g["gameid"]], G)])
        R["by gap"][G] = summary(F, len(games))
        OUT.mkdir(parents=True, exist_ok=True); F.to_csv(OUT / f"fights_G{G}.csv", index=False)
        # contact episodes with no death
        ne = []
        for g in games:
            c = g["t"][contact(g)]; dt_ = np.array([e["t"] for e in allev[g["gameid"]]])
            if not len(c): continue
            ep = np.split(c, np.where(np.diff(c) > G)[0] + 1)
            ne.append(sum(1 for e in ep if not ((dt_ >= e[0] - G) & (dt_ <= e[-1] + G)).any()))
        R["no-death contact episodes per game"][G] = round(sum(ne) / len(games), 2)
    run.result("deaths", R["deaths"]); run.save_json(OUT / "m1_fights.json", R)
    for k, v in R.items(): print(k, v)
