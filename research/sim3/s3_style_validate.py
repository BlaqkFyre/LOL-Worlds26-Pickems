"""Draft-style validation (Luke, 6 Nov, decision 2: keep all three styles, keep validating; siege should show in later games, late game is
generally siege or scaling comps). Research only.
Champion labels, none set by hand:
  class_*     Riot's official champion sub-classes (League wiki champion data, wiki_champ_tags.csv): a draft's count of each class
  tower_dmg   measured siege: the champion-role's share of its team's damage to towers in pro games before 1 Sep (Oracle's Elixir file),
              minus the role average, pulled toward 0 with k = 20 games; a draft = the sum over its five
  solo_scale  outside scaling: lolalytics solo-queue win rate in the last 3 game-length buckets minus the first 3 (16.17 + 16.20 pooled;
              lola_length.csv from session 2), per champion-role, minus the role average; a draft = the sum
Timing outcomes (real games):
  file (all major games): game length (min), towers (both), turret plates (both, an early-siege measure)
  timelines (gol.gg, 623 matched games): towers after 25:00 (both), first tower time
Each label on its own: both drafts together (blue + red) against each outcome, beyond how one-sided the game was (|v1 log-odds|) and patch
period; then blue minus red against blue's share of towers after 25:00 (who sieges late).
Measured on games before 1 Sep; checked on games from 1 Sep (Worlds included). Pass = same sign, |t| >= 2 on both sets.
usage: python -I s3_style_validate.py <OE csv> <wiki_champ_tags.csv> <lola_length.csv> <v1_games.csv> <tl_match.csv> <tl_events.csv> <out json>"""
import json, re, sys, unicodedata
import numpy as np
import pandas as pd

CSV, WIKI, LOLA, V1, TLM, TLE, OUT = sys.argv[1:8]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
key = lambda s: re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())
o = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "side", "position", "champion", "result", "gamelength", "towers",
                                                 "turretplates", "damagetotowers"])
o = o[o.league.isin(MAJOR) & ~((o.league == "WLDs") & (o.date < "2026-10-01"))].copy()
T = o[o.position == "team"]; P = o[o.position != "team"].copy(); P["k"] = P.champion.map(key)
P["td_share"] = P.damagetotowers / P.groupby(["gameid", "side"]).damagetotowers.transform("sum")
pre = P[P.date < "2026-09-01"].dropna(subset=["td_share"])
rm = pre.groupby("position").td_share.mean()
cr = pre.groupby(["k", "position"]).td_share.agg(["sum", "count"])
cr["td"] = (cr["sum"] - cr["count"] * rm.reindex(cr.index.get_level_values(1)).values) / (cr["count"] + 20)
P["tower_dmg"] = [cr.td.get((k, p), 0.0) for k, p in zip(P.k, P.position)]
# lolalytics solo scaling
L = pd.read_csv(LOLA); L["k"] = L.champion.map(key)
A = L.groupby(["k", "position"]).sum(numeric_only=True)
A["s"] = A[["w5", "w6", "w7"]].sum(axis=1) / A[["g5", "g6", "g7"]].sum(axis=1) - A[["w1", "w2", "w3"]].sum(axis=1) / A[["g1", "g2", "g3"]].sum(axis=1)
A["s"] = A.s - A.groupby(level=1).s.transform("mean")
P["solo_scale"] = [A.s.get((k, p), np.nan) for k, p in zip(P.k, P.position)]
# Riot sub-classes
W = pd.read_csv(WIKI, sep=";"); W["k"] = W.name.map(key)
cls = {}
for k, roles in zip(W.k, W.roles.fillna("")):
    for c in re.split(r"[,/]", roles):
        c = c.strip()
        if c: cls.setdefault(k, set()).add(c)
CLASSES = sorted({c for s in cls.values() for c in s})
for c in CLASSES: P["class_" + c] = [1.0 if c in cls.get(k, ()) else 0.0 for k in P.k]
res = {"label_coverage": {"wiki_classes": round(float(P.k.isin(cls).mean()), 3), "solo_scale": round(float(P.solo_scale.notna().mean()), 3)}}
LABELS = ["tower_dmg", "solo_scale"] + ["class_" + c for c in CLASSES]
D = P.groupby(["gameid", "side"])[LABELS].sum(min_count=5).unstack("side")
G = T[T.side == "Blue"].set_index("gameid")[["date", "gamelength", "towers", "turretplates", "league"]].copy()
Tr = T[T.side == "Red"].set_index("gameid")
G["towers"] = G.towers + Tr.towers.reindex(G.index); G["plates"] = G.turretplates + Tr.turretplates.reindex(G.index)
G["length"] = G.gamelength / 60
v1 = pd.read_csv(V1).set_index("gameid"); G["abs_z"] = v1.z_v1.reindex(G.index).abs()
for l in LABELS:
    G[l + "_sum"] = D[(l, "Blue")] + D[(l, "Red")]; G[l + "_diff"] = D[(l, "Blue")] - D[(l, "Red")]
# timelines
M = pd.read_csv(TLM, dtype={"gid": str}).dropna(subset=["gameid"]); E = pd.read_csv(TLE, dtype={"gid": str})
tw = E[E.type == "tower"]
late = tw[tw.t >= 1500].groupby("gid").size(); late_blue = tw[(tw.t >= 1500) & (tw.side == "blue")].groupby("gid").size()
ft = tw.groupby("gid").t.min() / 60
M = M.set_index("gid"); M["late_towers"] = late.reindex(M.index).fillna(0); M["late_blue"] = late_blue.reindex(M.index).fillna(0)
M["first_tower_min"] = ft.reindex(M.index)
G = G.join(M.set_index("gameid")[["late_towers", "late_blue", "first_tower_min"]], how="left")
G["late_blue_share"] = np.where(G.late_towers > 0, G.late_blue / G.late_towers, np.nan)
G["period"] = np.where(G.date < "2026-09-01", "train", "test")
G["half"] = (G.date >= "2026-06-01").astype(float)  # patch period control within training

def ols(d, y, x):
    d = d.dropna(subset=[y, x, "abs_z"])
    if len(d) < 30 or d[x].std() == 0: return None
    X = np.c_[np.ones(len(d)), (d[x] - d[x].mean()) / d[x].std(), d.abs_z] if d.half.nunique() < 2 else np.c_[np.ones(len(d)), (d[x] - d[x].mean()) / d[x].std(), d.abs_z, d.half]
    b, *_ = np.linalg.lstsq(X, d[y].values, rcond=None); r = d[y].values - X @ b
    se = np.sqrt(np.diag(np.linalg.inv(X.T @ X)) * (r @ r) / (len(d) - X.shape[1]))
    return {"n": len(d), "per_sd": round(float(b[1]), 4), "t": round(float(b[1] / se[1]), 2)}
OUTC = [("length", "sum"), ("towers", "sum"), ("plates", "sum"), ("late_towers", "sum"), ("first_tower_min", "sum"), ("late_blue_share", "diff")]
rows = []
for l in LABELS:
    for y, kind in OUTC:
        x = f"{l}_{kind}"; a = ols(G[G.period == "train"], y, x); b = ols(G[G.period == "test"], y, x)
        if not a or not b: continue
        ok = a["t"] * b["t"] > 0 and abs(a["t"]) >= 2 and abs(b["t"]) >= 2
        rows.append({"label": l, "outcome": y, "train_n": a["n"], "train_per_sd": a["per_sd"], "train_t": a["t"], "test_n": b["n"],
                     "test_per_sd": b["per_sd"], "test_t": b["t"], "passes": ok})
R = pd.DataFrame(rows)
res["tests"] = len(R); res["passing"] = R[R.passes].to_dict("records")
res["note"] = "per_sd = change in the outcome per standard deviation of the draft label (both drafts together; diff for late_blue_share)"
R.to_csv(OUT.replace(".json", ".csv"), index=False)
json.dump(res, open(OUT, "w"), indent=1, default=float)
pd.set_option("display.width", 200); print(R.to_string(index=False)); print(json.dumps({k: v for k, v in res.items() if k != "passing"}, indent=1))
print("passing:", R[R.passes][["label", "outcome", "train_per_sd", "train_t", "test_per_sd", "test_t"]].to_string(index=False))
