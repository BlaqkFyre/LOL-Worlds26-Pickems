"""Sim session 2, part 2 (read-only): the Worlds comfort check repeated on other events.
Groups: Worlds, MSI, EWC, First Stand, domestic playoffs (major leagues, playoffs flag = 1), domestic regular season (for contrast).
For every pick with v1 odds: the player's earlier games on that champion (all leagues incl. minor, earlier days only),
banded 0-2 / 3-9 / 10+; per role and group: picks, games, won - expected (v1) in percentage points, and a rough standard error.
usage: python -I s2_comfort_events.py <OE csv> v1_games.csv <out_csv>"""
import sys
from collections import defaultdict
import numpy as np
import pandas as pd

CSV, V1, OUT = sys.argv[1:4]
DOM = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL"}
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "playoffs", "side", "position", "playerid", "champion", "result"])
raw = raw[(raw.position != "team") & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy()
raw["day"] = raw.date.str[:10]
def group(r):
    if r.league == "WLDs": return "Worlds"
    if r.league in ("MSI", "EWC", "FST"): return {"MSI": "MSI", "EWC": "EWC", "FST": "First Stand"}[r.league]
    if r.league in DOM: return "Domestic playoffs" if r.playoffs == 1 else "Domestic regular season"
    return None
pv = pd.read_csv(V1).set_index("gameid").p_v1.to_dict()
cnt = defaultdict(int); rows = []
for d, day_rows in raw.sort_values("day").groupby("day", sort=True):
    for r in day_rows.itertuples(index=False):
        g = group(r); p = pv.get(r.gameid, np.nan)
        if g and not np.isnan(p):
            rows.append((g, r.gameid, r.position, cnt[(r.playerid, r.champion)], r.result, p if r.side == "Blue" else 1 - p))
    for r in day_rows.itertuples(index=False): cnt[(r.playerid, r.champion)] += 1
W = pd.DataFrame(rows, columns=["group", "gameid", "role", "prior", "won", "expected"])
W["band"] = pd.cut(W.prior, [-1, 2, 9, 10**6], labels=["0-2", "3-9", "10+"])
out = []
for grp in ["Worlds", "MSI", "EWC", "First Stand", "Domestic playoffs", "big events together", "Domestic regular season"]:
    G = W[W.group.isin(["Worlds", "MSI", "EWC", "First Stand", "Domestic playoffs"])] if grp == "big events together" else W[W.group == grp]
    for role in ["top", "jng", "mid", "bot", "sup", "all"]:
        S = G if role == "all" else G[G.role == role]
        for band, B in S.groupby("band", observed=True):
            diff = B.won - B.expected; se = diff.std() / np.sqrt(B.gameid.nunique()) if len(B) > 1 else np.nan
            out.append({"group": grp, "role": role, "band": band, "picks": len(B), "games": B.gameid.nunique(),
                        "won_minus_expected": round(100 * diff.mean(), 1), "rough_se": round(100 * se, 1)})
T = pd.DataFrame(out); T.to_csv(OUT, index=False)
P = T.pivot_table(index=["group", "role"], columns="band", values="won_minus_expected", observed=False)

pd.set_option("display.width", 200); print(W.groupby("group").gameid.nunique().to_dict())
print(P.round(1).to_string())
