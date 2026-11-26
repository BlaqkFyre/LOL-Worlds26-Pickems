"""Timing fixes step 1 (26 Nov 2026 AEST; Luke OK'd the plan: per-minute early fight count, real start seconds, real event gaps; gaps
under 60 s; a start-second table for each of minutes 0-4). Three fits for the app sim (js/sim-engine.js settings `opening` and `event_gap`):
  1. fights starting in a minute (Poisson): today's app model (research/sim3/s3_fighttypes.py "count_early": phase, gold lead size,
     monster up, buff up, draft pace, fight last minute, kills in the last 2 minutes, "early 0-4", "early 5-9"), with the single
     "early 0-4" term replaced by one term for each of minutes 0, 1, 2, 3 and 4. Same panel, same fit (ridge 1.0, as s3_fighttypes.py).
     The port is proven first: with the old terms it must give the app's count_early coefficients (to 4 dp) on the app's inputs.
  2. where in the minute a fight starts, minutes 0-4: 21 quantiles (0, 5, ..., 100%) of the start second of real fights (fights = kills
     20 s+ apart start a new one, as the fit) for each minute.
  3. gaps between consecutive events in a game, for events the sim places on its one clock: kill (the killing team), monster (dragon,
     Elder, Baron, Herald, and one event per team's void grub set, as the sim logs them), structure (tower, inhibitor, Nexus); plates are
     not events in the sim. Pairs by previous kind -> this kind and same / other team; kills of one fight (under 20 s apart) are left
     out (the sim draws those from the real kill gaps); only gaps under 60 s (the sim's minute step; Luke, 26 Nov). 21 quantiles each;
     a pair with fewer than 20 real gaps uses the same pair with both teams together (as the size tables' fallback). A fight's start
     (the sim draws it before it knows which side kills first) uses "-> kill, either team".
Splits: research copy fitted before config.SPLIT (1 Sep) with held-out Poisson deviance (games from 1 Sep, Worlds) against today's
count_early refitted on the same games; app copy fitted on every game before 10 Nov (the app's other tables' cut-off), written as one
block at the end of js/sim-tables.js (SIM_TABLES.timing, between markers; nothing else in that file is touched; re-running replaces it).
Inputs as the app's 13 Nov refit (research/local/sim3/refit_1110_v1fresh.zip run.sh): v1 games, draft pace from comp3_games.csv.
Output: research/model/memory/m12_fit_timing.json (+ the app block).
usage (repo root): python -I research/memory/m12_fit_timing.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import json, re
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run

OUT = config.MODEL_DIR / "memory"
APP_CUT = "2026-11-10"
L3 = config.R / "local" / "sim3"
INP = {"research": {"cut": config.SPLIT, "wf": False, "v1": config.R / "model" / "sim2" / "v1_games.csv", "comp": L3 / "out_11nov" / "comp3_games.csv"},
       "app": {"cut": APP_CUT, "wf": True, "v1": config.R / "local" / "sim1" / "v1_all" / "v1_games_all_fresh.csv",
               "comp": L3 / "refit_1110_v1fresh" / "fit" / "comp3_games.csv"}}
APP_COUNT_EARLY = config.ROOT / "research" / "local" / "sim4" / "app_params" / "fighttypes.json"   # the app's table (also in js/sim-tables.js)
SP = {"dragon": 300, "grub": 480, "herald": 900, "baron": 1200}
PH = [0, 14, 20, 25, 30, 35, 999]; PHN = ["0-13", "14-19", "20-24", "25-29", "30-34", "35+"]
NC = ["intercept", *[f"phase {p}" for p in PHN[1:]], "per_1k_abs_lead", "monster_up", "buff_up", "pace_style", "fight_last_minute", "log1p_kills_last_2min"]
QS = np.linspace(0, 1, 21)
MON = {"dragon", "baron", "herald", "grub"}; STR = {"tower", "inhib", "nexus"}
kind_of = lambda t: "kill" if t == "kill" else "monster" if t in MON else "structure"

def games(tm, inp):
    """the games and split of s3_fighttypes.py: games with a v1 strength, split by the cut-off (Worlds its own group)"""
    v1 = pd.read_csv(inp["v1"]).set_index("gameid"); M = tm[tm.gameid.map(v1.z_v1).notna()].drop_duplicates("gameid").copy()
    cut, wf = inp["cut"], inp["wf"]
    M["split"] = np.where(M.date < cut, "train", "test"); M.loc[M.tournament.str.startswith("Worlds") & ((M.date >= cut) | (not wf)), "split"] = "worlds"
    comp = pd.read_csv(inp["comp"]).set_index("gameid"); M["pace_s"] = M.gameid.map(comp.pace_blue + comp.pace_red).fillna(0)
    return M

def fight_starts(k):
    t = np.sort(k.t.values)
    return t[np.r_[True, np.diff(t) > 20]] if len(t) else t

def panel(M, ev, gold):
    """one row per game minute (as s3_fighttypes.py): fights starting in it and the count model's inputs; plus every fight's start"""
    GD = gold[gold.kind == "gold"].assign(sv=lambda d: d.value * np.where(d.side == "blue", 1, -1)).groupby(["gid", "minute"]).sv.sum().to_dict()
    E = {g: d.sort_values("t") for g, d in ev[ev.gid.isin(M.gid)].groupby("gid")}
    PAN, ST = [], []
    for gi in M.itertuples():
        g = gi.gid; e = E.get(g, ev.iloc[:0]); L = int(gi.len) // 60
        k = e[e.type == "kill"]; fs = fight_starts(k); kt = k.t.values
        ST += [(gi.split, float(s)) for s in fs]
        bar = e[e.type == "baron"]; eld = e[(e.type == "dragon") & (e.detail == "elder")]; drag = e[e.type == "dragon"]; up = []
        nxt = SP["dragon"]; soul = {"blue": 0, "red": 0}; elder_mode = False
        for r in drag.itertuples():
            up.append(("elder" if r.detail == "elder" else "dragon", nxt, r.t))
            if r.detail != "elder": soul[r.side] += 1
            if max(soul.values()) >= 4: elder_mode = True
            nxt = r.t + (360 if elder_mode else 300)
        up.append(("elder" if elder_mode else "dragon", nxt, None))
        nb = SP["baron"]
        for r in bar.itertuples(): up.append(("baron", nb, r.t)); nb = r.t + 360
        up.append(("baron", nb, None))
        for m in range(L + 1):
            t0, t1 = 60 * m, 60 * m + 60
            gd = GD.get((g, m), np.nan)
            mon_up = int(any(s_ <= t0 and (tk is None or tk >= t0) for kk, s_, tk in up if kk in ("dragon", "baron", "elder")))
            buff = int(((bar.t <= t0) & (bar.t > t0 - 180)).any() or ((eld.t <= t0) & (eld.t > t0 - 150)).any())
            f_prev = int(((fs >= t0 - 60) & (fs < t0)).any()) if len(fs) else 0
            k_prev2 = int(((kt >= t0 - 120) & (kt < t0)).sum())
            nf = int(((fs >= t0) & (fs < t1)).sum()) if len(fs) else 0
            PAN.append((g, m, gi.split, gd, nf, mon_up, buff, gi.pace_s, f_prev, k_prev2))
    PAN = pd.DataFrame(PAN, columns=["gid", "m", "split", "gd", "y", "mon_up", "buff", "pace_s", "f_prev", "k_prev2"]).dropna()
    return PAN, pd.DataFrame(ST, columns=["split", "t"])

def dummies(m): return np.c_[tuple((np.searchsorted(PH, m, side="right") - 1 == i).astype(float) for i in range(1, 6))]
def pois_fit(X, y, l2=1.0, it=60):   # as s3_fighttypes.py (the app's count tables were fitted with it)
    b = np.zeros(X.shape[1]); b[0] = np.log(max(y.mean(), 1e-3))
    for _ in range(it):
        mu = np.exp(X @ b); H = X.T @ (X * mu[:, None]) + l2 * np.eye(len(b)); b += np.linalg.solve(H, X.T @ (y - mu) - l2 * b)
    return b
pdev = lambda mu, y: float(np.mean(mu - y * np.log(np.maximum(mu, 1e-9))))   # the score s3_fighttypes.py reports (lower = better)
X1 = lambda d: np.c_[np.ones(len(d)), dummies(d.m.values), (d.gd.abs() / 1000).clip(0, 15), d.mon_up, d.buff, d.pace_s, d.f_prev, np.log1p(d.k_prev2)]
EW = lambda d: np.c_[(d.m.values < 5), (d.m.values >= 5) & (d.m.values < 10)].astype(float)
MW = lambda d: np.c_[tuple((d.m.values == i) for i in range(5)) + ((d.m.values >= 5) & (d.m.values < 10),)].astype(float)
N_OLD = NC + ["early 0-4", "early 5-9"]; N_NEW = NC + [f"minute {i}" for i in range(5)] + ["early 5-9"]

def count_fits(PAN):
    tr = PAN[PAN.split == "train"]
    bo = pois_fit(np.c_[X1(tr), EW(tr)], tr.y.values); bn = pois_fit(np.c_[X1(tr), MW(tr)], tr.y.values)
    out = {"old": dict(zip(N_OLD, np.round(bo, 4).tolist())), "new": dict(zip(N_NEW, np.round(bn, 4).tolist())), "minutes": {}, "score": {}}
    for s in ("train", "test", "worlds"):
        d = PAN[PAN.split == s]
        if not len(d): continue
        mo, mn = np.exp(np.c_[X1(d), EW(d)] @ bo), np.exp(np.c_[X1(d), MW(d)] @ bn)
        out["score"][s] = {"games": int(d.gid.nunique()), "minutes": int(len(d)), "today's count_early": round(pdev(mo, d.y.values), 5), "minute terms": round(pdev(mn, d.y.values), 5),
                           "minutes 0-4 only": {"today's count_early": round(pdev(mo[d.m < 5], d.y.values[d.m < 5]), 5), "minute terms": round(pdev(mn[d.m < 5], d.y.values[d.m < 5]), 5)}}
        ng = d.gid.nunique()
        out["minutes"][s] = {f"minute {i}": {"real": round(float(d.y[d.m == i].sum() / ng), 3), "today's count_early": round(float(mo[d.m.values == i].sum() / ng), 3),
                                             "minute terms": round(float(mn[d.m.values == i].sum() / ng), 3)} for i in range(6)}
    return out

def start_seconds(ST, splits_):
    x = ST[ST.split.isin(splits_)]; out = {}
    for i in range(5):
        s = x.t[(x.t >= 60 * i) & (x.t < 60 * i + 60)] - 60 * i
        out[str(i)] = {"fights": int(len(s)), "q": [round(float(v), 1) for v in np.quantile(s, QS)] if len(s) else None}
    return out

def event_gaps(ev, gids):
    """consecutive events on one clock: (previous kind, this kind, same / other team) -> real gaps under 60 s"""
    E = ev[ev.gid.isin(gids) & ev.type.isin(MON | STR | {"kill"})].sort_values(["gid", "t"]); rows = []
    for g, d in E.groupby("gid"):
        ty, t, sd = d.type.values, d.t.values.astype(float), d.side.values
        keep = np.ones(len(d), bool); lastgrub = {}
        for i in range(len(d)):   # one event per team's grub set (the sim logs the set once)
            if ty[i] == "grub":
                if sd[i] in lastgrub and t[i] - lastgrub[sd[i]] < 60: keep[i] = False
                lastgrub[sd[i]] = t[i]
        ty, t, sd = ty[keep], t[keep], sd[keep]
        for i in range(1, len(ty)):
            gap = t[i] - t[i - 1]
            if gap >= 60: continue
            a, b = kind_of(ty[i - 1]), kind_of(ty[i])
            if a == "kill" and b == "kill" and gap <= 20: continue   # the same fight: the sim uses the real kill gaps
            rows.append((a, b, "same" if sd[i] == sd[i - 1] else "other", gap))
    return pd.DataFrame(rows, columns=["a", "b", "team", "gap"])

def gap_tables(G):
    out, info = {}, {}
    for a in ("kill", "monster", "structure"):
        for b in ("kill", "monster", "structure"):
            both = G[(G.a == a) & (G.b == b)]
            for tm_ in ("same", "other", "any"):
                x = both if tm_ == "any" else both[both.team == tm_]; key = f"{a}>{b}|{tm_}"; src = key
                if len(x) < 20 and tm_ != "any": x = both; src = f"{a}>{b}|any (fewer than 20 {tm_}-team gaps)"
                if len(x) < 20: info[key] = {"pairs": int(len(x)), "table": None, "note": "fewer than 20 gaps with both teams"}; continue
                out[key] = [round(float(v), 1) for v in np.quantile(x.gap, QS)]
                info[key] = {"pairs": int(len(x)), "from": src, "within 1 s": round(float((x.gap <= 1).mean()), 3), "median s": round(float(x.gap.median()), 1)}
    return out, info

with Run("memory_timing_fit", params={"app_cut": APP_CUT, "split": config.SPLIT, "gap_under_s": 60, "fallback_pairs": 20, "ridge": 1.0},
         inputs=[config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD] + [p for c in INP.values() for p in (c["v1"], c["comp"])] + [APP_COUNT_EARLY]) as run:
    tm, ev, gold = data.timelines()
    R = {}
    for name, inp in INP.items():
        M = games(tm, inp); PAN, ST = panel(M, ev, gold); C = count_fits(PAN)
        tr_g = set(M.gid[M.split == "train"])
        G = event_gaps(ev, tr_g); gt, gi = gap_tables(G)
        R[name] = {"games": {s: int((M.split == s).sum()) for s in ("train", "test", "worlds")}, "count": C,
                   "start seconds (training games)": start_seconds(ST, ["train"]), "gaps (training games)": gi, "_gap_tables": gt}
        if name == "research":
            R[name]["start seconds (games from 1 Sep and Worlds)"] = start_seconds(ST, ["test", "worlds"])
            Gt = event_gaps(ev, set(M.gid[M.split != "train"])); R[name]["gaps (games from 1 Sep and Worlds)"] = gap_tables(Gt)[1]
    # the port check: the old terms on the app's inputs give the app's count_early
    app_ce = json.load(open(APP_COUNT_EARLY))["count_early"]["coef"]
    diff = max(abs(app_ce[k] - R["app"]["count"]["old"][k]) for k in N_OLD)
    R["port check: app count_early refitted v the app's table (largest gap)"] = diff
    if diff > 1e-4: raise RuntimeError(f"port check failed: the refit of today's count_early differs from the app's table by {diff}")
    for s, v in R["research"]["count"]["score"].items():
        run.result(f"research {s} deviance today v minute terms", [v["today's count_early"], v["minute terms"]])
    run.result("port check largest gap", diff)
    A = R["app"]
    TT = {"cutoff": APP_CUT, "source": f"research/memory/m12_fit_timing.py, gol.gg timelines before {APP_CUT} ({A['games']['train']} games)",
          "count_early": A["count"]["new"], "start_q": {k: v["q"] for k, v in A["start seconds (training games)"].items()}, "gap_q": A["_gap_tables"]}
    JS = config.ROOT / "js" / "sim-tables.js"
    START, END = "/* timing tables: BUILT BY research/memory/m12_fit_timing.py, never edit by hand */", "/* end timing tables */"
    block = f"{START}\nwindow.SIM_TABLES.timing = {json.dumps(TT, separators=(',', ':'))};\n{END}\n"
    js = JS.read_text(encoding="utf-8"); js = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", js, flags=re.S).rstrip("\n") + "\n" + block
    tmp = JS.with_suffix(".tmp"); tmp.write_text(js, encoding="utf-8"); tmp.replace(JS)
    for c in R.values():
        if isinstance(c, dict): c.pop("_gap_tables", None)
    R["app tables"] = TT
    run.save_json(OUT / "m12_fit_timing.json", R)
    print(json.dumps({k: R[k] for k in ("research",)}, indent=1)[:12000])
    print("port check", diff)
