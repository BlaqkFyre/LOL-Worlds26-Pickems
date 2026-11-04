"""Read-only: pool depth now (end of the file, 1 Nov) for every major-league player, and a card value on the S5 scale
(70 + 10 x standard deviations above the role average, clipped 40-99; reference = major-league players with 10+ games in 180 days).
Measures as in s2_pool.py: champions with 3+ games in the last 180 days (all leagues), meta pool = champions with 2+ games (180 days)
in the role's current pro meta (top 10 by pro picks in the last 30 days, i.e. mostly the Worlds patch).
Pool card = mean of the two measures' z-scores.
usage: python -I s2_pool_cards.py <OE csv> id_players.csv <out_csv>"""
import sys
from collections import Counter
import numpy as np
import pandas as pd

CSV, IDS, OUT = sys.argv[1:4]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
d = pd.read_csv(CSV, low_memory=False, usecols=["league", "date", "position", "playerid", "playername", "teamname", "champion"])
d = d[(d.position != "team") & d.playerid.notna() & ~((d.league == "WLDs") & (d.date < "2026-10-01"))].copy()
d["t"] = (pd.to_datetime(d.date.str[:10]) - pd.Timestamp("2026-01-01")).dt.days; T = d.t.max() + 1
meta = {r: set(d[(d.league.isin(MAJOR)) & (d.position == r) & (T - d.t <= 30)].champion.value_counts().head(10).index) for r in d.position.unique()}
h = d[T - d.t <= 180]
maj_players = d[d.league.isin(MAJOR)].groupby("playerid").agg(role=("position", lambda s: s.mode().iloc[0]), name=("playername", "last"),
                                                              team=("teamname", "last"), games=("champion", "size"))
rows = []
for pid, r in maj_players.iterrows():
    c = Counter(h[h.playerid == pid].champion)
    rows.append((pid, r["name"], r["team"], r["role"], int((T - d[d.playerid == pid].t <= 180).sum()),
                 sum(1 for v in c.values() if v >= 3), len({k for k, v in c.items() if v >= 2} & meta[r["role"]])))
P = pd.DataFrame(rows, columns=["playerid", "name", "team", "role", "games_180d", "pool_3plus", "meta_pool"])
ref = P[P.games_180d >= 10]
for k in ("pool_3plus", "meta_pool"):
    mu = ref.groupby("role")[k].mean(); sd = ref.groupby("role")[k].std()
    P["z_" + k] = (P[k] - P.role.map(mu)) / P.role.map(sd)
P["pool_card"] = (70 + 10 * (P.z_pool_3plus + P.z_meta_pool) / 2).clip(40, 99).round()
ids = pd.read_csv(IDS)
W = ids[["playerid", "app_id", "position"]].merge(P, on="playerid", how="left")
W[["app_id", "position", "name", "games_180d", "pool_3plus", "meta_pool", "pool_card"]].sort_values(["app_id", "position"]).to_csv(OUT, index=False)
print("current meta (top 10 per role, last 30 days):", {k: sorted(v) for k, v in meta.items()})
print(W.sort_values("pool_card", ascending=False)[["app_id", "position", "name", "pool_3plus", "meta_pool", "pool_card"]].head(12).to_string(index=False))
print(W.sort_values("pool_card")[["app_id", "position", "name", "pool_3plus", "meta_pool", "pool_card"]].head(8).to_string(index=False))
print(W[W.name.isin(["Faker", "Canyon", "Kanavi", "Knight", "Chovy"])][["app_id", "position", "name", "pool_3plus", "meta_pool", "pool_card"]].to_string(index=False))
