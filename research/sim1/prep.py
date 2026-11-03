"""Sim session 1, step 1: one row per game for the major leagues and internationals (read-only on the CSV).
Each game once (by gameid); WLDs rows before 1 Oct dropped (regional qualifier). Team identity = Oracle's Elixir teamid.
usage: python -I prep.py <csv> <out_games.csv>"""
import sys
import pandas as pd

MAJOR = ["LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"]
INTL = {"FST", "MSI", "EWC", "WLDs"}
APP = {"Gen.G": "GEN", "Hanwha Life Esports": "HLE", "T1": "T1", "Dplus KIA": "DK", "Bilibili Gaming": "BLG",
       "Anyone's Legend": "AL", "Top Esports": "TES", "Invictus Gaming": "IG", "G2 Esports": "G2", "Movistar KOI": "MKOI",
       "Karmine Corp": "KC", "Team Liquid": "TL", "LYON": "LYON", "Team Secret Whales": "TSW", "CTBC Flying Oyster": "CFO", "LØS": "LOS"}

APP = {k.lower(): v for k, v in APP.items()}
df = pd.read_csv(sys.argv[1], low_memory=False)
t = df[(df.position == "team") & df.league.isin(MAJOR)]
t = t[~((t.league == "WLDs") & (t.date < "2026-10-01"))]

# each team's home league = the domestic league it played most games in (internationals only link leagues)
dom = t[~t.league.isin(INTL)]
home = dom.groupby("teamid").league.agg(lambda s: s.value_counts().index[0])

rows, skipped = [], 0
for gid, g in t.groupby("gameid"):
    if len(g) != 2 or set(g.side) != {"Blue", "Red"}:
        skipped += 1; continue
    b, r = g[g.side == "Blue"].iloc[0], g[g.side == "Red"].iloc[0]
    if int(b.result) + int(r.result) != 1:
        skipped += 1; continue
    rows.append({"gameid": gid, "date": b.date, "league": b.league, "patch": b.patch,
                 "blue": b.teamid, "red": r.teamid, "blue_name": b.teamname, "red_name": r.teamname,
                 "blue_app": APP.get(str(b.teamname).lower(), ""), "red_app": APP.get(str(r.teamname).lower(), ""),
                 "blue_home": home.get(b.teamid, ""), "red_home": home.get(r.teamid, ""),
                 "blue_win": int(b.result), "len": int(b.gamelength)})
out = pd.DataFrame(rows).sort_values("date")
out.to_csv(sys.argv[2], index=False)
print(f"games {len(out)} (skipped {skipped}) · {out.date.min()[:10]} to {out.date.max()[:10]}")
print(out.league.value_counts().to_string())
print(f"teams {pd.unique(out[['blue', 'red']].values.ravel()).size}; teams with no home league (internationals only): "
      f"{sorted(set(out.loc[out.blue_home == '', 'blue_name']) | set(out.loc[out.red_home == '', 'red_name']))}")
print(f"blue side won {out.blue_win.mean():.3f}")
print("app teams found:", sorted(set(out.blue_app) | set(out.red_app) - {''}))
