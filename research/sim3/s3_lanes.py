"""Sim session 3, step 3 (read-only): laning at 10 and 15 minutes, role by role.
Per role and minute, the lane's gold lead (blue player minus red player, from the file's golddiffat10/15) is fitted as
   gd = a + b*z_v1 + c*skill gap + d*champion gap + noise
  z_v1        v1's pre-game log-odds (team + players), earlier days only
  skill gap   blue minus red lane skill from session 1 (top/mid e_laning, jng e_early, bot e_lane_own, sup e_playmaking: e_lane_duo is empty for supports)
  champion gap blue champion's lane value minus red's: the champion-role's average lead at that minute in training games,
              pulled toward 0 (k = 20 games)
Fitted on games before 1 Sep; judged from 1 Sep and on Worlds (out of sample). Also: how the five lanes' noise moves
together (the sim draws them jointly) and how 10 -> 15 grows. Patch groups check whether the current patches lane differently.
usage: python -I s3_lanes.py <OE csv> v1_games.csv gfeat.csv <out_dir>"""
import os, sys, json
import numpy as np
import pandas as pd

CSV, V1, GF, OUT = sys.argv[1:5]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
ROLES = ["top", "jng", "mid", "bot", "sup"]; MINS = [10, 15]; K = 20
SKILL = {"top": "e_laning", "jng": "e_early", "mid": "e_laning", "bot": "e_lane_own", "sup": "e_playmaking"}
cols = ["gameid", "league", "date", "patch", "side", "position", "champion", "golddiffat10", "golddiffat15"]
raw = pd.read_csv(CSV, low_memory=False, usecols=cols, dtype={"patch": str})
raw = raw[raw.league.isin(MAJOR) & raw.position.isin(ROLES) & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy()
raw["day"] = raw.date.str[:10]
gf = pd.read_csv(GF)
gf["skill"] = [r[SKILL[r.position]] for _, r in gf.iterrows()]
raw = raw.merge(gf[["gameid", "side", "position", "skill"]], on=["gameid", "side", "position"], how="left")
b = raw[raw.side == "Blue"].set_index(["gameid", "position"]); r = raw[raw.side == "Red"].set_index(["gameid", "position"])
L = b[["league", "day", "patch", "champion", "golddiffat10", "golddiffat15", "skill"]].join(
    r[["champion", "skill"]], rsuffix="_red").reset_index()
L = L.rename(columns={"champion": "c_blue", "champion_red": "c_red", "golddiffat10": "gd10", "golddiffat15": "gd15"})
L["skill_gap"] = L.skill - L.skill_red
v1 = pd.read_csv(V1)[["gameid", "z_v1"]]
L = L.merge(v1, on="gameid", how="left").dropna(subset=["gd10", "gd15", "z_v1"])
L["skill_gap"] = L.skill_gap.fillna(0)
L["pg"] = pd.cut(L.patch.str.split(".").str[1].astype(int), [0, 14, 18, 99], labels=["16.01-16.14", "16.15-16.18", "16.19-16.20"])
TR = L.day < "2026-09-01"; TE = ~TR; WO = TE & (L.league == "WLDs")

def champ_values(d, m):
    # champion-role average lead at minute m, from that champion's side of the lane
    x = pd.concat([d[["position", "c_blue", f"gd{m}"]].rename(columns={"c_blue": "c", f"gd{m}": "v"}),
                   d[["position", "c_red", f"gd{m}"]].rename(columns={"c_red": "c", f"gd{m}": "v"}).assign(v=lambda t: -t.v)])
    g = x.groupby(["position", "c"]).v.agg(["sum", "count"])
    return (g["sum"] / (g["count"] + K)).to_dict()

res = {"games": {"train": int(L[TR & (L.position == "top")].shape[0]), "test": int(L[TE & (L.position == "top")].shape[0]),
                 "worlds": int(L[WO & (L.position == "top")].shape[0])}, "fit": {}, "patch_groups": {}}
coef_rows = []
resid = {}
for m in MINS:
    cv = champ_values(L[TR], m)
    L[f"cg{m}"] = [cv.get((p, a), 0) - cv.get((p, c), 0) for p, a, c in zip(L.position, L.c_blue, L.c_red)]
    for ro in ROLES:
        d = L[L.position == ro]
        X = lambda q: np.c_[np.ones(len(q)), q.z_v1, q.skill_gap, q[f"cg{m}"]]
        tr, te, wo = d[TR[d.index]], d[TE[d.index]], d[WO[d.index]]
        beta, *_ = np.linalg.lstsq(X(tr), tr[f"gd{m}"], rcond=None)
        out = {}
        for nm, q in [("train", tr), ("from 1 Sep", te), ("Worlds", wo)]:
            y = q[f"gd{m}"].values; p = X(q) @ beta; base = tr[f"gd{m}"].mean()
            out[nm] = {"n": len(q), "r2": round(1 - ((y - p) ** 2).sum() / ((y - base) ** 2).sum(), 3),
                       "rmse": round(float(np.sqrt(((y - p) ** 2).mean()))), "sd": round(float(y.std()))}
        res["fit"][f"{ro} @{m}"] = out
        coef_rows.append(dict(role=ro, minute=m, intercept=beta[0], per_z=beta[1], per_skill_sd=beta[2], per_champ_gold=beta[3],
                              resid_sd=float(np.std(tr[f"gd{m}"] - X(tr) @ beta))))
        resid[(ro, m)] = pd.Series(d[f"gd{m}"].values - X(d) @ beta, index=d.gameid.values)
        for pg, q in d.groupby("pg", observed=True):
            res["patch_groups"].setdefault(f"{ro} @{m}", {})[str(pg)] = {"n": len(q), "sd": round(float(q[f"gd{m}"].std())),
                                                                        "blue_mean": round(float(q[f"gd{m}"].mean()))}
# joint noise: correlation of lane residuals across roles (all games), and 10 -> 15 carry-over
R15 = pd.DataFrame({ro: resid[(ro, 15)] for ro in ROLES}).dropna()
R10 = pd.DataFrame({ro: resid[(ro, 10)] for ro in ROLES}).dropna()
res["resid_corr_15"] = R15.corr().round(3).to_dict()
res["resid_corr_10"] = R10.corr().round(3).to_dict()
both = R10.join(R15, lsuffix="_10", rsuffix="_15").dropna()
res["carry_10_to_15"] = {ro: {"corr": round(float(both[f"{ro}_10"].corr(both[f"{ro}_15"])), 3),
                              "slope": round(float(np.polyfit(both[f"{ro}_10"], both[f"{ro}_15"], 1)[0]), 3)} for ro in ROLES}
team = L.groupby("gameid").agg(gd15=("gd15", "sum"), gd10=("gd10", "sum"), z=("z_v1", "first"), day=("day", "first"))
res["team_gd"] = {"sd10": round(float(team.gd10.std())), "sd15": round(float(team.gd15.std())),
                  "corr_with_z_15": round(float(team.gd15.corr(team.z)), 3)}
pd.DataFrame(coef_rows).round(3).to_csv(os.path.join(OUT, "lanes3_coef.csv"), index=False)
# per game and role inputs for the sim tests (champion values from training games only, so held-out games stay out)
L[["gameid", "day", "league", "position", "z_v1", "skill_gap", "cg10", "cg15", "gd10", "gd15"]].round(4).to_csv(
    os.path.join(OUT, "lanes3_features.csv"), index=False)
R15.cov().round(0).to_csv(os.path.join(OUT, "lanes3_resid_cov15.csv"))
R10.cov().round(0).to_csv(os.path.join(OUT, "lanes3_resid_cov10.csv"))
json.dump(res, open(os.path.join(OUT, "lanes3_results.json"), "w"), indent=1)
print(json.dumps(res["games"])); print(pd.DataFrame(coef_rows).round(2).to_string(index=False))
for k, v in res["fit"].items(): print(k, v)
print("corr15", R15.corr().round(2).to_string()); print("carry", res["carry_10_to_15"]); print("team", res["team_gd"])
for k, v in res["patch_groups"].items(): print(k, v)
