"""Laning slice, step 4 tests (14 Nov 2026 AEST): the research sim with the laning module v without it, against real Worlds games, day by
day (each Worlds game played with the tables fitted only on games before its day; s5_fit_laning.py). Seeds by game ID.
Both versions: the default sim (fight types, lane-level, first-dragon taker, fight players, early counts, event order, push fights) with
death timers, calibration as research/local/sim4/spread/w_dt (gain 1.604).
Real (Oracle's Elixir file, gol.gg timelines): each role's gold edge at 10 and 15, the team's at 15, kills before 14:00 by role and the first
blood time, plates before 14:00 by lane, first tower time and lane, first dragon side and time, grubs, who won.
Measures: spread (sd) of each role's edge at 10 / 15; how well the sim's average edge per game lines up with the real one (correlation);
the team edge at 15 and its link to team strength; early kills by role; first blood; plates by lane; first tower; first dragon; grubs;
who-wins log loss.
usage (repo root): python -I research/laning/s5_laning_check.py [sims per game=200] [both | module | current]   (writes research/model/laning/laning_check[_N].json)"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data, simsetup, fit
from lib.runlog import Run
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
OUT = config.MODEL_DIR / "laning" / ("laning_check.json" if N == 200 else f"laning_check_{N}.json")
with Run("laning_check", params={"sims_per_game": N}, inputs=[config.OE_CSV, config.TL_MATCH, config.TL_EVENTS, config.R / "sim3" / "s3_sim.py", config.R / "local" / "laning" / "inputs.json"]) as run:
    o = data.oe(["gameid", "league", "date", "side", "position", "golddiffat10", "golddiffat15", "result", "firstdragon", "void_grubs"]); data.check(o)
    W = o[o.league == "WLDs"]; IN = json.load(open(config.R / "local" / "laning" / "inputs.json")); XS = simsetup.inputs()
    games = [g for g in IN if g in XS]
    sim = simsetup.sim_module(); P0 = simsetup.params({"typed", "ll", "fdt", "fpl", "dt"}); cal0 = simsetup.cal_default(); cal1 = dict(cal0, laning="actions")
    tm, ev, _ = data.timelines(); g2 = dict(zip(tm.gameid, tm.gid)); look = data.roles(data.oe(["gameid", "league", "date", "side", "position", "champion"]))
    # real
    real = {}
    for g in games:
        Bl = W[(W.gameid == g) & (W.side == "Blue")].set_index("position"); e = ev[ev.gid == g2[g]] if g in g2 else ev.iloc[:0]
        k = e[(e.type == "kill") & (e.t < 840)]; roles_k = [look.get((g, data.key(c)), ("?",))[0] for c in k.champ]
        pl = e[(e.type == "plate") & (e.t < 840)]; tw = e[e.type == "tower"].sort_values("t"); dr = e[e.type == "dragon"].sort_values("t")
        real[g] = {"r10": [Bl.loc[r].golddiffat10 for r in config.ROLES], "r15": [Bl.loc[r].golddiffat15 for r in config.ROLES], "g15": float(Bl.loc[config.ROLES].golddiffat15.sum()),
                   "blue_win": float(Bl.loc["top"].result), "kills14": len(k), "kill_roles": roles_k, "fb_t": float(k.t.min()) if len(k) else np.nan,
                   "plates": {L: int((pl.detail == L).sum()) for L in ("TOP", "MID", "BOT")}, "ft_t": float(tw.t.iloc[0]) if len(tw) else np.nan,
                   "ft_lane": str(tw.detail.iloc[0]).split()[1] if len(tw) else "", "fd_blue": float(dr.side.iloc[0] == "blue") if len(dr) else np.nan,
                   "fd_t": float(dr.t.iloc[0]) if len(dr) else np.nan, "grubs_blue": np.nan}
    T = W[W.position == "team"].set_index(["gameid", "side"]).void_grubs
    for g in games: real[g]["grubs_blue"] = float(T.get((g, "Blue"), np.nan))
    # sims
    def play(cal, la):
        out = {}
        for g in games:
            P = dict(P0); x = dict(XS[g])
            if la: P["laning"] = json.load(open(config.R / "local" / "laning" / "params" / f"laning_{IN[g]['day']}.json")); x["la"] = IN[g]
            S = sim.Sim(P, cal); rows = []
            for j in range(N):
                r = S.run(x, simsetup.seed(g, j), log=True); st = r["steps"]
                ks = [e for e in st if e["kind"] == "kill" and e["t"] < 840]
                tws = [e for e in st if e["kind"] == "tower"]; drs = [e for e in st if e["kind"] == "dragon"]
                rows.append({"win": r["winner"] == "blue", "r10": r["roles10"], "r15": r["roles15"], "g15": r["g15"], "kills14": len(ks),
                             "kill_roles": [e["text"].split(" kills ")[0] for e in ks], "fb_t": ks[0]["t"] if ks else np.nan,
                             "ft_t": tws[0]["t"] if tws else np.nan, "ft_lane": tws[0]["text"].split()[-1] if tws else "",
                             "fd_blue": float(drs[0]["side"] == "blue") if drs else np.nan, "fd_t": drs[0]["t"] if drs else np.nan, "grubs_blue": r["grubs"][0]})
            out[g] = rows
            print(".", end="", flush=True)
        print(flush=True); return out
    import pickle
    CACHE = config.R / "local" / "laning" / f"check_sims_{N}.pkl"
    VERSION = sys.argv[2] if len(sys.argv) > 2 else "both"  # "module" re-runs only the module (the current sim's games are kept from the cache)
    sims = pickle.load(open(CACHE, "rb")) if CACHE.exists() else {}
    if VERSION in ("both", "current") or "current sim (with death timers)" not in sims: sims["current sim (with death timers)"] = play(cal0, False)
    if VERSION in ("both", "module") or "laning module" not in sims: sims["laning module"] = play(cal1, True)
    pickle.dump(sims, open(CACHE, "wb"))
    def summ(S_):
        R = {}
        R10 = np.array([[np.nanmean([r["r10"][i] for r in S_[g]]) for i in range(5)] for g in games]); R15 = np.array([[np.nanmean([r["r15"][i] for r in S_[g]]) for i in range(5)] for g in games])
        Q10 = np.array([real[g]["r10"] for g in games], float); Q15 = np.array([real[g]["r15"] for g in games], float)
        sd = lambda key, i: float(np.nanstd([r[key][i] for g in games for r in S_[g]]))
        R["role edge at 15: sd (sim)"] = {r: round(sd("r15", i)) for i, r in enumerate(config.ROLES)}
        R["role edge at 10: sd (sim)"] = {r: round(sd("r10", i)) for i, r in enumerate(config.ROLES)}
        R["role edge at 15: correlation of the sim's average with the real edge"] = {r: round(float(pd.Series(R15[:, i]).corr(pd.Series(Q15[:, i]))), 3) for i, r in enumerate(config.ROLES)}
        R["role edge at 10: correlation of the sim's average with the real edge"] = {r: round(float(pd.Series(R10[:, i]).corr(pd.Series(Q10[:, i]))), 3) for i, r in enumerate(config.ROLES)}
        gz = np.array([XS[g]["z"] for g in games]); G = np.array([[r["g15"] for r in S_[g]] for g in games]); ok = ~np.isnan(G.ravel())
        R["team edge at 15: sd, and per unit of v1 strength"] = [round(float(np.nanstd(G))), round(float(np.polyfit(np.repeat(gz, N)[ok], G.ravel()[ok], 1)[0]))]
        R["kills before 14:00 per game"] = round(float(np.mean([r["kills14"] for g in games for r in S_[g]])), 2)
        kr = pd.Series([k for g in games for r in S_[g] for k in r["kill_roles"]]).value_counts(normalize=True)
        R["early kills by killer role"] = {r: round(float(kr.get(r, 0)), 3) for r in config.ROLES}
        R["first blood time (median s)"] = float(np.nanmedian([r["fb_t"] for g in games for r in S_[g]]))
        R["first tower time (median s)"] = float(np.nanmedian([r["ft_t"] for g in games for r in S_[g]]))
        fl = pd.Series([r["ft_lane"] for g in games for r in S_[g]]).value_counts(normalize=True); R["first tower lane"] = {L: round(float(fl.get(L, 0)), 3) for L in ("TOP", "MID", "BOT")}
        R["first dragon: blue share, median time (s)"] = [round(float(np.nanmean([r["fd_blue"] for g in games for r in S_[g]])), 3), float(np.nanmedian([r["fd_t"] for g in games for r in S_[g]]))]
        R["grubs taken by blue (mean of 3)"] = round(float(np.mean([r["grubs_blue"] for g in games for r in S_[g]])), 2)
        p = np.array([np.mean([r["win"] for r in S_[g]]) for g in games]); y = np.array([real[g]["blue_win"] for g in games])
        R["who wins: log loss"] = round(fit.log_loss(y, np.clip(p, 0.02, 0.98)), 4)
        return R
    rq = lambda key: [real[g][key] for g in games]
    RealS = {"role edge at 15: sd": {r: round(float(np.nanstd([real[g]["r15"][i] for g in games]))) for i, r in enumerate(config.ROLES)},
             "role edge at 10: sd": {r: round(float(np.nanstd([real[g]["r10"][i] for g in games]))) for i, r in enumerate(config.ROLES)},
             "team edge at 15: sd, and per unit of v1 strength": [round(float(np.std(rq("g15")))), round(float(np.polyfit([XS[g]["z"] for g in games], rq("g15"), 1)[0]))],
             "kills before 14:00 per game": round(float(np.mean(rq("kills14"))), 2),
             "early kills by killer role": {r: round(float(v), 3) for r, v in pd.Series([k for g in games for k in real[g]["kill_roles"]]).value_counts(normalize=True).reindex(config.ROLES).fillna(0).items()},
             "first blood time (median s)": float(np.nanmedian(rq("fb_t"))), "first tower time (median s)": float(np.nanmedian(rq("ft_t"))),
             "first tower lane": {L: round(float(v), 3) for L, v in pd.Series(rq("ft_lane")).value_counts(normalize=True).reindex(["TOP", "MID", "BOT"]).fillna(0).items()},
             "first dragon: blue share, median time (s)": [round(float(np.nanmean(rq("fd_blue"))), 3), float(np.nanmedian(rq("fd_t")))],
             "grubs taken by blue (mean of 3)": round(float(np.nanmean(rq("grubs_blue"))), 2),
             "plates before 14:00 per game by lane": {L: round(float(np.mean([real[g]["plates"][L] for g in games])), 2) for L in ("TOP", "MID", "BOT")}}
    R = {"games": len(games), "sims per game": N, "real Worlds": RealS}
    for k_, S_ in sims.items(): R[k_] = summ(S_); print(k_, json.dumps(R[k_]), flush=True)
    run.result("who wins: current / module", [R["current sim (with death timers)"]["who wins: log loss"], R["laning module"]["who wins: log loss"]])
    run.save_json(OUT, R); print(json.dumps(R["real Worlds"]))
