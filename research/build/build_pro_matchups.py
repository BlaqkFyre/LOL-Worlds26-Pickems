#!/usr/bin/env python3
"""Build js/pro-matchups.js: pro champion matchups and pairs on the recent patches, for the champ-select champion cards.

Luke (5 Nov 2026): the cards' counters / countered by / pairs should show meta champions and lean on pro data from the recent
patches first; solo-queue tables (METAsrc, metabot) only fill gaps.

From the Oracle's Elixir file, major leagues and Worlds (the file's "WLDs" rows before 1 Oct are a regional qualifier and are
left out), patches 16.15 and later (the app calls them 26.15+):
  meta   champions picked or banned: {champion: [picks, bans, games picked, wins]}
  lane   same-role matchups, "role|A|B": [games, A's wins, A's average gold lead at 15]   (3+ games)
  pair   same-team pairs, "A|B" (A before B alphabetically): [games, wins]               (3+ games)
Each game is counted once (by the file's game id). Champion names must match the app's (js/champions.js); any that don't are
listed and the build stops (a champion that was only banned and isn't in the app is left out, with a note).

Usage (from the repo root):  python research/build/build_pro_matchups.py [--csv path/to/file.csv]
Writes only js/pro-matchups.js. Needs Python 3.9+ and pandas.
"""
import argparse, glob, json, os, re, sys
from itertools import combinations
import pandas as pd

MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
ROLES = ["top", "jng", "mid", "bot", "sup"]; MINOR_FROM = 15; MIN_G = 3
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); ap.add_argument("--csv")
a = ap.parse_args()
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
csv = a.csv or (glob.glob(os.path.join(root, "research", "*OraclesElixir*.csv")) or [None])[0]
if not csv: sys.exit("no Oracle's Elixir CSV found in research/ (use --csv)")
cols = ["gameid", "league", "date", "patch", "side", "position", "champion", "result", "golddiffat15", "ban1", "ban2", "ban3", "ban4", "ban5"]
d = pd.read_csv(csv, low_memory=False, usecols=cols, dtype={"patch": str})
d = d[d.league.isin(MAJOR) & ~((d.league == "WLDs") & (d.date < "2026-10-01"))].copy()
d["minor"] = pd.to_numeric(d.patch.str.split(".").str[1], errors="coerce")
d = d[d.minor >= MINOR_FROM]
js = open(os.path.join(root, "js", "champions.js"), encoding="utf-8").read()
i = js.index("const CHAMP_DB=") + len("const CHAMP_DB="); depth = 0
for j in range(i, len(js)):  # the object literal is JSON; find its closing brace
    depth += js[j] == "{"; depth -= js[j] == "}"
    if depth == 0: break
app = set(json.loads(js[i:j + 1]))
P = d[d.position.isin(ROLES)].copy(); T = d[d.position == "team"]
bans = pd.concat([T[f"ban{i}"] for i in range(1, 6)]).dropna()
bad = sorted(n for n in set(P.champion) if n not in app)
if bad: sys.exit(f"picked champions not in js/champions.js: {bad}")
ban_only = sorted(n for n in set(bans) if n not in app)  # banned but never picked, and unknown to the app: left out
if ban_only: print("left out (banned only, not in the app's champion data):", ban_only)
bans = bans[~bans.isin(ban_only)]
meta = {}
for c, g in P.groupby("champion"): meta[c] = [int(len(g)), 0, int(g.gameid.nunique()), int(g.result.sum())]
for c, n in bans.value_counts().items(): meta.setdefault(c, [0, 0, 0, 0])[1] = int(n)
opp = P[["gameid", "position", "side", "champion", "golddiffat15"]].copy()
opp["side"] = opp.side.map({"Blue": "Red", "Red": "Blue"})
L = P.merge(opp.rename(columns={"champion": "opp", "golddiffat15": "_"}), on=["gameid", "position", "side"])
lane = {}
for (r, c, o), g in L.groupby(["position", "champion", "opp"]):
    if len(g) >= MIN_G:
        gd = g.golddiffat15.dropna()
        lane[f"{r}|{c}|{o}"] = [int(len(g)), int(g.result.sum()), int(round(gd.mean())) if len(gd) else None]
pair = {}
for (gid, s), g in P.groupby(["gameid", "side"]):
    res = int(g.result.iloc[0])
    for x, y in combinations(sorted(g.champion), 2):
        e = pair.setdefault(f"{x}|{y}", [0, 0]); e[0] += 1; e[1] += res
pair = {k: v for k, v in pair.items() if v[0] >= MIN_G}
games = int(P.gameid.nunique()); last = d.date.max()[:10]
out = {"asof": last, "patches": f"26.{MINOR_FROM}+", "games": games, "meta": meta, "lane": lane, "pair": pair}
txt = ("/* Pro champion matchups and pairs on the recent patches (26.%d and later) and Worlds, from the Oracle's Elixir file:\n"
       "   meta: {champion: [picks, bans, games picked, wins]}; lane: \"role|A|B\": [games, A wins, A's average gold lead at 15];\n"
       "   pair: \"A|B\" (alphabetical, same team): [games, wins]. Built by research/build/build_pro_matchups.py; %d games to %s.\n"
       "   Used first by the champion cards (counters, countered by, pairs); solo-queue tables only fill gaps. */\n"
       "const PRO_MU = %s;\n") % (MINOR_FROM, games, last, json.dumps(out, ensure_ascii=False, separators=(",", ":")))
open(os.path.join(root, "js", "pro-matchups.js"), "w", encoding="utf-8").write(txt)
print(f"js/pro-matchups.js: {games} games to {last}; {len(meta)} meta champions, {len(lane)} lane matchups, {len(pair)} pairs; {len(txt) // 1024} KB")
