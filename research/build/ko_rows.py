"""Build js/worlds-live.js game rows from Oracle's Elixir rows (main CSV or Luke's saved spreadsheet copy).
usage: python -I ko_rows.py <repo> <source csv|xlsx> <round label> <first UTC date> [<last UTC date>]
Prints one JSON row per game. Dates in rows are US event days (UTC - 8 h)."""
import json, re, sys
from datetime import datetime, timedelta
import pandas as pd

REPO, SRC, RLAB, D0 = sys.argv[1:5]; D1 = sys.argv[5] if len(sys.argv) > 5 else "9999"
H = open(f"{REPO}/research/2026_LoL_esports_match_data_from_OraclesElixir.csv", encoding="utf-8").readline().strip().split(",")
if SRC.endswith(".xlsx"):
    raw = pd.read_excel(SRC, header=None, dtype=str)
    d = raw.iloc[1:].dropna(how="all").iloc[:, :165]; d.columns = H
else:
    d = pd.read_csv(SRC, dtype=str, low_memory=False)
d = d[(d.league == "WLDs") & (d.date >= D0) & (d.date <= D1)]
TEAM_ID = {"Gen.G": "GEN", "Hanwha Life Esports": "HLE", "T1": "T1", "Dplus Kia": "DK", "Bilibili Gaming": "BLG",
           "Anyone's Legend": "AL", "Top Esports": "TES", "Invictus Gaming": "IG", "G2 Esports": "G2",
           "Movistar KOI": "MKOI", "Karmine Corp": "KC", "Team Liquid": "TL", "LYON": "LYON",
           "Team Secret Whales": "TSW", "CTBC Flying Oyster": "CFO", "LØS": "LOS"}
names = {n.lower(): n for n in re.findall(r'\["([^"]+)",\[', open(f"{REPO}/js/data.js", encoding="utf-8").read())}
ROLE = {"top": "TOP", "jng": "JGL", "mid": "MID", "bot": "ADC", "sup": "SUP"}
I = lambda v: int(float(v))
num = lambda v: None if pd.isna(v) or v == "" else I(v)
for gid, r in sorted(d.groupby("gameid"), key=lambda kv: kv[1].date.iloc[0]):
    t = r[r.position == "team"].set_index("side"); p = r[r.position != "team"]
    side = {s: TEAM_ID[t.teamname[s]] for s in ("Blue", "Red")}
    L = I(r.gamelength.iloc[0])
    us = (datetime.fromisoformat(r.date.iloc[0]) - timedelta(hours=8)).date().isoformat()
    row = {"d": us, "r": RLAB, "g": I(r.game.iloc[0]), "blue": side["Blue"], "red": side["Red"],
           "w": side["Blue"] if t.result["Blue"] == "1" else side["Red"], "len": f"{L // 60}:{L % 60:02d}",
           "bans": {s.lower(): [t[f"ban{i}"][s] for i in range(1, 6)] for s in ("Blue", "Red")}, "pl": {}}
    for s in ("Blue", "Red"):
        tk = I(t.kills[s]); out = []
        for pos in ("top", "jng", "mid", "bot", "sup"):
            x = p[(p.side == s) & (p.position == pos)].iloc[0]
            k, de, a = I(x.kills), I(x.deaths), I(x.assists)
            out.append([ROLE[pos], names.get(x.playername.lower(), x.playername), x.champion, k, de, a, num(x["total cs"]),
                        num(x.csdiffat15), round(float(x.damageshare), 2), round((k + a) / tk, 2) if tk else 0])
        row["pl"][s.lower()] = out
    row["obj"] = {s.lower(): [I(t.dragons[s]), I(t.barons[s]), I(t.heralds[s]), I(t.void_grubs[s]), I(t.towers[s])] for s in ("Blue", "Red")}
    row["fp"] = side["Blue"] if t.firstPick["Blue"] == "1" else side["Red"]
    print(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
