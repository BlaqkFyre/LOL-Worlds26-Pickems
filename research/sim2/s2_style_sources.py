"""Read-only: the learned champion curves and styles compared with three outside labels.
  1. lolalytics win rate by game length (Emerald+): solo scaling = win rate in the last 3 length buckets - the first 3 (pooled 16.17 + 16.20)
  2. Riot Data Dragon class tags (official, current version): Assassin, Fighter, Mage, Marksman, Support, Tank
  3. the app's CHAMP_ARCH lists (engage, poke, scaling, ...)
Compared against: pro scaling (gold-lead curve 25 min - 10 min, after player skill) and pro styles (siege, objectives, skirmish, pace),
champion-roles with 20+ pro games.
usage: python -I s2_style_sources.py champion_curves.csv champion_styles.csv lola_length.csv <champions.js>"""
import json, re, sys, urllib.request
import numpy as np
import pandas as pd

CUR, STY, LEN, JS = sys.argv[1:5]
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalpha())
C = pd.read_csv(CUR).merge(pd.read_csv(STY)[["champion", "position", "siege", "objectives", "skirmish", "pace"]], on=["champion", "position"])
C = C[C.games >= 20].copy(); C["k"] = C.champion.map(key)
print(f"champion-roles with 20+ pro games: {len(C)}")
# 1. lolalytics game length
L = pd.read_csv(LEN); g = L[[f"g{i}" for i in range(1, 8)]].values; w = L[[f"w{i}" for i in range(1, 8)]].values
L["k"] = L.champion.map(key)
agg = L.assign(**{f"g{i}": g[:, i - 1] for i in range(1, 8)}, **{f"w{i}": w[:, i - 1] for i in range(1, 8)}).groupby(["k", "position"]).sum(numeric_only=True)
agg["solo_scaling"] = 100 * (agg[["w5", "w6", "w7"]].sum(1) / agg[["g5", "g6", "g7"]].sum(1) - agg[["w1", "w2", "w3"]].sum(1) / agg[["g1", "g2", "g3"]].sum(1))
M = C.join(agg[["solo_scaling"]], on=["k", "position"]).dropna(subset=["solo_scaling"])
rc = lambda a, b: float(pd.Series(a).rank().corr(pd.Series(b).rank()))
print(f"\n1. lolalytics solo scaling v pro scaling ({len(M)} champion-roles): rank agreement {rc(M.solo_scaling, M.scaling):.3f}")
for r in ["top", "jng", "mid", "bot", "sup"]:
    s = M[M.position == r]
    if len(s) >= 5: print(f"   {r}: n {len(s)}, {rc(s.solo_scaling, s.scaling):.2f}")
# 2. Data Dragon tags
ver = json.loads(urllib.request.urlopen("https://ddragon.leagueoflegends.com/api/versions.json", timeout=60).read())[0]
dd = json.loads(urllib.request.urlopen(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json", timeout=60).read())["data"]
tags = {key(v["name"]): v["tags"][0] for v in dd.values()}
C["riot_class"] = C.k.map(tags)
print(f"\n2. Riot Data Dragon {ver}: champions matched {C.riot_class.notna().sum()} of {len(C)}; mean pro styles by primary class:")
print(C.groupby("riot_class")[["scaling", "siege", "objectives", "skirmish", "pace"]].mean().round(3).assign(n=C.groupby("riot_class").size()).to_string())
# 3. CHAMP_ARCH
txt = open(JS, encoding="utf-8").read(); block = txt[txt.index("const CHAMP_ARCH={"):]; block = block[:block.index("};")]
arch = {m.group(1): re.findall(r'"([^"]+)"', m.group(2)) for m in re.finditer(r'(\w+):\[([^\]]*)\]', block)}
print(f"\n3. app CHAMP_ARCH lists: { {k: len(v) for k, v in arch.items()} }; mean pro styles in each list v the rest:")
for a, names in arch.items():
    ks = {key(n) for n in names}; inn = C[C.k.isin(ks)]; out = C[~C.k.isin(ks)]
    print(f"   {a:<10} n {len(inn):>3} | scaling {inn.scaling.mean():+.0f} v {out.scaling.mean():+.0f} gold | siege {inn.siege.mean():+.4f} v {out.siege.mean():+.4f}"
          f" | objectives {inn.objectives.mean():+.4f} v {out.objectives.mean():+.4f} | pace {inn.pace.mean():+.4f} v {out.pace.mean():+.4f}")
