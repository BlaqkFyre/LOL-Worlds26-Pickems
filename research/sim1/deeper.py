"""Read-only analysis for Luke's questions (3 Nov):
 A. League gaps: in cross-league games, when does the stronger league pull ahead (gold at 10/15/20/25), in which roles, and do leads hold?
 B. How much of each team's fitted rating do its players' stats explain (the rest = what stats don't capture: macro, calls, teamwork)?
 C. Do the 3 weak skills matter in a game state? (ADC damage and top teamfight when games go long; top steadiness and upsets.)
usage: python -I deeper.py <csv> games.csv gfeat.csv out/team_ratings_now.csv out/player_cards_league_adjusted.csv"""
import sys
import numpy as np
import pandas as pd

MAJOR = ["LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"]
L = {"CBLOL": -0.79, "LCK": 1.49, "LCP": -0.72, "LCS": -0.12, "LEC": 0.14, "LPL": 0.95}
df = pd.read_csv(sys.argv[1], low_memory=False)
G = pd.read_csv(sys.argv[2]); GF = pd.read_csv(sys.argv[3]); TR = pd.read_csv(sys.argv[4]); PC = pd.read_csv(sys.argv[5])
gids = set(G.gameid)
pl = df[(df.position != "team") & df.gameid.isin(gids)]
home = {}
for r in G.itertuples():
    home[(r.gameid, "Blue")] = r.blue_home if isinstance(r.blue_home, str) else ""; home[(r.gameid, "Red")] = r.red_home if isinstance(r.red_home, str) else ""

# A. team gold lead by time, from the stronger league's side
tm = pl.groupby(["gameid", "side"])[["golddiffat10", "golddiffat15", "golddiffat20", "golddiffat25"]].sum(min_count=5).reset_index()
res = pl.groupby(["gameid", "side"]).result.first().reset_index()
tm = tm.merge(res, on=["gameid", "side"])
tm["home"] = [home[(g, s)] for g, s in zip(tm.gameid, tm.side)]
opp = tm.copy(); opp["side"] = opp.side.map({"Blue": "Red", "Red": "Blue"})
tm = tm.merge(opp[["gameid", "side", "home"]].rename(columns={"home": "opp_home"}), on=["gameid", "side"])
x = tm[(tm.home != "") & (tm.opp_home != "") & (tm.home != tm.opp_home)].copy()
x["gap"] = x.home.map(L) - x.opp_home.map(L)
x = x[x.gap > 0]  # one row per game: the stronger league's side
GROUPS = {"LCK v LPL": lambda r: {r.home, r.opp_home} == {"LCK", "LPL"},
          "LCK/LPL v LEC/LCS": lambda r: r.home in ("LCK", "LPL") and r.opp_home in ("LEC", "LCS"),
          "LCK/LPL v LCP/CBLOL": lambda r: r.home in ("LCK", "LPL") and r.opp_home in ("LCP", "CBLOL"),
          "LEC/LCS v LCP/CBLOL": lambda r: r.home in ("LEC", "LCS") and r.opp_home in ("LCP", "CBLOL")}
print("A. Cross-league games, seen from the stronger league (model gap in log-odds):")
for name, f in GROUPS.items():
    s = x[x.apply(f, axis=1)]
    if not len(s): continue
    ahead15 = s.golddiffat15 > 0
    print(f"  {name}: games {len(s)}, stronger won {s.result.mean():.0%} | avg gold lead at 10 {s.golddiffat10.mean():+.0f}, 15 {s.golddiffat15.mean():+.0f}, "
          f"20 {s.golddiffat20.mean():+.0f}, 25 {s.golddiffat25.mean():+.0f} | ahead at 15: {ahead15.mean():.0%} of games, won {s[ahead15].result.mean():.0%}; "
          f"behind at 15 won {s[~ahead15].result.mean():.0%}")
# by role, gold lead at 15 in cross-league games (stronger side)
pr = pl.merge(x[["gameid", "side", "gap"]], on=["gameid", "side"])
print("  Stronger league's average gold lead at 15 by role (all cross-league games):", pr.groupby("position").golddiffat15.mean().round(0).to_dict())
print("  per 1.0 of league gap:", (pr.groupby("position").apply(lambda d: (d.golddiffat15 * d.gap).sum() / (d.gap ** 2).sum())).round(0).to_dict())

# B. how much of team rating do player stats explain?
last = GF.merge(G[["gameid", "date"]], on="gameid")
PCm = PC[PC.games >= 10]
team_players = pl.sort_values("date").groupby(["teamname", "position"]).playername.last().reset_index()
agg = team_players.merge(PC[["name", "role", "Overall"]].assign(position=lambda d: d.role.map({"TOP": "top", "JGL": "jng", "MID": "mid", "ADC": "bot", "SUP": "sup"})),
                         left_on=["playername", "position"], right_on=["name", "position"], how="left").groupby("teamname").Overall.sum(min_count=5)
T = TR.merge(agg.rename("players_sum"), left_on="team", right_index=True, how="inner").dropna()
T["league_L"] = T.home.map(L).fillna(0)
A = np.c_[np.ones(len(T)), T.players_sum, T.league_L]
coef, *_ = np.linalg.lstsq(A, T.rating, rcond=None)
fitv = A @ coef; r2 = 1 - ((T.rating - fitv) ** 2).sum() / ((T.rating - T.rating.mean()) ** 2).sum()
r2L = 1 - ((T.rating - np.c_[np.ones(len(T)), T.league_L] @ np.linalg.lstsq(np.c_[np.ones(len(T)), T.league_L], T.rating, rcond=None)[0]) ** 2).sum() / ((T.rating - T.rating.mean()) ** 2).sum()
print(f"\nB. Team rating explained (71 teams): league alone R2 {r2L:.2f}; league + players' summed stat overall R2 {r2:.2f}")
T["unexplained"] = T.rating - fitv
APP = ["GEN", "HLE", "T1", "DK", "BLG", "IG", "TES", "AL", "G2", "KC", "LYON", "TL", "MKOI", "LOS", "TSW", "CFO"]
print("  Worlds teams: rating, part from players+league, unexplained (macro/teamwork the stats don't show):")
for r in T[T.team.isin(APP)].sort_values("unexplained", ascending=False).itertuples():
    print(f"   {r.team:5s} rating {r.rating:+.2f}  explained {r.rating - r.unexplained:+.2f}  unexplained {r.unexplained:+.2f}")

# C. weak skills in a game state
GFm = GF.merge(G[["gameid", "len", "blue_win"]], on="gameid")
def diff(feat, pos):
    d = GFm[GFm.position == pos].pivot_table(index="gameid", columns="side", values="e_" + feat)
    return (d["Blue"] - d["Red"]).rename(feat)
Z = pd.concat([diff("damage", "bot"), diff("lategame", "bot"), diff("teamfight", "top"), diff("cons_steady", "top"), diff("laning", "top")], axis=1)
Z = Z.join(G.set_index("gameid")[["len", "blue_win"]])
def slope(sub, col):
    xx = sub[col].values; yy = sub.blue_win.values - sub.blue_win.mean()
    return (xx * yy).sum() / (xx * xx).sum(), len(sub)
print("\nC. Does the skill gap line up with winning, by game length? (slope of win on pre-game skill gap; per 1.0 skill z)")
for col in ("damage", "lategame", "teamfight", "laning"):
    s1, n1 = slope(Z[Z.len < 30 * 60], col); s2, n2 = slope(Z[(Z.len >= 30 * 60) & (Z.len < 36 * 60)], col); s3, n3 = slope(Z[Z.len >= 36 * 60], col)
    print(f"  {col:9s} under 30 min {s1:+.3f} (n {n1}) · 30-36 {s2:+.3f} (n {n2}) · 36+ {s3:+.3f} (n {n3})")
