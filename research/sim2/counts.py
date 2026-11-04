"""Sim session 2, step 0 (read-only): how much champion data the Oracle's Elixir file holds.
Major leagues + internationals for fitting (WLDs rows before 1 Oct dropped); all leagues for player-champion history.
usage: python -I counts.py <OraclesElixir csv> <out json>"""
import json, sys
import pandas as pd

MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
df = pd.read_csv(sys.argv[1], low_memory=False)
df = df[~((df.league == "WLDs") & (df.date < "2026-10-01"))]
pl = df[df.position != "team"]
maj = pl[pl.league.isin(MAJOR)]
R = {"file_last_date": str(df.date.max()), "games_all": int(df.gameid.nunique()), "games_major": int(maj.gameid.nunique()),
     "worlds_games": int(maj[maj.league == "WLDs"].gameid.nunique()),
     "patches_major": maj.groupby("patch").gameid.nunique().sort_index().to_dict()}
cr = maj.groupby(["champion", "position"]).agg(g=("gameid", "size"), w=("result", "sum")).reset_index()
R["champion_role_pairs"] = int(len(cr))
R["champions_major"] = int(maj.champion.nunique())
for n in (10, 30, 100):
    R[f"champion_role_pairs_{n}plus"] = int((cr.g >= n).sum())
pc = pl.groupby(["playerid", "champion"]).size()
pcm = maj.groupby(["playerid", "champion"]).size()
R["player_champion_pairs_all_leagues"] = int(len(pc)); R["player_champion_pairs_major"] = int(len(pcm))
for n in (3, 5, 10):
    R[f"player_champion_pairs_major_{n}plus"] = int((pcm >= n).sum())
# lane pairs: same role, opposite sides, same game
a = maj[["gameid", "position", "side", "champion"]]
lp = a[a.side == "Blue"].merge(a[a.side == "Red"], on=["gameid", "position"], suffixes=("_b", "_r"))
lp["pair"] = lp.apply(lambda r: tuple(sorted((r.champion_b, r.champion_r))), axis=1)
lc = lp.groupby(["position", "pair"]).size()
R["lane_pairs"] = int(len(lc))
for n in (3, 5, 10):
    R[f"lane_pairs_{n}plus"] = int((lc >= n).sum())
# bot duos on one side
bd = maj[maj.position.isin(["bot", "sup"])].pivot_table(index=["gameid", "side"], columns="position", values="champion", aggfunc="first").dropna()
dc = bd.groupby(["bot", "sup"]).size()
R["bot_duos"] = int(len(dc)); R["bot_duos_10plus"] = int((dc >= 10).sum())
R["top_champion_roles"] = cr.sort_values("g", ascending=False).head(15).assign(wr=lambda d: (d.w / d.g).round(3)).to_dict("records")
json.dump(R, open(sys.argv[2], "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in R.items() if k != "top_champion_roles"}, indent=1, default=str))
