"""Match Leaguepedia 2026 Player of the Game (per game) and series MVP awards to the Oracle's Elixir file.
Per game: same two teams, same game number in the series, start within 6 hours (UTC); MVP name matched to one of the 10 players.
Per series: same two teams, start within 12 hours of the series' first game; the series' games are the file's games between those
teams from that start until the next 30 hours.
Writes pog_games_matched.csv (one row per player per matched game, with mvp = 1/0) and pog_series_matched.csv, and prints
match rates and unmatched names.
usage: python -I pog_match.py <OE csv> <pog dir>"""
import json, os, re, sys, unicodedata
import pandas as pd

CSV, D = sys.argv[1:3]
GAME_LEAGUES = {"LPL": "LPL", "LCS": "LCS", "2026 First Stand": "FST"}
SERIES_LEAGUES = {"LCK": "LCK", "LPL": "LPL", "LEC": "LEC", "CBLOL": "CBLOL", "LCP": "LCP", "LCS": "LCS", "Esports World Cup 2026": "EWC",
                  "2026 Season World Championship": "WLDs", "2026 First Stand": "FST", "2026 Mid-Season Invitational": "MSI"}
norm = lambda x: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower())
ALIAS = {"ninjasinpyjamascn": "ninjasinpyjamas", "brion": "hanjinbrion", "drx": "kiwoomdrx"}  # Leaguepedia -> file team names
tnorm = lambda x: (lambda k: ALIAS.get(k, k))(norm(re.sub(r"\s*\(.*\)$", "", str(x))))
pname = lambda x: norm(re.sub(r"\s*\(.*\)$", "", str(x)))
cols = ["gameid", "league", "date", "game", "side", "position", "playername", "teamname", "result", "gamelength", "kills", "deaths", "assists",
        "teamkills", "damageshare", "earnedgoldshare", "golddiffat15", "csdiffat15", "xpdiffat15", "visionscore", "dpm", "damagetakenperminute",
        "firstbloodkill", "firstbloodassist", "cspm", "vspm", "champion"]
oe = pd.read_csv(CSV, low_memory=False, usecols=cols)
oe = oe[~((oe.league == "WLDs") & (oe.date < "2026-10-01"))]
oe["t"] = pd.to_datetime(oe.date)
T = oe[oe.position == "team"].copy(); P = oe[oe.position != "team"].copy()
T["tn"] = T.teamname.map(tnorm)
games = T.groupby("gameid").agg(league=("league", "first"), t=("t", "first"), n=("game", "first"), teams=("tn", lambda s: frozenset(s))).reset_index()

def match_games(rows, lg):
    G = games[games.league == lg]; out, miss = [], []
    for r in rows:
        if not r.get("Date") or not r.get("Team1"): miss.append(("no date/teams", r["GameId"])); continue
        key, t, n = frozenset([tnorm(r["Team1"]), tnorm(r["Team2"])]), pd.Timestamp(r["Date"]), r.get("N")
        c = G[(G.teams == key) & ((G.t - t).abs() <= pd.Timedelta(hours=6))]
        if n is not None and len(c) > 1: c = c[c.n == n]
        if len(c) != 1: miss.append((f"{len(c)} candidates", r["GameId"], r["Team1"], r["Team2"], r["Date"])); continue
        out.append((c.gameid.iloc[0], r["MVP"], r["Page"]))
    return out, miss

g = json.load(open(os.path.join(D, "pog_games_2026.json"), encoding="utf-8"))
allm, rows = [], []
for k, lg in GAME_LEAGUES.items():
    sub = [r for r in g if r["Page"].split("/")[0] == k and r["MVP"] not in ("N/A", "None", "") and "Showmatch" not in r["Page"]]
    m, miss = match_games(sub, lg)
    print(f"{k}: {len(sub)} awards, {len(m)} matched to the file; unmatched {len(miss)}", miss[:4])
    allm += [(a, b, c, lg) for a, b, c in m]
name_miss = []
for gid, mvp, page, lg in allm:
    p = P[P.gameid == gid].copy(); hit = p.playername.map(norm) == pname(mvp)
    if hit.sum() != 1: name_miss.append((gid, mvp, list(p.playername))); continue
    p["mvp"] = hit.astype(int); p["page"] = page; p["lg"] = lg; rows.append(p)
print("player-name misses:", len(name_miss), name_miss[:6])
R = pd.concat(rows); R.to_csv(os.path.join(D, "pog_games_matched.csv"), index=False)
print("matched games with the MVP found among the 10 players:", R.gameid.nunique())

# series
s = json.load(open(os.path.join(D, "pog_series_2026.json"), encoding="utf-8"))
srows, smiss, sname = [], [], []
for r in s:
    k = r["Page"].split("/")[0]
    if k not in SERIES_LEAGUES or r["MVP"] in ("N/A", "None", "") or "Showmatch" in r["Page"] or not r.get("Date"): continue
    lg = SERIES_LEAGUES[k]; G = games[games.league == lg]
    key, t = frozenset([tnorm(r["Team1"]), tnorm(r["Team2"])]), pd.Timestamp(r["Date"])
    c = G[(G.teams == key) & (G.t >= t - pd.Timedelta(hours=12)) & (G.t <= t + pd.Timedelta(hours=30))].sort_values("t")
    if c.empty: smiss.append((k, r["Team1"], r["Team2"], r["Date"])); continue
    c = c[c.t <= c.t.iloc[0] + pd.Timedelta(hours=8)]  # one series: games within 8 h of its first
    p = P[P.gameid.isin(c.gameid)].copy(); hit = p.playername.map(norm) == pname(r["MVP"])
    if not hit.any(): sname.append((k, r["MVP"], r["Team1"], r["Team2"])); continue
    p["mvp"] = hit.astype(int); p["series"] = r["MatchId"]; p["lg"] = lg; p["n_games"] = c.gameid.nunique()
    p["score"] = f'{r["S1"]}-{r["S2"]}'; srows.append(p)
print(f"series: matched {len(srows)}; no games found {len(smiss)}", smiss[:5]); print("series name misses", len(sname), sname[:6])
S = pd.concat(srows); S.to_csv(os.path.join(D, "pog_series_matched.csv"), index=False)
print(S.groupby("lg").series.nunique().to_dict())
