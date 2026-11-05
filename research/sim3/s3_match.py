"""Sim session 3, step 2 (read-only): match gol.gg timeline games to the Oracle's Elixir file and check them.
Match: the champions seen on each side (all but at most 2 must fit, 6+ in all) and a date within 1 day. Only matched games are used (the file stays the
source of record; every game counted once by its file game id). Check per matched game: team kills, towers, dragons,
barons, winner and length from the timeline v the file.
usage: python -I s3_match.py <OE csv> tl_games.csv tl_events.csv <out_dir>"""
import os, sys, json
import numpy as np
import pandas as pd

CSV, TG, TE, OUT = sys.argv[1:5]; os.makedirs(OUT, exist_ok=True)
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
cols = ["gameid", "league", "date", "side", "position", "champion", "teamname", "result", "gamelength",
        "teamkills", "towers", "dragons", "barons", "void_grubs", "heralds", "inhibitors", "turretplates", "elders", "atakhans"]
oe = pd.read_csv(CSV, low_memory=False, usecols=cols)
oe = oe[~((oe.league == "WLDs") & (oe.date < "2026-10-01"))]
pl = oe[oe.position != "team"].copy(); pl["k"] = pl.champion.map(key)
sig = pl.groupby(["gameid", "side"]).k.apply(lambda s: "|".join(sorted(s))).unstack()
sig = sig.dropna(); sig["sig"] = sig.Blue + "/" + sig.Red
day = oe.groupby("gameid").date.first().str[:10]
lookup = {}
for gid, s in sig.sig.items(): lookup.setdefault(s, []).append(gid)

tg = pd.read_csv(TG, dtype={"gid": str}); ev = pd.read_csv(TE, dtype={"gid": str})
champs = ev[ev.type == "kill"]  # actor + victim champions per side (only shows champions that took part in kills)
# champion lists per side: from the timeline page's gold rows we don't get names, so use every champion seen on each side
seen = {}
for r in ev.itertuples():
    if isinstance(r.champ, str) and r.champ: seen.setdefault((r.gid, r.side), set()).add(key(r.champ))
    if r.type == "kill" and isinstance(r.victim_champ, str):
        seen.setdefault((r.gid, "red" if r.side == "blue" else "blue"), set()).add(key(r.victim_champ))
    if isinstance(r.assists, str):
        for a in r.assists.split("|"): seen.setdefault((r.gid, r.side), set()).add(key(a))
rows = []
for g in tg.itertuples():
    b, rd = seen.get((g.gid, "blue"), set()), seen.get((g.gid, "red"), set())
    # best file game within 1 day by champions in common; up to 2 names may not fit (e.g. a stolen ultimate shown as
    # another champion), and the runner-up must fit clearly worse
    cands = []
    for s, gids in lookup.items():
        bs, rs = set(s.split("/")[0].split("|")), set(s.split("/")[1].split("|"))
        hit = len(b & bs) + len(rd & rs)
        if hit >= 6 and hit >= len(b) + len(rd) - 2:
            for oid in gids:
                if abs((pd.Timestamp(day[oid]) - pd.Timestamp(g.date)).days) <= 1: cands.append((hit, oid))
    cands.sort(reverse=True)
    best = None if not cands else cands[0][1] if len(cands) == 1 or cands[1][0] < cands[0][0] - 2 else "AMBIGUOUS"
    rows.append(dict(gid=g.gid, gameid=best, n_champs_seen=len(b) + len(rd), n_fit=cands[0][0] if cands else 0))
M = pd.DataFrame(rows)
M = M.merge(tg, on="gid")
ok = M.gameid.notna() & (M.gameid != "AMBIGUOUS")
team = oe[oe.position == "team"].set_index(["gameid", "side"])
cnt = ev.groupby(["gid", "side", "type"]).size().unstack(fill_value=0)
chk = []
for r in M[ok].itertuples():
    for side, S in [("blue", "Blue"), ("red", "Red")]:
        t = team.loc[(r.gameid, S)]
        c = cnt.loc[(r.gid, side)] if (r.gid, side) in cnt.index else pd.Series(dtype=int)
        chk.append(dict(gid=r.gid, gameid=r.gameid, side=side,
                        kills=(int(c.get("kill", 0)), int(t.teamkills)), towers=(int(c.get("tower", 0)), int(t.towers)),
                        dragons=(int(c.get("dragon", 0)), int(t.dragons)), barons=(int(c.get("baron", 0)), int(t.barons)),
                        grubs=(int(c.get("grub", 0)), int(t.void_grubs) if pd.notna(t.void_grubs) else -1),
                        heralds=(int(c.get("herald", 0)), int(t.heralds) if pd.notna(t.heralds) else -1),
                        inhibs=(int(c.get("inhib", 0)), int(t.inhibitors)),
                        win=(int(r.win == side), int(t.result)), length=(int(r.len), int(t.gamelength))))
C = pd.DataFrame(chk)
summ = {"timeline games": len(M), "matched": int(ok.sum()), "unmatched": int(M.gameid.isna().sum()),
        "ambiguous": int((M.gameid == "AMBIGUOUS").sum())}
for f in ["kills", "towers", "dragons", "barons", "grubs", "heralds", "inhibs", "win"]:
    summ[f + " same"] = round(float(np.mean([a == b for a, b in C[f]])), 4)
    summ[f + " off by 1+"] = int(sum(abs(a - b) >= 1 for a, b in C[f]))
summ["length within 5 s"] = round(float(np.mean([abs(a - b) <= 5 for a, b in C["length"]])), 4)
summ["dup file ids"] = int(M[ok].gameid.duplicated().sum())
M[["gid", "gameid", "tournament", "date", "game", "patch", "blue", "red", "win", "len", "n_champs_seen", "n_fit"]].to_csv(os.path.join(OUT, "tl_match.csv"), index=False)
C.to_csv(os.path.join(OUT, "tl_check.csv"), index=False)
json.dump(summ, open(os.path.join(OUT, "tl_check.json"), "w"), indent=1)
print(json.dumps(summ, indent=1))
bad = C[[a != b for a, b in C.kills]]
print(bad.head(10).to_string())
