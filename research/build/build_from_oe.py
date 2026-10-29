#!/usr/bin/env python3
"""Rebuild the app's real-data tables from the Oracle's Elixir 2026 match data file.

What it builds (each game counted once, by Oracle's Elixir game ID):
  1. js/h2h.js and research/model/h2h_2026.json
       2026 head-to-head (games won-lost, events met at) between the 16 Worlds teams.
  2. The play-in tables in js/worlds-live.js (`pinTeam` and `pin`)
       Worlds play-in games (15-18 Oct) per player: {champion: [games, wins]}.
  3. A check of every game already in js/worlds-live.js against the file
       (champions, K/D/A, bans, length, objectives), written to research/model/oe_check.txt.
       With --fix it also fills what the file has and worlds-live lacks or has wrong:
       game length, missing bans (bans: null), objectives, CS difference at 15.

It never adds new games to worlds-live.js and never touches simulated tournament data.

Usage (from the repo root):
  python research/build/build_from_oe.py            # build tables + write the check report
  python research/build/build_from_oe.py --fix      # same, and correct worlds-live.js from the file
  python research/build/build_from_oe.py --csv path/to/file.csv

Needs Python 3.9+ and pandas (pip install pandas).
"""
import argparse, glob, json, os, re, sys
from datetime import date

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = lambda *a: os.path.join(ROOT, *a)

# Oracle's Elixir team names -> app team IDs (the 16 Worlds Swiss teams)
TEAM_ID = {"Gen.G": "GEN", "Hanwha Life Esports": "HLE", "T1": "T1", "Dplus Kia": "DK", "Bilibili Gaming": "BLG",
           "Anyone's Legend": "AL", "Top Esports": "TES", "Invictus Gaming": "IG", "G2 Esports": "G2",
           "Movistar KOI": "MKOI", "Karmine Corp": "KC", "Team Liquid": "TL", "LYON": "LYON",
           "Team Secret Whales": "TSW", "CTBC Flying Oyster": "CFO", "LØS": "LOS"}
# play-in teams that did not reach the Swiss stage (short tags for the champion cards)
PLAYIN_TAG = {"Cloud9": "C9", "FURIA": "FUR", "MVK Esports": "MVK"}
EVENT = {"WLDs": "Worlds", "FST": "First Stand", "EWC": "EWC", "MSI": "MSI", "KeSPA Cup": "KeSPA Cup"}
# Worlds stages by UTC date in the file. Rows labelled WLDs before 1 Oct are not Worlds games (regional qualifier).
PLAYIN = ("2026-10-15", "2026-10-20")
SWISS_FROM = "2026-10-23"


def find_csv(arg):
    if arg:
        return arg
    hits = sorted(glob.glob(P("research", "*OraclesElixir*.csv")))
    if not hits:
        sys.exit("No Oracle's Elixir CSV found in research/. Download it and save it there, or pass --csv.")
    return hits[-1]


def app_player_names():
    """Player names as the app spells them (js/data.js), keyed by lower case."""
    src = open(P("js", "data.js"), encoding="utf-8").read()
    return {n.lower(): n for n in re.findall(r'\["([^"]+)",\[', src)}


def load_live():
    src = open(P("js", "worlds-live.js"), encoding="utf-8").read()
    i = src.index("games:[") + len("games:")
    j = src.index("]};", i) + 1
    return src, json.loads(src[i:j]), (i, j)


def build_h2h(df):
    t = df[(df.position == "team") & df.teamname.isin(TEAM_ID)]
    H = {}
    for _, x in t.groupby("gameid"):
        if len(x) != 2:
            continue
        a, b = x.iloc[0], x.iloc[1]
        A, B = TEAM_ID[a.teamname], TEAM_ID[b.teamname]
        w = A if a.result == 1 else B
        ev = EVENT.get(a.league, a.league)
        for p, q in ((A, B), (B, A)):
            e = H.setdefault(p, {}).setdefault(q, [0, 0, []])
            e[0 if w == p else 1] += 1
            if ev not in e[2]:
                e[2].append(ev)
    asof = str(t.date.max())[:10]
    os.makedirs(P("research", "model"), exist_ok=True)
    json.dump(H, open(P("research", "model", "h2h_2026.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
    js = ("/* Real 2026 head-to-head between the 16 Worlds teams: games won-lost, every pro game in 2026 (domestic,\n"
          "   international and Worlds so far). Built from the Oracle's Elixir 2026 match data file (research/, kept local)\n"
          "   by research/build/build_from_oe.py; each game counted once by its game ID. Simulated tournament games are\n"
          "   never added here.\n"
          "   H2H_2026.g[A][B] = [A's wins, A's losses, [events they met at]] */\n"
          f"const H2H_2026 = {{asof:\"{asof}\", g:{json.dumps(H, separators=(',', ':'), ensure_ascii=False)}}};\n")
    open(P("js", "h2h.js"), "w", encoding="utf-8").write(js)
    return asof, sum(len(v) for v in H.values()) // 2


def build_playin(df, names):
    w = df[(df.league == "WLDs") & (df.date >= PLAYIN[0]) & (df.date < PLAYIN[1]) & (df.position != "team")]
    pin, tag = {}, {}
    for _, r in w.iterrows():
        n = names.get(str(r.playername).lower(), r.playername)
        e = pin.setdefault(n, {}).setdefault(r.champion, [0, 0])
        e[0] += 1
        e[1] += int(r.result)
        if r.teamname in PLAYIN_TAG:
            tag[n] = PLAYIN_TAG[r.teamname]
        elif r.teamname in TEAM_ID:
            tag[n] = TEAM_ID[r.teamname]
    return pin, tag, w.gameid.nunique()


def write_playin(src, pin, tag):
    pt = "  pinTeam:{" + ",".join(f'{json.dumps(k, ensure_ascii=False) if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k) else k}:"{v}"' for k, v in tag.items()) + "},"
    pn = "  pin:" + json.dumps(pin, separators=(",", ":"), ensure_ascii=False) + ","
    src = re.sub(r"^  pinTeam:\{.*\},$", lambda m: pt, src, count=1, flags=re.M)
    src = re.sub(r"^  pin:\{.*\},$", lambda m: pn, src, count=1, flags=re.M)
    return src


def check_live(df, games, names, fix):
    w = df[(df.league == "WLDs") & (df.date >= SWISS_FROM)]
    t, pl = w[w.position == "team"], w[w.position != "team"]
    by_champs = {tuple(sorted(g.champion)): gid for gid, g in pl.groupby("gameid")}
    lines, changed = [], 0
    for g in games:
        tag = f"{g['d']} {g['blue']} vs {g['red']} g{g['g']}"
        champs = tuple(sorted(r[2] for sd in ("blue", "red") for r in g["pl"][sd]))
        gid = by_champs.get(champs)
        if not gid:
            lines.append(f"{tag}: NOT IN FILE (yet)")
            continue
        tt, gp = t[t.gameid == gid], pl[pl.gameid == gid]
        issues = []
        for sd in ("blue", "red"):
            for r in g["pl"][sd]:
                x = gp[gp.champion == r[2]].iloc[0]
                if names.get(str(x.playername).lower(), x.playername).lower() != r[1].lower():
                    issues.append(f"{r[2]} player {r[1]} vs file {x.playername}")
                if (int(x.kills), int(x.deaths), int(x.assists)) != tuple(r[3:6]):
                    issues.append(f"{r[1]} K/D/A {r[3]}/{r[4]}/{r[5]} vs file {int(x.kills)}/{int(x.deaths)}/{int(x.assists)}")
                if fix and pd.notna(x.csdiffat15) and r[7] is None:
                    r[7] = int(x.csdiffat15); changed += 1
        L = int(tt.gamelength.iloc[0]); fl = f"{L // 60}:{L % 60:02d}"
        if fl != g["len"]:
            issues.append(f"length {g['len']} vs file {fl}")
            if fix:
                g["len"] = fl; g.pop("lenEst", None); changed += 1
        side = {"blue": "Blue", "red": "Red"}
        fb = {sd: [tt[tt.side == S].iloc[0][f"ban{k}"] for k in range(1, 6)] for sd, S in side.items()}
        if g.get("bans") is None:
            issues.append("bans missing")
            if fix:
                g["bans"] = fb; changed += 1
        else:
            for sd in side:
                if sorted(map(str, fb[sd])) != sorted(g["bans"][sd]):
                    issues.append(f"bans {sd} {g['bans'][sd]} vs file {fb[sd]}")
        fo = {sd: [int(tt[tt.side == S].iloc[0][c]) for c in ("dragons", "barons", "heralds", "void_grubs", "towers")] for sd, S in side.items()}
        if g.get("obj") and any(g["obj"].get(sd) != fo[sd] for sd in side):
            issues.append(f"objectives {g['obj']} vs file {fo}")
            if fix:
                g["obj"] = fo; changed += 1
        lines.append(f"{tag}: " + ("OK" if not issues else "; ".join(issues)))
    return lines, changed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv")
    ap.add_argument("--fix", action="store_true", help="correct js/worlds-live.js from the file")
    a = ap.parse_args()
    csv = find_csv(a.csv)
    df = pd.read_csv(csv, low_memory=False)
    print(f"File: {os.path.basename(csv)} · {df.gameid.nunique()} games · {str(df.date.min())[:10]} to {str(df.date.max())[:10]}")
    names = app_player_names()

    asof, pairs = build_h2h(df)
    print(f"js/h2h.js: {pairs} team pairs, data to {asof}")

    src, games, (i, j) = load_live()
    pin, tag, n = build_playin(df, names)
    src = write_playin(src, pin, tag)
    print(f"worlds-live.js play-in tables: {n} games, {len(pin)} players")

    lines, changed = check_live(df, games, names, a.fix)
    i = src.index("games:[") + len("games:"); j = src.index("]};", i) + 1
    src = src[:i] + json.dumps(games, separators=(",", ":"), ensure_ascii=False) + src[j:]
    open(P("js", "worlds-live.js"), "w", encoding="utf-8").write(src)
    report = [f"Oracle's Elixir check of js/worlds-live.js · {date.today()} · {os.path.basename(csv)}", ""] + lines
    open(P("research", "model", "oe_check.txt"), "w", encoding="utf-8").write("\n".join(report) + "\n")
    bad = [l for l in lines if not l.endswith(": OK")]
    print(f"Checked {len(lines)} Worlds Swiss games: {len(lines) - len(bad)} OK, {len(bad)} with notes (research/model/oe_check.txt)"
          + (f"; {changed} fields corrected" if a.fix else ""))
    for l in bad:
        print("  " + l)
    print("Remember to bump the ?v= cache version in index.html before committing.")


if __name__ == "__main__":
    main()
