"""Game memory, step 5 (17 Nov 2026 AEST): snowballing, dead time and fight closeness on the 98 Worlds feed games.
Fights from research/model/memory/fights_G20.csv (m1_fights.py; winner by gold swing).
- Snowball: does the winner of a fight win the next one more often than the gold lead explains? Logistic fit of "blue wins the next fight"
  on blue's gold lead before it (per 1,000) and who won the last fight (+1 blue, -1 red), with a 1,000-draw bootstrap over games for the
  range. Raw rates by gold lead shown too.
- Dead time: each role's share of game time spent dead (deaths and respawns from common.deaths), by game phase.
- Closeness: does the side with more players or more health going in win, and are fights with even health closer (smaller swing)?
  Going in = 20 s before the first death; players counted = alive then and lost 5%+ health or died in the fight.
Output: research/model/memory/m3_state.json.
usage (repo root): python -I research/memory/m3_state.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from lib import config, feed, fit
from lib.runlog import Run
from common import deaths

OUT = config.MODEL_DIR / "memory"; BOOT = 1000
PHASE = [(0, 840, "before 14:00"), (840, 1500, "14:00-25:00"), (1500, 1e9, "after 25:00")]
r3 = lambda x: round(float(x), 3)

with Run("memory_state", params={"fights": "fights_G20.csv", "bootstrap": BOOT}, inputs=[OUT / "fights_G20.csv"]) as run:
    F = pd.read_csv(OUT / "fights_G20.csv").sort_values(["gameid", "n"]); R = {}
    # snowball
    F["blue_win"] = (F.win_gold == "blue").astype(float)
    F["last"] = F.groupby("gameid").win_gold.shift(1).map({"blue": 1.0, "red": -1.0})
    S = F[F.last.notna() & (F.win_gold != "even")].copy()
    X = lambda d: np.c_[np.ones(len(d)), d.lead_before / 1000, d["last"]]
    b = fit.logistic(X(S), S.blue_win.values)
    gids = S.gameid.unique(); rng = np.random.default_rng(20261117); bs = []
    by = {g: d for g, d in S.groupby("gameid")}
    for _ in range(BOOT):
        d = pd.concat([by[g] for g in rng.choice(gids, len(gids))]); bs.append(fit.logistic(X(d), d.blue_win.values))
    bs = np.array(bs)
    R["snowball: fit (blue wins next fight)"] = {"fights": len(S), "constant (blue side)": r3(b[0]), "per 1,000 gold lead": r3(b[1]), "won the last fight": r3(b[2]),
        "won the last fight, 90% range": [r3(np.percentile(bs[:, 2], 5)), r3(np.percentile(bs[:, 2], 95))],
        "per 1,000 gold, 90% range": [r3(np.percentile(bs[:, 1], 5)), r3(np.percentile(bs[:, 1], 95))],
        "won last, at even gold: win chance": r3(fit.sigmoid(b[0] + b[2])), "lost last, at even gold": r3(fit.sigmoid(b[0] - b[2]))}
    S["lead_w"] = S.lead_before * S["last"]  # gold lead of the last fight's winner
    S["won_again"] = ((S.win_gold == "blue") == (S["last"] > 0)).astype(float)
    bins = [-1e9, -3000, -1000, 1000, 3000, 1e9]; lab = ["behind 3k+", "behind 1-3k", "within 1k", "ahead 1-3k", "ahead 3k+"]
    R["snowball: last fight's winner wins the next, by its gold lead"] = {l: {"fights": int(len(x)), "wins next": r3(x.won_again.mean())}
        for l, x in S.groupby(pd.cut(S.lead_w, bins, labels=lab), observed=True)}
    S["phase"] = pd.cut(S.t_first, [p[0] for p in PHASE] + [1e9], labels=[p[2] for p in PHASE], right=False)
    R["snowball: last fight's winner wins the next, by phase"] = {str(p): {"fights": int(len(x)), "wins next": r3(x.won_again.mean())} for p, x in S.groupby("phase", observed=True)}
    gap = S.t_first - F.groupby("gameid").t_last.shift(1).loc[S.index]
    R["seconds from one fight to the next: median, 25%, 75%"] = [round(float(gap.median())), round(float(gap.quantile(.25))), round(float(gap.quantile(.75)))]
    # dead time
    games = feed.full(); dead = {r: {p[2]: [0.0, 0.0] for p in PHASE} for r in config.ROLES}
    for g in games:
        t = g["t"]; dt = np.diff(t, prepend=t[0]); isdead = np.zeros((len(t), 10), bool)
        for e in deaths(g):
            end = t[-1] if e["game_over"] else e["respawn"]; isdead[(t >= e["t"]) & (t < end), e["p"]] = True
        for a, z, name in PHASE:
            m = (t >= a) & (t < z)
            for p in range(10): dead[g["roles"][p]][name][0] += float((dt[m] * isdead[m, p]).sum()); dead[g["roles"][p]][name][1] += float(dt[m].sum())
    R["share of game time dead, by role and phase"] = {r: {k: r3(v[0] / v[1]) for k, v in d.items()} for r, d in dead.items()}
    # closeness
    C = F[F.win_gold != "even"].copy()
    C["num"] = C.in_blue - C.in_red; C["hp"] = C.hp_blue - C.hp_red; C["alive"] = C.alive_blue - C.alive_red
    Xc = np.c_[np.ones(len(C)), C.num, C.hp, C.lead_before / 1000]
    bc = fit.logistic(Xc, C.blue_win.values)
    R["closeness: fit (blue wins the fight)"] = {"fights": len(C), "constant": r3(bc[0]), "per extra player in the fight": r3(bc[1]),
        "per extra full health bar": r3(bc[2]), "per 1,000 gold lead": r3(bc[3])}
    C["hpgap"] = pd.cut(C.hp.abs(), [-0.01, 0.5, 1, 2, 10], labels=["under 0.5", "0.5-1", "1-2", "2+"])
    R["closeness: by health gap going in (full bars)"] = {str(k): {"fights": int(len(x)), "side with more health wins": r3(((x.hp > 0) == (x.win_gold == "blue"))[x.hp != 0].mean()),
        "median |swing|": round(float(x.swing.abs().median()))} for k, x in C.groupby("hpgap", observed=True)}
    R["numbers going in (alive): side with more alive wins"] = {str(k): {"fights": int(len(x)), "wins": r3(((x.alive > 0) == (x.win_gold == "blue")).mean())}
        for k, x in C[C.alive != 0].groupby(C.alive.abs().clip(upper=3))}
    run.result("snowball, won last fight", R["snowball: fit (blue wins next fight)"]["won the last fight"])
    run.save_json(OUT / "m3_state.json", R)
    import json; print(json.dumps(R, indent=1))
