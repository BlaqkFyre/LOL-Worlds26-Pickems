"""Sim session 2 (read-only): how fast the meta moves, and whether recent patches describe the Worlds patch better.
Pro presence per champion per patch = (picks + bans) / games. Compared with Worlds (16.20, 73 games):
  - rank correlation of pro presence, Worlds v each earlier patch;
  - rank correlation of lolalytics win rate and pick rate, 16.20 v each earlier lolalytics patch;
  - Worlds pro presence v lolalytics 16.20 pick+ban and win rate.
usage: python -I meta_by_patch.py <csv> lola_tiers_all.csv <out_json>"""
import json, sys
import numpy as np
import pandas as pd

CSV, LOLA, OUT = sys.argv[1:4]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
def norm(p):
    a, _, b = str(p).partition("."); return f"{a}.{b}0" if len(b) == 1 else f"{a}.{b.zfill(2)}"
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalpha())
df = pd.read_csv(CSV, low_memory=False, dtype={"patch": str},
                 usecols=["gameid", "league", "date", "patch", "position", "champion", "ban1", "ban2", "ban3", "ban4", "ban5"])
df = df[df.league.isin(MAJOR) & ~((df.league == "WLDs") & (df.date < "2026-10-01"))].copy(); df["patch"] = df.patch.map(norm)
pl, tm = df[df.position != "team"], df[df.position == "team"]
games = pl.groupby("patch").gameid.nunique()
picks = pl.groupby(["patch", "champion"]).size()
bans = pd.concat([tm[["patch", c]].rename(columns={c: "champion"}) for c in ["ban1", "ban2", "ban3", "ban4", "ban5"]]).dropna().groupby(["patch", "champion"]).size()
pres = picks.add(bans, fill_value=0).rename("n").reset_index()
pres["pres"] = pres.n / pres.patch.map(games); pres["k"] = pres.champion.map(key)
P = pres.pivot_table(index="k", columns="patch", values="pres", fill_value=0.0)
rc = lambda a, b: float(pd.Series(a).rank().corr(pd.Series(b).rank()))
R = {"pro_games_per_patch": games.to_dict()}
W = P["16.20"]
R["pro_presence_v_worlds"] = {p: round(rc(W.values, P[p].values), 3) for p in P.columns if p != "16.20"}
top = W.sort_values(ascending=False).head(30).index
R["top30_worlds_overlap_with_top30"] = {p: int(len(set(top) & set(P[p].sort_values(ascending=False).head(30).index))) for p in P.columns if p != "16.20"}
L = pd.read_csv(LOLA, dtype={"patch": str}); L["patch"] = L.patch.map(norm); L["k"] = L.name.map(key)
L = L[L.games >= 1000]
for m in ("wr", "pr"):
    Q = L.pivot_table(index=["k", "lane"], columns="patch", values=m)
    R[f"lolalytics_{m}_v_16.20"] = {p: round(rc(Q["16.20"].dropna().reindex(Q.index).values, Q[p].values) if True else 0, 3)
                                   for p in Q.columns if p != "16.20"}
# solo meta v Worlds pro meta (champion level: lanes summed for pick rate, best lane for win rate)
lc = L[L.patch == "16.20"].groupby("k").agg(pr=("pr", "sum"), br=("br", "max"), wr=("wr", lambda s: s.iloc[np.argmax(L.loc[s.index, "games"].values)]))
J = pd.DataFrame({"worlds_pres": W}).join(lc, how="inner")
R["worlds_presence_v_lolalytics_16.20"] = {"champions": len(J), "pick_plus_ban": round(rc(J.worlds_pres, J.pr + J.br), 3),
                                          "pick": round(rc(J.worlds_pres, J.pr), 3), "ban": round(rc(J.worlds_pres, J.br), 3), "win": round(rc(J.worlds_pres, J.wr), 3)}
# same, for the last domestic patch (16.17) v lolalytics 16.17
W17 = P["16.17"]; lc17 = L[L.patch == "16.17"].groupby("k").agg(pr=("pr", "sum"), br=("br", "max"))
J17 = pd.DataFrame({"p": W17}).join(lc17, how="inner")
R["pro_16.17_presence_v_lolalytics_16.17_pick_plus_ban"] = round(rc(J17.p, J17.pr + J17.br), 3)
json.dump(R, open(OUT, "w"), indent=1); print(json.dumps(R, indent=1))
