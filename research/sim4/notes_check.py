"""Luke's game-flow notes (13 Nov 2026, photo in chat) against the real timelines, and later the sim.
The gol.gg timelines have kills (killer, assisters, victim), plates, towers, dragons (type), grubs, Herald, Baron, inhibitors and the
Nexus with times; no jungle camps, Scuttle crabs or positions, so notes about those can't be checked here.
Checks (real games; with --sim also the sim on port_ref.json games):
  1m  invade or not          kills before 1:30 (share of games), who takes part
  2m  lanes start 1v1/2v2    kills 1:30-3:00: same-lane share, jungle involved
  3m  first clear, gank      kills 2:45-4:30 with the jungler in them (killer, assister or victim); first kill time
  5m  support / mid roam     kills 4:00-8:00 in top or mid lane fights (top or mid laner involved) with the support or mid of the
                             other lanes taking part
  6m  first dragon           time of the first dragon, blue/red share
  7m  grubs (help plates)    time grubs are taken; plates in the 3 min after grubs v the 3 min before
  7-15m lanes, skirmishes    kills per game by window; jungle share
  12-20m tower pushes        first tower time; towers by 14:00 and 20:00
  22m Baron                  first Baron time, games with a Baron
  game length                short 22-28, average 28-35, long 35+ (and under 22)
usage (repo root): python -I research/sim4/notes_check.py <OE csv> tl_match.csv tl_events.csv tl_games.csv <out_json>"""
import sys, json
import numpy as np, pandas as pd
CSV, TMF, TEF, TGF, OUT = sys.argv[1:6]
ROLES = ["top", "jng", "mid", "bot", "sup"]; LANE = {"top": "top", "mid": "mid", "bot": "bot", "sup": "bot"}
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
raw = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "side", "position", "champion"]); pl = raw[raw.position.isin(ROLES)]
role_of = {(g, s.lower(), key(c)): p for g, s, c, p in zip(pl.gameid, pl.side, pl.champion, pl.position)}
lg = pl.drop_duplicates("gameid").set_index("gameid").league
tm = pd.read_csv(TMF, dtype={"gid": str}).dropna(subset=["gameid"]); tm = tm[tm.gameid != "AMBIGUOUS"].drop_duplicates("gameid")
tg = pd.read_csv(TGF, dtype={"gid": str}).set_index("gid")
ev = pd.read_csv(TEF, dtype={"gid": str}); ev = ev[ev.gid.isin(tm.gid)].merge(tm[["gid", "gameid"]], on="gid")
ev["league"] = ev.gameid.map(lg)

def kill_rows(d):
    out = []
    for e in d[d.type == "kill"].itertuples():
        o = "red" if e.side == "blue" else "blue"
        k = role_of.get((e.gameid, e.side, key(e.champ))); v = role_of.get((e.gameid, o, key(e.victim_champ)))
        a = [role_of.get((e.gameid, e.side, key(c))) for c in str(e.assists).split("|")] if isinstance(e.assists, str) and e.assists else []
        out.append((e.gameid, e.t, e.side, k, v, [x for x in a if x]))
    return pd.DataFrame(out, columns=["g", "t", "side", "k", "v", "a"])

def check(d, games):
    n = len(games); K = kill_rows(d); K = K[K.k.notna() & K.v.notna()]
    inv = lambda r: {r.k, r.v, *r.a}
    w = lambda a, b: K[(K.t >= a) & (K.t < b)]
    res = {"games": n}
    k1 = w(0, 90); res["1m invade: games with a kill before 1:30"] = round(k1.g.nunique() / n, 3)
    res["1m invade: kills before 1:30 per game"] = round(len(k1) / n, 3)
    k2 = w(90, 180)
    res["2m lanes: kills 1:30-3:00 per game"] = round(len(k2) / n, 3)
    if len(k2): res["2m lanes: same-lane share of those kills"] = round(float(np.mean([LANE.get(r.k) is not None and LANE.get(r.k) == LANE.get(r.v) for r in k2.itertuples()])), 3)
    k3 = w(165, 270)
    res["3m gank: kills 2:45-4:30 per game"] = round(len(k3) / n, 3)
    if len(k3): res["3m gank: share of those with the jungler in them"] = round(float(np.mean(["jng" in inv(r) for r in k3.itertuples()])), 3)
    fk = K.groupby("g").t.min()
    res["first kill time (min) p10 / median / p90"] = [round(float(fk.quantile(q)) / 60, 2) for q in (.1, .5, .9)]
    res["games with no kill before 5:00"] = round(1 - (fk < 300).sum() / n, 3)
    k5 = w(240, 480)
    if len(k5):
        roam = [((("top" in inv(r)) or ("mid" in inv(r))) and ("sup" in inv(r))) for r in k5.itertuples()]
        res["5m roam: kills 4:00-8:00 with a support and a top or mid laner in them"] = round(float(np.mean(roam)), 3)
        res["5m roam: games with such a kill"] = round(k5[roam].g.nunique() / n, 3)
    dr = d[d.type == "dragon"].groupby("gameid").t.min()
    first_side = d[d.type == "dragon"].sort_values("t").groupby("gameid").side.first()
    res["6m first dragon time (min) p10 / median / p90"] = [round(float(dr.quantile(q)) / 60, 2) for q in (.1, .5, .9)]
    res["6m first dragon: blue share"] = round(float((first_side == "blue").mean()), 3)
    gr = d[d.type == "grub"].groupby("gameid").t.min()
    res["7m grubs first taken (min) p10 / median / p90"] = [round(float(gr.quantile(q)) / 60, 2) for q in (.1, .5, .9)]
    pl_ = d[d.type == "plate"]; after = before = 0
    for g, t0 in gr.items():
        p = pl_[pl_.gameid == g].t; after += int(((p >= t0) & (p < t0 + 180)).sum()); before += int(((p >= t0 - 180) & (p < t0)).sum())
    res["7m grubs: plates in the 3 min after the grubs v the 3 min before"] = [after, before]
    he = d[d.type == "herald"].groupby("gameid").t.min()
    res["Herald taken (min) median, share of games"] = [round(float(he.median()) / 60, 2), round(len(he) / n, 3)]
    res["kills per game by window"] = {f"{a // 60}-{b // 60}": round(len(w(a, b)) / n, 2) for a, b in [(0, 300), (300, 420), (420, 900), (900, 1200), (1200, 1500), (1500, 1800), (1800, 2400), (2400, 4000)]}
    kj = w(420, 900); res["7-15m: share of kills with the jungler in them"] = round(float(np.mean(["jng" in inv(r) for r in kj.itertuples()])), 3) if len(kj) else None
    tw = d[d.type == "tower"]; ft = tw.groupby("gameid").t.min()
    res["first tower (min) p10 / median / p90"] = [round(float(ft.quantile(q)) / 60, 2) for q in (.1, .5, .9)]
    res["towers per game by 14:00 / 20:00 / 25:00"] = [round(float((tw.t < x).sum()) / n, 2) for x in (840, 1200, 1500)]
    ba = d[d.type == "baron"].groupby("gameid").t.min()
    res["first Baron (min) p10 / median / p90, share of games"] = [*[round(float(ba.quantile(q)) / 60, 2) for q in (.1, .5, .9)], round(len(ba) / n, 3)]
    ln = tg.loc[[x for x in tm.set_index("gameid").gid.reindex(games).dropna()], "len"] / 60
    res["game length bands: under 22 / 22-28 / 28-35 / 35+"] = [round(float(((ln >= a) & (ln < b)).mean()), 3) for a, b in [(0, 22), (22, 28), (28, 35), (35, 99)]]
    res["game length (min) median"] = round(float(ln.median()), 2)
    return res

games = ev.gameid.unique(); wg = [g for g in games if lg.get(g) == "WLDs"]
R = {"all timeline games": check(ev, games), "Worlds": check(ev[ev.gameid.isin(wg)], wg)}
json.dump(R, open(OUT, "w"), indent=1); print(json.dumps(R, indent=1))
