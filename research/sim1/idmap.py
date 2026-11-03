"""Fixed ID lookup for the 16 Worlds teams and their players, keyed on Oracle's Elixir IDs (teamid, playerid).
Source of truth: the file's Worlds games from 1 Oct (play-ins and Swiss). App names come from js/data.js rosters.
usage: python -I idmap.py <csv> <data.js> <out_teams.csv> <out_players.csv>"""
import re, sys
import pandas as pd

APP = {"gen.g": "GEN", "hanwha life esports": "HLE", "t1": "T1", "dplus kia": "DK", "bilibili gaming": "BLG", "anyone's legend": "AL",
       "top esports": "TES", "invictus gaming": "IG", "g2 esports": "G2", "movistar koi": "MKOI", "karmine corp": "KC", "team liquid": "TL",
       "lyon": "LYON", "team secret whales": "TSW", "ctbc flying oyster": "CFO", "løs": "LOS"}
df = pd.read_csv(sys.argv[1], low_memory=False)
w = df[(df.league == "WLDs") & (df.date >= "2026-10-01")]
src = open(sys.argv[2], encoding="utf-8").read()
# rosters in data.js: team id then five ["Name",[...]] rows
roster = {}
for m in re.finditer(r'id:"([A-Z0-9]+)"(.*?)(?=id:"[A-Z0-9]+"|$)', src, re.S):
    roster[m.group(1)] = re.findall(r'\["([^"]+)",\[', m.group(2))[:5]
tw = w[w.position == "team"].groupby("teamid").agg(oe_name=("teamname", "first"), games=("gameid", "nunique")).reset_index()
tw["app_id"] = tw.oe_name.str.lower().map(APP)
teams = tw[tw.app_id.notna()].copy()
others = tw[tw.app_id.isna()]
assert teams.app_id.nunique() == 16 and teams.teamid.nunique() == 16, teams
# all names each Worlds team used across 2026 (to catch renames)
allnames = df[df.teamid.isin(teams.teamid) & (df.position == "team")].groupby("teamid").teamname.agg(lambda s: sorted(set(s)))
teams["oe_names_2026"] = teams.teamid.map(allnames).map(lambda x: " | ".join(x))
pw = w[w.position != "team"].merge(teams[["teamid", "app_id"]], on="teamid")
pl = pw.groupby(["playerid", "app_id", "position"]).agg(oe_name=("playername", "first"), worlds_games=("gameid", "nunique")).reset_index()
ROLE = {"top": 0, "jng": 1, "mid": 2, "bot": 3, "sup": 4}
app_names = []
for r in pl.itertuples():
    rs = roster.get(r.app_id, [])
    exact = [n for n in rs if n.lower() == str(r.oe_name).lower()]
    app_names.append(exact[0] if exact else "")
pl["app_name"] = app_names
pl["app_slot_name"] = [roster.get(r.app_id, [""] * 5)[ROLE[r.position]] if len(roster.get(r.app_id, [])) == 5 else "" for r in pl.itertuples()]
pl["note"] = ["" if a else ("not in app roster (sub?)" if s != r.oe_name else "") for a, s, r in zip(pl.app_name, pl.app_slot_name, pl.itertuples())]
teams[["app_id", "teamid", "oe_name", "oe_names_2026", "games"]].sort_values("app_id").to_csv(sys.argv[3], index=False)
pl.sort_values(["app_id", "position"]).to_csv(sys.argv[4], index=False)
print(f"teams {len(teams)}/16; other Worlds teams in file (play-ins): {sorted(others.oe_name)}")
print("teams with more than one 2026 name:", teams[teams.oe_names_2026.str.contains(r'\|')][['app_id', 'oe_names_2026']].values.tolist())
print(f"players {len(pl)}; matched to app roster {int((pl.app_name != '').sum())}; app roster slots {sum(len(v) for k, v in roster.items() if k in set(teams.app_id))}")
print("unmatched:", pl[pl.app_name == ""][["app_id", "position", "oe_name", "app_slot_name", "worlds_games"]].values.tolist())
miss = [(t, n) for t, ns in roster.items() if t in set(teams.app_id) for n in ns if n.lower() not in set(pl[pl.app_id == t].oe_name.str.lower())]
print("app roster names with no Worlds games in the file:", miss)
