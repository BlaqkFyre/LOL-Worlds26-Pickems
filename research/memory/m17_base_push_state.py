"""Base push learns the game state, part A: the fit (27 Nov 2026 AEST; Luke OK'd research/memory/base-push-plan.md part A).
The app's per-minute base push (js/sim-engine.js, `base_push_fight` in js/sim-tables.js, fitted by research/sim3/s3_rates.py) keeps
every input; added, fitted on the same real team-minutes (a side with a lane open, gol.gg timelines):
  structures left   to the enemy Nexus at the minute's start: nexus towers standing (back 180 s after they fall) + 1 if no enemy
                    inhibitor is down (back after 300 s); 0-3. Tried as one slope and as 0 / 1 / 2 dummies (3 = base)
  enemies dead      the most enemy players dead at the same moment during the minute (0-5), and own dead the same; each death lasts the
                    official timer at the victim's level from their XP by minute in the Oracle's Elixir file (research/sim4/s4_deadpush.py)
  base under attack the enemy took one of this side's own base structures (inhibitor, nexus tower) in the minute before
  exposed x dead    (structures left = 0) x enemies dead, kept only if the training-half check supports it
The left form and the interaction are chosen on training games only (fit on the earlier half of the training dates, judge the later
half, as s3_rates.py chose its cut-off); held-out log loss (games from 1 Sep, Worlds) is reported for every version.
Also from real games: push sizes by structures left at the push's start (pushes = one side's base structures under 30 s apart, as
s3_rates.py), gaps between a side's consecutive structures when the later one is a base structure (by pair, under 60 s), and the Nexus
after a won fight's last kill by structures left at the fight's start (fights and pushes as m16_nexus_push.py).
Two copies, inputs as m12_fit_timing.py: research (fit before config.SPLIT, the fixed test's inputs) and app (every game before 10 Nov,
the app's other tables' cut-off, inputs of the 13 Nov refit). Port check first: the app copy's refit of today's inputs must give
`base_push_fight` in js/sim-tables.js exactly.
Output: research/model/memory/m17_base_push_state.json (with the app block). With --app the block is also written to the end of
js/sim-tables.js (SIM_TABLES.base, between markers; nothing else in that file is touched); part A runs without it.
usage (repo root): python -I research/memory/m17_base_push_state.py [--app]"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import json, re, runpy, contextlib, io
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run

OUT = config.MODEL_DIR / "memory"
APP_CUT = "2026-11-10"
L3 = config.R / "local" / "sim3"
INP = {"research": {"cut": None, "v1": config.R / "model" / "sim2" / "v1_games.csv", "comp": L3 / "out_11nov" / "comp3_games.csv"},
       "app": {"cut": APP_CUT, "v1": config.R / "local" / "sim1" / "v1_all" / "v1_games_all_fresh.csv",
               "comp": L3 / "refit_1110_v1fresh" / "fit" / "comp3_games.csv"}}
DTJ = config.R / "model" / "sim4" / "deathtimer.json"
RATES = config.R / "sim3" / "s3_rates.py"
WRITE_APP = "--app" in sys.argv[1:]
INHIB_BACK, NXT_BACK = 300, 180
QS5, Q21 = [.1, .25, .5, .75, .9], np.linspace(0, 1, 21)
qq = lambda a: [round(float(v), 1) for v in np.quantile(a, QS5)] if len(a) else None
q21 = lambda a: [round(float(v), 1) for v in np.quantile(a, Q21)]
STR = {"tower", "inhib", "nexus"}

def kind(ty, det):
    d = str(det)
    if ty == "nexus": return "nexus"
    if ty == "inhib": return "inhib"
    if "NEXUS" in d: return "nxt"
    if d.startswith("T3"): return "T3"
    return "outer"

def rates(copy):
    """run s3_rates.py (quietly, to a scratch folder) with one copy's inputs; returns its namespace"""
    inp = INP[copy]; tmp = config.R / "local" / "memory" / f"m17_rates_{copy}"; tmp.mkdir(parents=True, exist_ok=True)
    old_argv, old_env = sys.argv, os.environ.get("S3_CUTOFF")
    if inp["cut"]: os.environ["S3_CUTOFF"] = inp["cut"]
    else: os.environ.pop("S3_CUTOFF", None)
    sys.argv = ["s3_rates.py", str(config.TL_MATCH), str(config.TL_EVENTS), str(config.TL_GOLD), str(inp["v1"]), str(tmp), str(inp["comp"])]
    try:
        with contextlib.redirect_stdout(io.StringIO()): ns = runpy.run_path(str(RATES))
    finally:
        sys.argv = old_argv
        if old_env is None: os.environ.pop("S3_CUTOFF", None)
        else: os.environ["S3_CUTOFF"] = old_env
    ns["Xb"].__globals__["SC"] = "siege_s"   # the timing-only inputs (the app's); runpy hands back a copy, so set it where Xb looks
    return ns

def dead_intervals(info, ev, XP, AVG, DT):
    """each side's death intervals (victim's side): [kill time, kill time + official timer at the victim's level]"""
    def wait(c, t):
        xp = float(np.interp(t, [0, 600, 900, 1200, 1500], [0, *c])) if t <= 1500 else min(DT["xp_levels"][-1], c[3] + (c[3] - c[2]) / 300 * (t - 1500))
        lv = int(np.searchsorted(DT["xp_levels"], xp, side="right")); tf_ = DT["time_factor"]; f = 0.0; prev = tf_["start_s"]
        for end, per in tf_["per_step"]:
            if t > prev: f += per * ((min(t, end) - prev) // tf_["step_s"])
            prev = end
        return DT["base_wait"][min(17, lv - 1)] * (1 + min(tf_["cap"], f))
    D, matched = {}, [0, 0]
    K = ev[ev.type == "kill"]
    for g, k in K.groupby("gid"):
        if g not in info.index: continue
        gid = info.loc[g, "gameid"]; L = {"blue": [], "red": []}
        for t, sd, v in zip(k.t.values, k.side.values, k.victim.values):
            c = XP.get((gid, str(v).lower())); matched[1] += 1; matched[0] += c is not None
            L["red" if sd == "blue" else "blue"].append((float(t), float(t) + wait(c or AVG, float(t))))
        D[g] = L
    return D, matched

def max_dead(iv, a, b):
    """most intervals open at the same moment within [a, b) (as s4_deadpush.py)"""
    pts = sorted([(max(s, a), 1) for s, e in iv if s < b and e > a] + [(min(e, b), -1) for s, e in iv if s < b and e > a], key=lambda z: (z[0], z[1]))
    cur = best = 0
    for _, d in pts: cur += d; best = max(best, cur)
    return best

def structures(ev):
    """per game and side: (time, kind) of the structures that side took, in time order"""
    S = ev[ev.type.isin(STR)].sort_values("t")
    return {(g, sd): [(float(t), kind(ty, de)) for t, ty, de in zip(d.t, d.type, d.detail)] for (g, sd), d in S.groupby(["gid", "side"])}

def left_at(st, t):
    """structures left to the enemy Nexus at time t (strictly before t), from this side's takes"""
    inh = any(k == "inhib" and t - INHIB_BACK < x < t for x, k in st)
    nxd = min(2, sum(1 for x, k in st if k == "nxt" and t - NXT_BACK < x < t))
    return (2 - nxd) + (0 if inh else 1)

def add_state(B, ST, DEAD):
    left, en, ow, att = [], [], [], []
    for g, m, s in zip(B.gid, B.m, B.side):
        o = "red" if s == "blue" else "blue"; t0 = 60.0 * m
        left.append(left_at(ST.get((g, s), []), t0))
        dd = DEAD.get(g, {"blue": [], "red": []}); en.append(max_dead(dd[o], t0, t0 + 60)); ow.append(max_dead(dd[s], t0, t0 + 60))
        att.append(int(any(k in ("inhib", "nxt") and t0 - 60 <= x < t0 for x, k in ST.get((g, o), []))))
    return B.assign(left=left, en_dead=np.clip(en, 0, 5), own_dead=np.clip(ow, 0, 5), under_attack=att)

def fight_pushes(ev, gids):
    """won fights and the winner's push, with structures left at the fight's start (as m16_nexus_push.py)"""
    E = ev[ev.gid.isin(gids)].sort_values(["gid", "t"]); P = []
    for g, d in E.groupby("gid"):
        k = d[d.type == "kill"]; s = d[d.type.isin(STR)]
        if not len(k): continue
        sk = [(float(t), sd, kind(ty, de)) for t, sd, ty, de in zip(s.t, s.side, s.type, s.detail)]
        kt, ks = k.t.values.astype(float), k.side.values
        grp = np.cumsum(np.r_[True, np.diff(kt) > 20]); F = []
        for gi in np.unique(grp):
            m = grp == gi; nb, nr = int((ks[m] == "blue").sum()), int((ks[m] == "red").sum())
            F.append((kt[m].min(), kt[m].max(), "blue" if nb > nr else "red" if nr > nb else None))
        for i, (t0, t1, w) in enumerate(F):
            if w is None: continue
            pre = [(t, kd) for t, sd, kd in sk if sd == w and t < t0]
            if not any(kd == "T3" for t, kd in pre): continue   # lane closed at the fight's start
            end = min(F[i + 1][0] if i + 1 < len(F) else 1e9, t1 + 120)
            x = [(t, kd) for t, sd, kd in sk if sd == w and t0 <= t < end]
            P.append({"t1": t1, "left": left_at(pre, t0), "x": x})
    return P

def base_pushes(ev, gids, ST):
    """base pushes (one side's inhibitors, nexus towers, Nexus under 30 s apart, as s3_rates.py) with structures left at the start"""
    out = []
    for (g, sd), st in ST.items():
        if g not in gids: continue
        b = [(x, k) for x, k in st if k in ("inhib", "nxt", "nexus")]; i = 0
        while i < len(b):
            j = i
            while j + 1 < len(b) and b[j + 1][0] - b[j][0] <= 30: j += 1
            out.append({"left": left_at(st, b[i][0]), "size": j - i + 1, "nexus": any(k == "nexus" for x, k in b[i:j + 1])}); i = j + 1
    return pd.DataFrame(out)

def gap_pairs(ST, gids):
    """gaps between a side's consecutive structures when the later one is an inhibitor or nexus tower (under 60 s), by pair"""
    G = {}
    for (g, sd), st in ST.items():
        if g not in gids: continue
        for (a, ka), (b, kb) in zip(st, st[1:]):
            if kb in ("inhib", "nxt") and b - a < 60: G.setdefault(f"{ka}>{kb}", []).append(b - a)
    return G

def tables(ev, gids, ST):
    """the timing and size tables for one set of games"""
    BP = base_pushes(ev, gids, ST); G = gap_pairs(ST, gids); FP = fight_pushes(ev, gids)
    pooled = sum(G.values(), [])
    size = {}
    for L in (0, 1, 2, 3):
        d = BP[BP.left == L]
        vc = d["size"].clip(upper=6).value_counts(normalize=True).sort_index()
        size[str(L)] = {"sizes": [int(z) for z in vc.index], "p": [round(float(v), 4) for v in vc.values], "n": int(len(d)), "ends_in_nexus": round(float(d.nexus.mean()), 3) if len(d) else None}
    gaps = {k: q21(v) for k, v in G.items() if len(v) >= 20}
    nx = {}
    for L in (0, 1, 2, 3):
        a = [next(t for t, kd in p["x"] if kd == "nexus") - p["t1"] for p in FP if p["left"] == L and any(kd == "nexus" for t, kd in p["x"])]
        nx[str(L)] = a
    nexus_q = {L: q21(a) for L, a in nx.items() if len(a) >= 20}
    summ = {"push sizes by structures left (share, n, ends in the Nexus)": size,
            "base gaps s (10/25/50/75/90%), n": {k: [qq(v), len(v)] for k, v in sorted(G.items())}, "base gaps pooled": [qq(pooled), len(pooled)],
            "Nexus from the last kill by structures left at the fight's start s (10/25/50/75/90%), n": {L: [qq(a), len(a)] for L, a in nx.items()},
            "won fights by structures left (lane open)": {str(L): sum(1 for p in FP if p["left"] == L) for L in (0, 1, 2, 3)}}
    app = {"size_by_left": {L: [v["sizes"], v["p"]] for L, v in size.items() if v["n"] >= 30},
           "gap_q": gaps, "gap_pooled_q": q21(pooled), "nexus_q": nexus_q}
    return summ, app

lgl = lambda p, y: float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
def ll(X, b, y): return round(lgl(np.clip(1 / (1 + np.exp(-X @ b)), 1e-6, 1 - 1e-6), y), 5)

def extra(d, form, inter):
    c = [d.left.values.astype(float)] if form == "linear" else [(d.left.values == L).astype(float) for L in (0, 1, 2)]
    c += [d.en_dead.values, d.own_dead.values, d.under_attack.values]
    if inter: c.append((d.left.values == 0) * d.en_dead.values)
    return np.c_[tuple(np.asarray(x, float) for x in c)]

def names_extra(form, inter):
    return (["structures_left"] if form == "linear" else ["left 0", "left 1", "left 2"]) + ["enemies_dead_max", "own_dead_max", "own_base_under_attack"] + (["left 0 x enemies_dead"] if inter else [])

def fit_copy(ns, ST, DEAD, copy):
    logit_fit, Xb, fight_terms, cB = ns["logit_fit"], ns["Xb"], ns["fight_terms"], ns["res"]["base_push_fight"]["clear_fight_cutoff"]
    names0 = [n if n != "siege_style" else "siege_style_sum" for n in ns["names_b"]] + ["net_kills_last_minute"] + (["clear_fight_win"] if cB is not None else [])
    B = add_state(ns["BASE"], ST, DEAD); y = lambda d: (d.y.values > 0).astype(float)
    X0 = lambda d: np.c_[Xb(d), fight_terms(d, cB)]
    tr = B[B.split == "train"]; b0 = logit_fit(X0(tr), y(tr))
    port = {"refit of today's inputs": dict(zip(names0, np.round(b0, 4).tolist())), "s3_rates.py base_push_fight": {k: float(v) for k, v in ns["res"]["base_push_fight"]["coef"].items()}}
    # choices on training games only: earlier half of the training dates fits, later half judges
    early = (tr.gid.map(ns["info"].date) < ns["CUTD"]).values; E, Lt = tr[early], tr[~early]; ch = {}
    for form in ("linear", "dummies"):
        for inter in (False, True):
            X = lambda d: np.c_[X0(d), extra(d, form, inter)]
            ch[f"{form}{' + interaction' if inter else ''}"] = ll(X(Lt), logit_fit(X(E), y(E)), y(Lt))
    ch["today's inputs"] = ll(X0(Lt), logit_fit(X0(E), y(E)), y(Lt))
    form = "linear" if ch["linear"] <= ch["dummies"] else "dummies"
    inter = ch[f"{form} + interaction"] < ch[form]
    choice = {"split_date": ns["CUTD"], "n_fit": int(early.sum()), "n_check": int((~early).sum()), "later-half log loss": ch, "left form": form, "interaction kept": bool(inter)}
    # versions: one input group at a time, then all
    V = {"today's inputs": (X0, names0),
         "+ structures left": (lambda d: np.c_[X0(d), extra(d, form, False)[:, :1 if form == "linear" else 3]], names0 + names_extra(form, False)[:1 if form == "linear" else 3]),
         "+ dead": (lambda d: np.c_[X0(d), d.en_dead.values, d.own_dead.values], names0 + ["enemies_dead_max", "own_dead_max"]),
         "+ base under attack": (lambda d: np.c_[X0(d), d.under_attack.values], names0 + ["own_base_under_attack"]),
         "all (chosen)": (lambda d: np.c_[X0(d), extra(d, form, inter)], names0 + names_extra(form, inter))}
    R = {}
    for k, (X, nm) in V.items():
        b = logit_fit(X(tr), y(tr))
        R[k] = {"coef": dict(zip(nm, np.round(b, 4).tolist())), **{s: {"n": int((B.split == s).sum()), "logloss": ll(X(B[B.split == s]), b, y(B[B.split == s])) if (B.split == s).any() else None} for s in ("train", "test", "worlds")}}
    desc = {"push start share by structures left (train)": {str(L): [round(float(y(q).mean()), 3), len(q)] for L, q in tr.groupby("left")},
            "push start share by enemies dead (train)": {str(k): [round(float(y(q).mean()), 3), len(q)] for k, q in tr.groupby(tr.en_dead.clip(upper=4))},
            "push start share, 0 left, by enemies dead (train)": {str(k): [round(float(y(q).mean()), 3), len(q)] for k, q in tr[tr.left == 0].groupby(tr[tr.left == 0].en_dead.clip(upper=4))},
            "push start share by own base under attack (train)": {str(k): [round(float(y(q).mean()), 3), len(q)] for k, q in tr.groupby("under_attack")}}
    return {"port": port, "choice": choice, "versions": R, "descriptive": desc, "cutoff": cB, "form": form, "inter": bool(inter)}

def app_base_push_fight():
    js = (config.ROOT / "js" / "sim-tables.js").read_text(encoding="utf-8")
    m = re.search(r'"base_push_fight":\{"coef":(\{[^}]*\})', js); return json.loads(m.group(1))

with Run("memory_base_push_state", params={"app_cut": APP_CUT, "split": config.SPLIT, "inhib_back": INHIB_BACK, "nexus_tower_back": NXT_BACK, "ridge": 1.0, "write_app": WRITE_APP},
         inputs=[config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD, config.OE_CSV, DTJ, RATES, *[p for c in INP.values() for p in (c["v1"], c["comp"])]]) as run:
    tm, ev_all, _ = data.timelines()
    o = data.oe(["gameid", "league", "date", "playername", "xpat10", "xpat15", "xpat20", "xpat25"]).dropna()
    XP = {(g, str(p).lower()): (a, b, c, d) for g, p, a, b, c, d in zip(o.gameid, o.playername, o.xpat10, o.xpat15, o.xpat20, o.xpat25)}
    DT = json.load(open(DTJ)); AVG = tuple(np.mean([DT["role_xp"][r] for r in config.ROLES], axis=0))
    R = {"source": "research/memory/m17_base_push_state.py (27 Nov 2026 AEST)"}
    for copy in ("research", "app"):
        ns = rates(copy); info, ev = ns["info"], ns["ev"]
        ST = structures(ev); DEAD, matched = dead_intervals(info, ev, XP, AVG, DT)
        F = fit_copy(ns, ST, DEAD, copy); F["deaths matched to the file's XP"] = matched
        F["games by split"] = {k: int(v) for k, v in info.split.value_counts().items()}
        R[copy] = F
        if copy == "research":
            trg = set(info.index[info.split == "train"])
            R["tables, training games (before 1 Sep)"], _ = tables(ev, trg, ST)
            R["tables, all timelines"], _ = tables(ev, set(info.index), ST)
        else:
            appg = set(info.index[info.date < APP_CUT]); summ, APPT = tables(ev, appg, ST)
            R["tables, app games (before 10 Nov)"] = summ
    # port check: the app copy's refit of today's inputs against the table in the app
    inapp = app_base_push_fight(); ref = R["app"]["port"]["refit of today's inputs"]
    diff = {k: round(ref.get(k, float("nan")) - v, 4) for k, v in inapp.items()}
    R["port check"] = {"app copy refit v js/sim-tables.js base_push_fight (differences)": diff, "identical": all(abs(v) < 1e-9 for v in diff.values()) and set(ref) == set(inapp)}
    A = R["app"]; best = A["versions"]["all (chosen)"]
    block = {"cutoff": APP_CUT, "source": f"research/memory/m17_base_push_state.py, gol.gg timelines before {APP_CUT}",
             "coef": best["coef"], "clear_fight_cutoff": A["cutoff"], "left_form": A["form"], **APPT}
    R["app block"] = block
    if WRITE_APP:
        JS = config.ROOT / "js" / "sim-tables.js"
        START, END = "/* base push state tables: BUILT BY research/memory/m17_base_push_state.py, never edit by hand */", "/* end base push state tables */"
        txt = f"{START}\nwindow.SIM_TABLES.base = {json.dumps(block, separators=(',', ':'))};\n{END}\n"
        js = JS.read_text(encoding="utf-8"); js = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", js, flags=re.S).rstrip("\n") + "\n" + txt
        tmp = JS.with_suffix(".tmp"); tmp.write_text(js, encoding="utf-8"); tmp.replace(JS)
    run.result("port identical", R["port check"]["identical"])
    for s in ("test", "worlds"):
        run.result(f"research {s} log loss today / all", [R["research"]["versions"]["today's inputs"][s]["logloss"], R["research"]["versions"]["all (chosen)"][s]["logloss"]])
    run.save_json(OUT / "m17_base_push_state.json", R)
    print(json.dumps({k: R[k] for k in ("port check",)}, indent=1))
    print(json.dumps({c: {"choice": R[c]["choice"], "scores": {k: {s: v[s]["logloss"] for s in ("train", "test", "worlds")} for k, v in R[c]["versions"].items()}} for c in ("research", "app")}, indent=1))
