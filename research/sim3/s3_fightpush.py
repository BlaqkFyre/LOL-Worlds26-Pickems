"""Sim session 3 (research only, 10 Nov, report 7g): do towers and game endings follow won fights as much in the sim as in real games?
Held-out games from 1 Sep (Worlds included), real timelines v the sim (current, or a variant). For each side and minute (14:00+):
the side's net kills that minute (its kills minus the enemy's), then whether it takes a structure (tower, inhibitor, nexus
tower or nexus) that minute or in the next two, and, from 20:00, whether it wins the game within the next three minutes.
Also kills in the last three minutes of the game, and a short-game check.
usage: python -I s3_fightpush.py params3.json test3_results.json lanes3_features.csv comp3_games.csv tl_match.csv tl_events.csv out.json [runs] [variant]"""
import os, sys, json, importlib.util
import numpy as np
import pandas as pd

PJ, CJ, FE, CO, TM, TE, OUT = sys.argv[1:8]; NR = int(sys.argv[8]) if len(sys.argv) > 8 else 4; VAR = sys.argv[9] if len(sys.argv) > 9 else ""
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_sim.py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
P = json.load(open(PJ)); cal = json.load(open(CJ))["cal"]
if "typed" in VAR.split(","): P["fight_typed"] = json.load(open(os.path.join(os.path.dirname(PJ), "fighttypes.json"))); cal["fight_model"] = "typed"
sim = mod.Sim(P, cal)
fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid")
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.date >= "2026-09-01")]
GAMES = [g for g in fe[fe.day >= "2026-09-01"].gameid.unique() if g in set(M.gameid)]
STRUCT = {"tower", "inhib", "nexus"}
ev, games = [], []
for i, g in enumerate(GAMES):
    d = fe[fe.gameid == g].set_index("position").reindex(["top", "jng", "mid", "bot", "sup"])
    if d.z_v1.isna().any(): continue
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
    if g in comp.index:
        c = comp.loc[g]; x.update(pace_s=float(c.pace_blue + c.pace_red), siege_s=float(c.siege_blue + c.siege_red), obj_s=float(c.objectives_blue + c.objectives_red))
    for j in range(NR):
        r = sim.run(x, seed=70000 + 10 * i + j, log=True); gid = f"S{i}_{j}"
        games.append((gid, "sim", r["sec"], r["winner"]))
        ev += [(gid, e["t"], e["side"], "kill" if e["kind"] == "kill" else "struct") for e in r["steps"] if e["kind"] == "kill" or e["kind"] in STRUCT]
Mr = M[M.gameid.isin(set(GAMES))]
e = pd.read_csv(TE, dtype={"gid": str}); e = e[e.gid.isin(Mr.gid)]
games += [("R" + g, "real", int(l), w) for g, l, w in zip(Mr.gid, Mr.len, Mr.win)]
e = e[(e.type == "kill") | (e.type.isin(["tower", "inhib", "nexus"]))]
ev += [("R" + g, t, s, "kill" if ty == "kill" else "struct") for g, t, s, ty in zip(e.gid, e.t, e.side, e.type)]
E = pd.DataFrame(ev, columns=["gid", "t", "side", "kind"]); G = pd.DataFrame(games, columns=["gid", "src", "sec", "win"]).set_index("gid")
rows = []
for gid, gg in G.iterrows():
    eg = E[E.gid == gid]; mm = int(gg.sec // 60)
    kb = np.bincount((eg[(eg.kind == "kill") & (eg.side == "blue")].t // 60).astype(int), minlength=mm + 4)
    kr = np.bincount((eg[(eg.kind == "kill") & (eg.side == "red")].t // 60).astype(int), minlength=mm + 4)
    sb = np.bincount((eg[(eg.kind == "struct") & (eg.side == "blue")].t // 60).astype(int), minlength=mm + 4)
    sr = np.bincount((eg[(eg.kind == "struct") & (eg.side == "red")].t // 60).astype(int), minlength=mm + 4)
    for m in range(14, mm):
        for side, k1, k2, s1 in (("blue", kb, kr, sb), ("red", kr, kb, sr)):
            rows.append((gg.src, m, int(k1[m] - k2[m]), int(s1[m:m + 3].sum() > 0), int(gg.win == side and gg.sec < 60 * (m + 4))))
A = pd.DataFrame(rows, columns=["src", "m", "net", "struct3", "win3"])
A["netb"] = pd.cut(A.net, [-99, -2, 1, 3, 99], labels=["lost by 2+", "even (-1..1)", "won by 2-3", "won by 4+"])
res = {"variant": VAR or "current", "games_real": int((G.src == "real").sum()), "games_sim": int((G.src == "sim").sum())}
res["structure_within_3min"] = {s: {str(b): [round(float(d.struct3.mean()), 3), int(len(d))] for b, d in A[A.src == s].groupby("netb", observed=True)} for s in ("real", "sim")}
A20 = A[A.m >= 20]
res["win_within_4min_from_20"] = {s: {str(b): [round(float(d.win3.mean()), 3), int(len(d))] for b, d in A20[A20.src == s].groupby("netb", observed=True)} for s in ("real", "sim")}
last = []
for gid, gg in G.iterrows():
    eg = E[(E.gid == gid) & (E.kind == "kill")]
    last.append((gg.src, int(((eg.t >= gg.sec - 180)).sum()), gg.sec / 60))
Lt = pd.DataFrame(last, columns=["src", "k_last3", "min"])
res["kills_last_3min"] = {s: round(float(Lt[Lt.src == s].k_last3.mean()), 2) for s in ("real", "sim")}
res["short_games_under_26"] = {s: round(float((Lt[Lt.src == s]["min"] < 26).mean()), 3) for s in ("real", "sim")}
res["note"] = "[share, side-minutes]; structure = tower, inhibitor, nexus tower or nexus taken this minute or in the next two; win = the side wins before the end of minute m+3"
json.dump(res, open(OUT, "w"), indent=1); print(json.dumps(res, indent=1))
