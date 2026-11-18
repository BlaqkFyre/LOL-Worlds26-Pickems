"""Game memory, step 4 (17 Nov 2026 AEST): what follows a won fight, until the losers are back to full numbers.
Fights from common.fights (20 s death gap), winner by gold swing. The window runs from the fight's last death to the moment the losing side's
last player from that fight respawns (measured in the feed). If the game ends first, the Nexus fell in the window.
Within the window, from the feed's team totals: towers, inhibitors, Barons and dragons taken by each side, how soon the winner's first one
came, and whether the loser contested (took anything, or won a fight that started in the window).
Baseline: the same objectives per minute outside every window, so the response can be read as "x times the usual rate".
Outputs: research/model/memory/m2_responses.json, responses.csv (one row per fight).
usage (repo root): python -I research/memory/m2_responses.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from lib import config, feed
from lib.runlog import Run
from common import deaths, fights, at, FIGHT_GAP

OUT = config.MODEL_DIR / "memory"; OBJ = {"tower": 1, "inhib": 2, "baron": 3, "dragon": 5}
PHASE = [(0, 840, "before 14:00"), (840, 1500, "14:00-25:00"), (1500, 1e9, "after 25:00")]

def rows_for(g):
    t, T = g["t"], g["T"]; ev = deaths(g); F = fights(g, ev, FIGHT_GAP); out = []
    for n, f in enumerate(F):
        w = f["win_gold"]
        if w == "even": continue
        L = "red" if w == "blue" else "blue"; wi, li = (0, 1) if w == "blue" else (1, 0)
        lost = [e for e in ev if e["side"] == L and f["t_first"] <= e["t"] <= f["t_last"]]
        ended = any(e["game_over"] for e in lost)
        end = t[-1] if ended else max([e["respawn"] for e in lost], default=f["t_last"])
        i0, i1 = at(t, f["t_last"]), at(t, end)
        r = {"gameid": g["gameid"], "n": n, "t": f["t_last"], "winner": w, "loser_deaths": len(lost), "winner_deaths": f["deaths_" + w],
             "window_s": end - f["t_last"], "swing": abs(f["swing"]), "lead_before_winner": f["lead_before"] * (1 if w == "blue" else -1),
             "nexus": int(ended and g["winner"] == w), "loser_won_game_in_window": int(ended and g["winner"] == L)}
        first = np.inf
        for k, c in OBJ.items():
            r[k + "_w"] = int(T[i1, wi, c] - T[i0, wi, c]); r[k + "_l"] = int(T[i1, li, c] - T[i0, li, c])
            if r[k + "_w"] > 0:
                j = i0 + int(np.argmax(T[i0:i1 + 1, wi, c] > T[i0, wi, c])); first = min(first, t[j] - f["t_last"])
        r["first_obj_s"] = first if np.isfinite(first) else np.nan
        nxt = [x for x in F[n + 1:] if x["t_first"] <= end]
        r["loser_won_fight_in_window"] = int(any(x["win_gold"] == L for x in nxt))
        r["loser_contested"] = int(any(r[k + "_l"] > 0 for k in OBJ) or r["loser_won_fight_in_window"])
        out.append(r)
    # baseline: objectives per minute outside the windows
    inside = np.zeros(len(t), bool)
    for r in out: inside[(t > r["t"]) & (t <= r["t"] + r["window_s"])] = True
    base = {"minutes_outside": float((~inside[1:] * np.diff(t)).sum() / 60)}
    for k, c in OBJ.items():
        d = np.diff(T[:, :, c], axis=0).sum(1); base[k] = float(d[~inside[1:]].sum())
    return out, base

with Run("memory_responses", params={"fight_gap": FIGHT_GAP, "window": "fight's last death to the losers' last respawn"}, inputs=[config.OE_CSV]) as run:
    games = feed.full(); rows, B = [], []
    for g in games:
        o, b = rows_for(g); rows += o; B.append(b)
    D = pd.DataFrame(rows); D["phase"] = pd.cut(D.t, [p[0] for p in PHASE] + [1e9], labels=[p[2] for p in PHASE], right=False)
    D.to_csv(OUT / "responses.csv", index=False)
    mins = sum(b["minutes_outside"] for b in B)
    R = {"fights with a gold winner": len(D), "baseline per minute outside the windows (both sides)": {k: round(sum(b[k] for b in B) / mins, 3) for k in OBJ}}
    def block(x):
        o = {"fights": len(x), "window median s": round(float(x.window_s.median()), 0)}
        for k in OBJ:
            o[k + " winner per fight"] = round(float(x[k + "_w"].mean()), 3); o[k + " loser per fight"] = round(float(x[k + "_l"].mean()), 3)
            o[k + " winner per minute of window"] = round(float(x[k + "_w"].sum() / max(x.window_s.sum() / 60, 1e-9)), 3)
        o["winner takes anything"] = round(float((x[[k + "_w" for k in OBJ]].sum(1) > 0).mean()), 3)
        o["median s to winner's first objective"] = round(float(x.first_obj_s.median()), 0) if x.first_obj_s.notna().any() else None
        o["Nexus in window"] = round(float(x.nexus.mean()), 3); o["loser contested"] = round(float(x.loser_contested.mean()), 3)
        o["loser won a fight in window"] = round(float(x.loser_won_fight_in_window.mean()), 3)
        return o
    R["all"] = block(D)
    R["by phase"] = {str(p): block(x) for p, x in D.groupby("phase", observed=True)}
    D["loser_deaths_c"] = D.loser_deaths.clip(upper=4).astype(str).replace({"4": "4+"})
    R["by loser deaths"] = {k: block(x) for k, x in D.groupby("loser_deaths_c")}
    late = D[D.t >= 1500]
    R["after 25:00 by loser deaths"] = {k: block(x) for k, x in late.groupby("loser_deaths_c")}
    run.result("fights", len(D)); run.save_json(OUT / "m2_responses.json", R)
    import json; print(json.dumps(R, indent=1))
