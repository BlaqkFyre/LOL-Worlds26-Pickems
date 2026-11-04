"""Sim session 2, part 2 (read-only): comfort at Worlds, checked directly.
For every Worlds pick (play-ins + Swiss in the file, 73 games), the player's earlier games on that champion (all leagues incl. minor,
days before the game only). Picks grouped 0-2 / 3-9 / 10+ games, per role and overall:
  picks, win rate, the win rate v1 expected for that side, and the difference (won - expected).
Note: the five picks of one side share the same game result, so picks are not independent; games are counted too.
usage: python -I s2_comfort_worlds.py <OE csv> v1_games.csv <out_csv>"""
import sys
from collections import defaultdict
import numpy as np
import pandas as pd

CSV, V1, OUT = sys.argv[1:4]
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "side", "position", "playerid", "playername", "champion", "result"])
raw = raw[(raw.position != "team") & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy()
raw["day"] = raw.date.str[:10]
pv = pd.read_csv(V1).set_index("gameid").p_v1.to_dict()
cnt = defaultdict(int); rows = []
for d, day_rows in raw.sort_values("day").groupby("day", sort=True):
    for r in day_rows[day_rows.league == "WLDs"].itertuples(index=False):
        p = pv.get(r.gameid, np.nan)
        exp = p if r.side == "Blue" else 1 - p
        rows.append((r.gameid, r.position, r.playername, r.champion, cnt[(r.playerid, r.champion)], r.result, exp))
    for r in day_rows.itertuples(index=False): cnt[(r.playerid, r.champion)] += 1
W = pd.DataFrame(rows, columns=["gameid", "role", "player", "champion", "prior_games", "won", "expected"]).dropna(subset=["expected"])
W["band"] = pd.cut(W.prior_games, [-1, 2, 9, 10**6], labels=["0-2", "3-9", "10+"])
out = []
for role in ["top", "jng", "mid", "bot", "sup", "all"]:
    S = W if role == "all" else W[W.role == role]
    for band, B in S.groupby("band", observed=True):
        out.append({"role": role, "band": band, "picks": len(B), "games": B.gameid.nunique(), "win_rate": round(B.won.mean(), 3),
                    "v1_expected": round(B.expected.mean(), 3), "won_minus_expected": round((B.won - B.expected).mean(), 3)})
T = pd.DataFrame(out); T.to_csv(OUT, index=False)
pd.set_option("display.width", 160); print(f"Worlds picks with v1 odds: {len(W)} ({W.gameid.nunique()} games)"); print(T.to_string(index=False))
print("\nLowest-comfort Worlds picks (0 earlier games):")
print(W[W.prior_games == 0][["role", "player", "champion", "won"]].sort_values("role").to_string(index=False))
