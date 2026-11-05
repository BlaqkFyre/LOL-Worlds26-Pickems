"""Role-by-role event tests (Luke, 5 Nov): do session 2's draft and player inputs move the in-game events they should,
for every role and every teammate pair (not only the ones that passed for who-wins)?
Inputs (pre-game; built from earlier days only; player history from all leagues in the file):
  comfort      log(1 + the player's earlier games on that champion)                      per role
  together     log(1 + earlier games the two players played on the same team)            per pair (10)
  strength     champion-role result minus v1's expected, summed over earlier major games, / (n + 100)   per role
  synergy      the two champions' (same team) result minus v1's expected, / (n + 30)     per pair (10)
Events (major games, from the file; blue minus red):
  gold lead at 15 (role, or the pair's two roles); kills minus deaths by 15 (role, or pair); for jungle pairs the objectives on
  their side: jungle with bot / support -> first dragon; jungle with top / mid -> first Herald, more grubs
Each input alone, added to v1's log-odds and side (linear for gold and K-D, logistic for objectives), standardised.
Pass (as in session 2): better than v1 alone on Jul-Aug (fit Feb-Jun) AND from 1 Sep (fit Feb-Aug). Worlds shown too.
usage: python -I s3_roleevents.py <OE csv> v1_games.csv <out_json> <out_csv>"""
import sys, json, itertools
from collections import defaultdict
import numpy as np
import pandas as pd

CSV, V1, OUTJ, OUTC = sys.argv[1:5]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}; ROLES = ["top", "jng", "mid", "bot", "sup"]
PAIRS = list(itertools.combinations(ROLES, 2))
c = ["gameid", "league", "date", "side", "position", "playerid", "champion", "result", "golddiffat15", "killsat15", "deathsat15",
     "firstdragon", "firstherald", "void_grubs", "opp_void_grubs"]
raw = pd.read_csv(CSV, low_memory=False, usecols=c)
raw = raw[~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy(); raw["day"] = raw.date.str[:10]
v1 = pd.read_csv(V1).set_index("gameid")
PL = raw[raw.position.isin(ROLES)].copy()
TM = raw[raw.position == "team"].copy()
PL["p"] = PL.gameid.map(v1.p_v1); PL.loc[PL.side == "Red", "p"] = 1 - PL.loc[PL.side == "Red", "p"]
comf = defaultdict(int); tog = defaultdict(int); st_s = defaultdict(float); st_n = defaultdict(int); sy_s = defaultdict(float); sy_n = defaultdict(int)
feat = {}
for day, dd in PL.groupby("day", sort=True):
    sides = dd.groupby(["gameid", "side"])
    for (g, s), x in sides:
        x = x.set_index("position")
        if not set(ROLES) <= set(x.index): continue
        f = {}
        for r in ROLES:
            pid, ch = x.at[r, "playerid"], x.at[r, "champion"]
            f[f"comfort_{r}"] = np.log1p(comf[(pid, ch)]) if pid == pid else np.nan
            f[f"strength_{r}"] = st_s[(ch, r)] / (st_n[(ch, r)] + 100)
        for a, b in PAIRS:
            pa, pb = x.at[a, "playerid"], x.at[b, "playerid"]
            f[f"together_{a}_{b}"] = np.log1p(tog[frozenset((pa, pb))]) if pa == pa and pb == pb else np.nan
            k = (x.at[a, "champion"], a, x.at[b, "champion"], b); f[f"synergy_{a}_{b}"] = sy_s[k] / (sy_n[k] + 30)
        feat[(g, s)] = f
    for (g, s), x in sides:  # update history after the day
        x = x.set_index("position")
        if not set(ROLES) <= set(x.index): continue
        for r in ROLES:
            pid, ch = x.at[r, "playerid"], x.at[r, "champion"]
            if pid == pid: comf[(pid, ch)] += 1
            if x.at[r, "p"] == x.at[r, "p"]: st_s[(ch, r)] += x.at[r, "result"] - x.at[r, "p"]; st_n[(ch, r)] += 1
        for a, b in PAIRS:
            pa, pb = x.at[a, "playerid"], x.at[b, "playerid"]
            if pa == pa and pb == pb: tog[frozenset((pa, pb))] += 1
            if x.at[a, "p"] == x.at[a, "p"]:
                k = (x.at[a, "champion"], a, x.at[b, "champion"], b); sy_s[k] += x.at[a, "result"] - x.at[a, "p"]; sy_n[k] += 1
F = pd.DataFrame.from_dict(feat, orient="index"); F.index = pd.MultiIndex.from_tuples(F.index, names=["gameid", "side"])
# events per major game, blue minus red
maj = TM[TM.league.isin(MAJOR)].gameid.unique()
P2 = PL[PL.gameid.isin(maj)].copy(); P2["kd15"] = P2.killsat15 - P2.deathsat15
gdv = P2[P2.side == "Blue"].pivot_table(index="gameid", columns="position", values="golddiffat15")
kdb = P2[P2.side == "Blue"].pivot_table(index="gameid", columns="position", values="kd15"); kdr = P2[P2.side == "Red"].pivot_table(index="gameid", columns="position", values="kd15")
kd = kdb - kdr
bt = TM[(TM.side == "Blue") & TM.gameid.isin(maj)].set_index("gameid")
G = pd.DataFrame(index=maj); G["z"] = v1.z_v1.reindex(G.index); G["date"] = bt.date.reindex(G.index); G["league"] = bt.league.reindex(G.index)
G["fd"] = bt.firstdragon.reindex(G.index); G["fh"] = bt.firstherald.reindex(G.index); G["grubs"] = (bt.void_grubs > bt.opp_void_grubs).astype(float).reindex(G.index)
for r in ROLES: G[f"gd_{r}"] = gdv[r].reindex(G.index); G[f"kd_{r}"] = kd[r].reindex(G.index)
Fb = F.xs("Blue", level="side"); Fr = F.xs("Red", level="side")
D = (Fb - Fr.reindex(Fb.index)).reindex(G.index)
G = G.join(D); G = G.dropna(subset=["z"])
def lfit(X, y, l2=1.0):
    bb = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ bb)); bb += np.linalg.solve(X.T @ (X * (p * (1 - p))[:, None]) + l2 * np.eye(len(bb)), X.T @ (y - p) - l2 * bb)
    return bb
ll = lambda p, y: float(-np.mean(y * np.log(np.clip(p, 1e-6, 1 - 1e-6)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1))))
def test(fc, yc, kind):
    d = G.dropna(subset=[fc, yc])
    sets = {"Jul-Aug": (d.date < "2026-07-01", (d.date >= "2026-07-01") & (d.date < "2026-09-01")),
            "from 1 Sep": (d.date < "2026-09-01", d.date >= "2026-09-01"),
            "Worlds": (d.date < "2026-09-01", d.league == "WLDs")}
    out = {}
    for nm, (trm, tem) in sets.items():
        tr, te = d[trm], d[tem]
        if len(te) < 20: continue
        sd = tr[fc].std() or 1
        X0 = lambda q: np.c_[np.ones(len(q)), q.z]; X1 = lambda q: np.c_[X0(q), q[fc] / sd]
        if kind == "lin":
            b0, *_ = np.linalg.lstsq(X0(tr), tr[yc], rcond=None); b1, *_ = np.linalg.lstsq(X1(tr), tr[yc], rcond=None)
            e0 = float(np.mean((te[yc] - X0(te) @ b0) ** 2)); e1 = float(np.mean((te[yc] - X1(te) @ b1) ** 2))
            out[nm] = {"n": len(te), "weight": round(float(b1[2]), 2), "change_pct": round(100 * (e1 - e0) / e0, 3)}
        else:
            b0 = lfit(X0(tr), tr[yc].values); b1 = lfit(X1(tr), tr[yc].values)
            l0 = ll(1 / (1 + np.exp(-X0(te) @ b0)), te[yc].values); l1 = ll(1 / (1 + np.exp(-X1(te) @ b1)), te[yc].values)
            out[nm] = {"n": len(te), "weight": round(float(b1[2]), 3), "change": round(l1 - l0, 4)}
    key_ = "change_pct" if kind == "lin" else "change"
    out["passes"] = bool("Jul-Aug" in out and out["Jul-Aug"][key_] < 0 and out["from 1 Sep"][key_] < 0)
    out["worlds_better"] = bool("Worlds" in out and out["Worlds"][key_] < 0)
    return out
rows = []
for r in ROLES:
    for inp in ["comfort", "strength"]:
        fc = f"{inp}_{r}"
        for yc, kind in [(f"gd_{r}", "lin"), (f"kd_{r}", "lin")] + ([("fd", "logit"), ("fh", "logit"), ("grubs", "logit")] if r == "jng" else []):
            rows.append((inp, r, yc, test(fc, yc, kind)))
OBJ = {("jng", "bot"): ["fd"], ("jng", "sup"): ["fd"], ("top", "jng"): ["fh", "grubs"], ("jng", "mid"): ["fh", "grubs"], ("bot", "sup"): ["fd"]}
for a, b in PAIRS:
    G[f"gd_{a}_{b}"] = G[f"gd_{a}"] + G[f"gd_{b}"]; G[f"kd_{a}_{b}"] = G[f"kd_{a}"] + G[f"kd_{b}"]
    for inp in ["together", "synergy"]:
        fc = f"{inp}_{a}_{b}"
        for yc, kind in [(f"gd_{a}_{b}", "lin"), (f"kd_{a}_{b}", "lin")] + [(o, "logit") for o in OBJ.get((a, b), [])]:
            rows.append((inp, f"{a}-{b}", yc, test(fc, yc, kind)))
tab = []
for inp, who, yc, o in rows:
    k = "change_pct" if yc.startswith(("gd", "kd")) else "change"
    tab.append({"input": inp, "role_or_pair": who, "event": yc, "passes": o["passes"], "worlds_better": o["worlds_better"],
                "jul_aug": o.get("Jul-Aug", {}).get(k), "from_1_sep": o.get("from 1 Sep", {}).get(k), "worlds": o.get("Worlds", {}).get(k),
                "weight": o.get("from 1 Sep", {}).get("weight"), "measure": "% change in squared error" if k == "change_pct" else "change in log loss"})
T = pd.DataFrame(tab); T.to_csv(OUTC, index=False)
res = {"tests": len(T), "passes": int(T.passes.sum()), "passes_and_worlds": int((T.passes & T.worlds_better).sum()),
       "passing": T[T.passes].to_dict("records")}
json.dump(res, open(OUTJ, "w"), indent=1, default=str)
pd.set_option("display.width", 220)
print(T.to_string(index=False))
print("tests", len(T), "pass", int(T.passes.sum()), "pass + Worlds better", int((T.passes & T.worlds_better).sum()))
