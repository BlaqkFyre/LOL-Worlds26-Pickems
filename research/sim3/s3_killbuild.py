"""Sim session 3 (research only, 10 Nov): how kills per game build up, sim v real, on held-out games (from 1 Sep, Worlds included).
Kills are grouped into fights the same way for both (a gap of 20 s+ starts a new fight, as in s3_events.py).
Per game: length, kills, kill rate per minute, fights, kills per fight. Then where the spread of kills comes from:
  - length v rate: kills = rate x minutes; how much of the kill spread each part carries
  - minute-to-minute pattern: does a fight make another fight in the next minutes more or less likely (real fights may be
    held back by death timers and resets; the sim draws each minute on its own)
  - fights per minute by size of the gold lead
usage: python -I s3_killbuild.py params3.json test3_results.json lanes3_features.csv comp3_games.csv tl_match.csv tl_events.csv tl_gold.csv out.json [runs]"""
import os, sys, json, importlib.util
import numpy as np
import pandas as pd

PJ, CJ, FE, CO, TM, TE, TGo, OUT = sys.argv[1:9]; NR = int(sys.argv[9]) if len(sys.argv) > 9 else 4
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s3_sim.py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
P = json.load(open(PJ)); cal = json.load(open(CJ))["cal"]
if len(sys.argv) > 11 and "typed" in sys.argv[11].split(","):  # optional 11th argument: sim variant (typed = fight types, 7g)
    P["fight_typed"] = json.load(open(os.path.join(os.path.dirname(PJ), "fighttypes.json"))); cal["fight_model"] = "typed"
sim = mod.Sim(P, cal)
fe = pd.read_csv(FE); comp = pd.read_csv(CO).set_index("gameid")
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.date >= "2026-09-01")]
GAMES = [g for g in fe[fe.day >= "2026-09-01"].gameid.unique() if g in set(M.gameid)]

kills, games, leads = [], [], []
for i, g in enumerate(GAMES):
    d = fe[fe.gameid == g].set_index("position").reindex(["top", "jng", "mid", "bot", "sup"])
    if d.z_v1.isna().any(): continue
    x = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist()}
    if g in comp.index:
        c = comp.loc[g]; x.update(pace_s=float(c.pace_blue + c.pace_red), siege_s=float(c.siege_blue + c.siege_red), obj_s=float(c.objectives_blue + c.objectives_red))
    for j in range(NR):
        r = sim.run(x, seed=70000 + 10 * i + j, log=True); gid = f"S{i}_{j}"
        games.append({"gid": gid, "src": "sim", "sec": r["sec"]})
        kills += [{"gid": gid, "t": e["t"], "side": e["side"]} for e in r["steps"] if e["kind"] == "kill"]
        leads += [{"gid": gid, "minute": k, "gd": v} for k, v in r["gd"].items() if isinstance(k, (int, np.integer))]
S_used = {g for g in GAMES}
Mr = M[M.gameid.isin(S_used)]
e = pd.read_csv(TE, dtype={"gid": str}); e = e[e.gid.isin(Mr.gid) & (e.type == "kill")]
games += [{"gid": "R" + g, "src": "real", "sec": int(l)} for g, l in zip(Mr.gid, Mr.len)]
kills += [{"gid": "R" + g, "t": t, "side": s} for g, t, s in zip(e.gid, e.t, e.side)]
go = pd.read_csv(TGo, dtype={"gid": str}); go = go[go.gid.isin(Mr.gid) & (go.kind == "gold")]
gl = go.assign(v=go.value * np.where(go.side == "blue", 1, -1)).groupby(["gid", "minute"]).v.sum()
leads += [{"gid": "R" + g, "minute": int(m_), "gd": v} for (g, m_), v in gl.items()]
G = pd.DataFrame(games).set_index("gid"); K = pd.DataFrame(kills).sort_values(["gid", "t"]); L = pd.DataFrame(leads)
K["new"] = (K.groupby("gid").t.diff().fillna(1e9) >= 20).astype(int); K["fight"] = K.groupby("gid").new.cumsum()
F = K.groupby(["gid", "fight"]).agg(t=("t", "min"), n=("t", "size")).reset_index()
G["min"] = G.sec / 60; G["kills"] = K.groupby("gid").size().reindex(G.index).fillna(0)
G["fights"] = F.groupby("gid").size().reindex(G.index).fillna(0); G["rate"] = G.kills / G["min"]; G["kpf"] = G.kills / G.fights.clip(lower=1)
res = {"games_real": int((G.src == "real").sum()), "games_sim": int((G.src == "sim").sum()), "runs_per_game": NR}

def summ(D):
    out = {c: [round(float(D[c].mean()), 2), round(float(D[c].std()), 2)] for c in ("min", "kills", "rate", "fights", "kpf")}
    out["corr_kills_length"] = round(float(np.corrcoef(D.kills, D["min"])[0, 1]), 2)
    out["corr_rate_length"] = round(float(np.corrcoef(D.rate, D["min"])[0, 1]), 2)
    lr = np.log(D.kills.clip(lower=1)); out["var_log_kills"] = round(float(lr.var()), 4)
    out["var_log_rate"] = round(float(np.log(D.rate.clip(lower=1e-3)).var()), 4); out["var_log_min"] = round(float(np.log(D["min"]).var()), 4)
    return out
res["per_game"] = {s: summ(G[G.src == s]) for s in ("real", "sim")}
res["per_game_note"] = "[mean, sd]; rate = kills per minute; kpf = kills per fight. log variances: var(log kills) = var(log rate) + var(log minutes) + 2 cov"
# kills in fixed windows (removes length): kills before 15:00, 15:00-25:00 (games that reach 25:00)
for nm, a, b in (("k_0_15", 0, 900), ("k_15_25", 900, 1500)):
    cnt = K[(K.t >= a) & (K.t < b)].groupby("gid").size().reindex(G.index).fillna(0)
    ok = G.sec >= b
    res[nm] = {s: [round(float(cnt[ok & (G.src == s)].mean()), 2), round(float(cnt[ok & (G.src == s)].std()), 2),
                   round(float(cnt[ok & (G.src == s)].var() / max(1e-9, cnt[ok & (G.src == s)].mean())), 2)] for s in ("real", "sim")}
res["window_note"] = "[mean, sd, variance / mean] of kills in the window, games that reach the window's end"
# fight starts in the same windows (count only, sizes taken out): below 1 = more regular than chance, above 1 = bursty
for nm, a, b in (("f_0_15", 0, 900), ("f_15_25", 900, 1500)):
    cnt = F[(F.t >= a) & (F.t < b)].groupby("gid").size().reindex(G.index).fillna(0); ok = G.sec >= b
    res[nm] = {s: [round(float(cnt[ok & (G.src == s)].mean()), 2), round(float(cnt[ok & (G.src == s)].var() / max(1e-9, cnt[ok & (G.src == s)].mean())), 2)] for s in ("real", "sim")}
# kills and fight starts per minute played, by phase; and mean fight size
F["src"] = np.where(F.gid.str.startswith("R"), "real", "sim")
PHB = [0, 14, 20, 25, 30, 35, 99]; PHL = ["0-13", "14-19", "20-24", "25-29", "30-34", "35+"]
expo = {s: np.zeros(6) for s in ("real", "sim")}
for gid, gg in G.iterrows():
    mm = gg.sec / 60
    for i_ in range(6): expo[gg.src][i_] += max(0.0, min(mm, PHB[i_ + 1]) - PHB[i_])
F["ph"] = pd.cut(F.t / 60, PHB, right=False, labels=PHL)
res["by_phase"] = {s: {ph: {"fights_per_min": round(float((F[(F.src == s) & (F.ph == ph)].shape[0]) / max(1e-9, expo[s][i_])), 3),
                            "kills_per_min": round(float(F[(F.src == s) & (F.ph == ph)].n.sum() / max(1e-9, expo[s][i_])), 3),
                            "mean_size": round(float(F[(F.src == s) & (F.ph == ph)].n.mean()), 2)} for i_, ph in enumerate(PHL)} for s in ("real", "sim")}
# minute-to-minute: fights starting per minute; chance of a fight start in minutes m+1..m+3 after a fight-start minute v otherwise
F["m"] = (F.t // 60).astype(int)
rows = []
for gid, gg in G.iterrows():
    mm = int(gg.sec // 60); f = np.zeros(mm + 4); fs = F[F.gid == gid]
    for m_, n_ in zip(fs.m, fs.n):
        if m_ < len(f): f[m_] += 1
    for m_ in range(1, mm - 3):
        rows.append((gg.src, m_, f[m_] > 0, f[m_ + 1] > 0, (f[m_ + 1:m_ + 4] > 0).sum()))
A = pd.DataFrame(rows, columns=["src", "m", "fight_now", "fight_next", "next3"])
res["after_fight"] = {}
for s in ("real", "sim"):
    a = A[(A.src == s) & (A.m >= 14)]
    res["after_fight"][s] = {"P(fight next min | fight now)": round(float(a[a.fight_now].fight_next.mean()), 3),
                             "P(fight next min | none now)": round(float(a[~a.fight_now].fight_next.mean()), 3),
                             "fight minutes in next 3 | fight now": round(float(a[a.fight_now].next3.mean()), 3),
                             "fight minutes in next 3 | none now": round(float(a[~a.fight_now].next3.mean()), 3)}
res["after_fight_note"] = "minutes 14+; a fight minute = a minute in which a fight starts"
# size of next fight after a big fight (4+ kills) v after a small one
F = F.sort_values(["gid", "t"]); F["prev_n"] = F.groupby("gid").n.shift(); F["gap"] = F.groupby("gid").t.diff()
F["src"] = np.where(F.gid.str.startswith("R"), "real", "sim")
res["after_big_fight"] = {s: {"gap_s after 1-2 kill fight": int(F[(F.src == s) & (F.prev_n <= 2)].gap.median()),
                              "gap_s after 4+ kill fight": int(F[(F.src == s) & (F.prev_n >= 4)].gap.median()),
                              "share of fights 4+ kills": round(float((F[F.src == s].n >= 4).mean()), 3)} for s in ("real", "sim")}
# fights per minute by size of the lead at the start of the minute (minutes 14+)
L["absk"] = (L.gd.abs() / 1000).clip(upper=12).astype(int) // 3 * 3
fm = F.groupby(["gid", "m"]).size().rename("nf").reset_index().rename(columns={"m": "minute"})
LL = L[L.minute >= 14].merge(fm, on=["gid", "minute"], how="left").fillna({"nf": 0})
LL = LL[LL.minute < LL.gid.map(G.sec // 60)]
LL["src"] = np.where(LL.gid.str.startswith("R"), "real", "sim")
res["fights_per_min_by_lead"] = {s: {f"{k}-{k+3}k": [round(float(d.nf.mean()), 3), int(len(d))] for k, d in LL[LL.src == s].groupby("absk")} for s in ("real", "sim")}
json.dump(res, open(OUT, "w"), indent=1)
if len(sys.argv) > 10:  # optional: keep the per-game and per-fight tables for further checks (local folder)
    G.to_csv(os.path.join(sys.argv[10], "killbuild_games.csv")); F.to_csv(os.path.join(sys.argv[10], "killbuild_fights.csv"), index=False)
print(json.dumps(res, indent=1))
