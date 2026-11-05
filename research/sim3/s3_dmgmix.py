"""Comps option C, tested on data (Luke, 5 Nov: "the sim engine shouldn't have or not have data based on AI assumptions").
Claim tested: a comp with (almost) no magic damage, only one damage type, or no frontline does worse.
Labels (outside sources, not judgement):
  damage type   Riot client tags via the League wiki's Module:ChampionData/data (read 5 Nov in the browser): Magic / Physical /
                Mixed (counts 0.5); 3 champions have no damage tag there (Evelynn, Katarina, Renata Glasc): counted as unknown
  frontline     Riot class roles from the same module: Vanguard or Warden
Compared with: the app's hand-made CHAMP_AP list (js/champions.js) and Riot Data Dragon's 0-10 'magic' rating (16.22.1).
Test: every major-league game side; win compared with v1's pre-game odds (session 1). Descriptive bands, then a logistic on
v1's log-odds with the draft terms (blue minus red), fitted before 1 Sep, judged from 1 Sep and on Worlds.
usage: python -I s3_dmgmix.py <OE csv> v1_games.csv wiki_champ_tags.csv champion.json(ddragon) champions.js <out_json>"""
import sys, json, re
import numpy as np
import pandas as pd

CSV, V1, WT, DD, CJ, OUT = sys.argv[1:7]
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}; ROLES = ["top", "jng", "mid", "bot", "sup"]
W = pd.read_csv(WT, sep=";"); W["k"] = W.name.map(key)
W["mag"] = W.dtype.map({"Magic": 1.0, "Mixed": 0.5, "Physical": 0.0})
W["front"] = W.roles.fillna("").str.contains("Vanguard|Warden").astype(int)
WM = W.set_index("k")
dd = json.load(open(DD, encoding="utf-8"))["data"]; DDM = {key(v["name"]): v["info"]["magic"] for v in dd.values()}
js = open(CJ, encoding="utf-8").read(); m = re.search(r"const CHAMP_AP\s*=\s*new Set\(\[([^\]]*)\]", js)
APP = {key(x) for x in re.findall(r'"([^"]+)"', m.group(1))} if m else set()
res = {"labels": {"wiki_champions": len(W), "unknown_damage_tag": W[W.dtype.isna()].name.tolist(), "frontline_champions": int(W.front.sum())}}

raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "side", "position", "champion", "result"])
raw = raw[raw.league.isin(MAJOR) & raw.position.isin(ROLES) & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy()
raw["k"] = raw.champion.map(key)
miss = sorted(set(raw.champion[~raw.k.isin(WM.index)]))
res["labels"]["pro_champions_not_in_wiki"] = miss
raw["mag"] = raw.k.map(WM.mag); raw["front"] = raw.k.map(WM.front)
# agreement of label sources on champions played in pro games
pc = raw.drop_duplicates("k")[["k", "champion", "mag"]].dropna()
pc["app_magic"] = pc.k.isin(APP); pc["dd_magic"] = pc.k.map(DDM)
res["labels"]["app_CHAMP_AP_v_wiki"] = {"champions": len(pc), "agree": int(((pc.mag >= 0.5) == pc.app_magic).sum()),
                                        "app_magic_wiki_physical": pc[(pc.app_magic) & (pc.mag == 0)].champion.tolist(),
                                        "app_physical_wiki_magic": pc[(~pc.app_magic) & (pc.mag == 1)].champion.tolist()}
pc2 = pc.dropna(subset=["dd_magic"])
res["labels"]["ddragon_magic_rating_by_wiki_type"] = pc2.groupby("mag").dd_magic.agg(["mean", "min", "max", "count"]).round(2).reset_index().to_dict("records")

S = raw.groupby(["gameid", "side"]).agg(date=("date", "first"), league=("league", "first"), result=("result", "first"),
                                        magic=("mag", lambda s: s.sum() if s.notna().all() else np.nan), front=("front", "sum"),
                                        known=("mag", lambda s: s.notna().sum())).reset_index()
v1 = pd.read_csv(V1).set_index("gameid")
S["p"] = S.gameid.map(v1.p_v1); S.loc[S.side == "Red", "p"] = 1 - S.loc[S.side == "Red", "p"]
S = S.dropna(subset=["p"])
S["win_"] = np.where(S.league == "WLDs", "Worlds", np.where(S.date < "2026-09-01", "before 1 Sep", "from 1 Sep"))
S["one_type"] = ((S.magic <= 0.5) | (S.magic >= 4.5)).astype(float); S.loc[S.magic.isna(), "one_type"] = np.nan
S["low_magic"] = (S.magic <= 1.0).astype(float); S.loc[S.magic.isna(), "low_magic"] = np.nan
res["how_common"] = {w: {"sides": len(d), "magic_count": d.magic.round(1).value_counts().sort_index().to_dict(),
                         "frontline_count": d.front.value_counts().sort_index().to_dict(),
                         "one_damage_type_share": round(float(d.one_type.mean()), 4), "no_frontline_share": round(float((d.front == 0).mean()), 4)}
                     for w, d in S.groupby("win_")}
def band(col, bins, labels):
    out = {}
    for w, d in list(S.groupby("win_")) + [("all", S)]:
        b = pd.cut(d[col], bins, labels=labels)
        g = d.groupby(b, observed=True).agg(sides=("result", "size"), won=("result", "mean"), v1_expected=("p", "mean"))
        g["won_minus_expected_pts"] = (g.won - g.v1_expected) * 100
        g["se_pts"] = np.sqrt(g.won * (1 - g.won) / g.sides) * 100
        out[w] = {str(k): {kk: round(float(vv), 3) for kk, vv in r.items()} for k, r in g.iterrows()}
    return out
res["by_magic_count"] = band("magic", [-0.1, 0.5, 1.0, 1.5, 2.5, 5], ["0-0.5", "1", "1.5", "2", "2.5+"])
res["by_frontline_count"] = band("front", [-0.1, 0, 1, 5], ["0", "1", "2+"])
res["one_damage_type"] = band("one_type", [-0.1, 0.5, 1.5], ["mixed", "one type"])

# model: v1 log-odds + draft terms (blue minus red), fitted before 1 Sep
G = S.pivot_table(index="gameid", columns="side", values=["result", "p", "one_type", "low_magic", "front", "magic"], aggfunc="first")
G = G.dropna(); G.columns = [f"{a}_{b}" for a, b in G.columns]
G["y"] = G.result_Blue; G["z"] = np.log(G.p_Blue / (1 - G.p_Blue)); G["win_"] = G.index.map(S.drop_duplicates("gameid").set_index("gameid").win_)
feats = {"one damage type": G.one_type_Blue - G.one_type_Red, "low magic (<=1)": G.low_magic_Blue - G.low_magic_Red,
         "no frontline": (G.front_Blue == 0).astype(float) - (G.front_Red == 0).astype(float), "frontline count": G.front_Blue - G.front_Red,
         "magic count": G.magic_Blue - G.magic_Red}
def fit(x, y, z, l2=1.0):
    b = np.zeros(1)
    for _ in range(50):
        p = 1 / (1 + np.exp(-(z + x * b[0]))); H = (x * x * p * (1 - p)).sum() + l2; g = (x * (y - p)).sum() - l2 * b[0]; b[0] += g / H
    return b[0]
ll = lambda p, y: float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
res["model"] = {}
for nm, x in feats.items():
    tr = G.win_ == "before 1 Sep"; b = fit(x[tr].values, G.y[tr].values, G.z[tr].values)
    o = {"weight": round(float(b), 4)}
    for w in ["before 1 Sep", "from 1 Sep", "Worlds"]:
        q = G.win_ == w; p0 = 1 / (1 + np.exp(-G.z[q])); p1 = 1 / (1 + np.exp(-(G.z[q] + b * x[q])))
        o[w] = {"games": int(q.sum()), "v1": round(ll(p0.values, G.y[q].values), 4), "v1_plus": round(ll(p1.values, G.y[q].values), 4),
                "games_where_it_differs": int((x[q] != 0).sum())}
    res["model"][nm] = o
json.dump(res, open(OUT, "w"), indent=1, default=str)
print(json.dumps(res["labels"], indent=1, default=str)); print(json.dumps(res["how_common"], indent=1, default=str))
for k in ["by_magic_count", "by_frontline_count", "one_damage_type"]:
    print(k)
    for w, d in res[k].items(): print("  ", w, {b: (v["sides"], round(v["won_minus_expected_pts"], 1), round(v["se_pts"], 1)) for b, v in d.items()})
for k, v in res["model"].items(): print(k, v)
