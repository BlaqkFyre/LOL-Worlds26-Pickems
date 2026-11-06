"""Sim session 3, step 7 (research only): calibrate the game-state sim on training games, then test it on held-out games.
A. fight_eps  per-fight swing, chosen so fights of 2-6 kills are two-sided as often as in training timelines
              (analytic: 1 - E[p^n + (1-p)^n] over training fights)
B. On training games (before 1 Sep, sample): gain (v1 strength -> every event chance) so the sim's win chance moves with
   v1's log-odds at slope 1; lane_k / lane_mu so the sim's lane gold leads at 15 have the real spread and real link to v1.
   These only scale strength and lane noise; no outcome is set.
C. Held-out: every game from 1 Sep and every Worlds game, N sims each (seeded). Who-wins: log loss, Brier, favourite,
   calibration bands, v1 and coin flip side by side. Game shape: length, kills, towers, dragons, Barons, grubs, Heralds,
   Elders, first-Baron / first-dragon / first-tower / Elder team win rates, role kill share, gold lead at 15, against the
   file's real games in the same window (targets3.json).
usage: python -I s3_test.py params3.json lanes3_features.csv v1_games.csv targets3.json tl_fights.csv comp3_games.csv <out_dir> [n_sims] [side|timing] [phase,zphase,lt]
  The final sim: n_sims 200, "timing". "phase" switches on the per-phase fight swing (tested 5 Nov, not kept; report 7d)."""
import os, sys, json, math, importlib.util
from multiprocessing import Pool
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PJ, FE, V1, TJ, FI, CO, OUT = sys.argv[1:8]; NS = int(sys.argv[8]) if len(sys.argv) > 8 else 200
MODE = sys.argv[9] if len(sys.argv) > 9 else "side"  # draft styles: "side" (who) or "timing" (when only)
OPTS = set(sys.argv[10].split(",")) if len(sys.argv) > 10 else set()  # opt-in variants: "phase" (per-phase fight swing, 7d), "zphase"
                                                                      # (strength in kills by phase, 7e), "lt" (lane x tier push terms, 7e)
PHASE_EPS = "phase" in OPTS
os.makedirs(OUT, exist_ok=True)
ROLES = ["top", "jng", "mid", "bot", "sup"]
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(HERE, "s3_sim.py")); simmod = importlib.util.module_from_spec(spec); spec.loader.exec_module(simmod)
P = json.load(open(PJ))
sig = lambda x: 1 / (1 + np.exp(-x))

def prep():  # runs in the main process only (workers on Windows re-import this file)
    global G, res, cal
    # inputs per game
    fe = pd.read_csv(FE)
    G = {}
    for gid, d in fe.groupby("gameid"):
        d = d.set_index("position").reindex(ROLES)
        if d.z_v1.isna().any(): continue
        G[gid] = {"z": float(d.z_v1.iloc[0]), "skill_gap": d.skill_gap.fillna(0).tolist(), "cg15": d.cg15.fillna(0).tolist(),
                  "day": d.day.iloc[0], "league": d.league.iloc[0], "gd15": d.gd15.tolist()}
    v1 = pd.read_csv(V1).set_index("gameid"); comp = pd.read_csv(CO).set_index("gameid")
    for g in G:
        c = comp.loc[g] if g in comp.index else None
        G[g].update({"siege_d": float(c.siege_blue - c.siege_red) if c is not None else 0.0, "obj_d": float(c.objectives_blue - c.objectives_red) if c is not None else 0.0,
                     "skirm_d": float(c.skirmish_blue - c.skirmish_red) if c is not None else 0.0, "pace_s": float(c.pace_blue + c.pace_red) if c is not None else 0.0,
                     "siege_s": float(c.siege_blue + c.siege_red) if c is not None else 0.0, "obj_s": float(c.objectives_blue + c.objectives_red) if c is not None else 0.0})
    for g in G: G[g]["y"] = int(v1.blue_win.get(g, -1)); G[g]["p_v1"] = float(v1.p_v1.get(g, np.nan))

    # ---------- A. per-fight swing ----------
    F = pd.read_csv(FI); F = F[(F.split == "train") & (F.n >= 2)].dropna(subset=["gd", "z"])
    ks = P["kill_side"]
    # the draft skirmish term (early fights only, about 0 on average) is left out of this check
    xb = ks["intercept"] + ks["per_1k_gold_lead"] * F.gd / 1000 + ks["per_v1_logit"] * F.z + ks["baron"] * F.baron + ks["elder"] * F.elder
    rs = np.random.default_rng(0).standard_normal(400)
    def fit_eps(FF, xbb):
        real2 = ((FF.blue > 0) & (FF.red > 0)).groupby(FF.n.clip(upper=6)).mean(); cnt = FF.groupby(FF.n.clip(upper=6)).size()
        def two_sided(eps):
            out = {}
            for n in real2.index:
                sel = (FF.n.clip(upper=6) == n).values
                x = xbb[sel].values[:, None] + eps * rs[None, :]
                p = sig(x); nn = FF.n[sel].values[:, None]
                out[n] = float(np.mean(1 - p ** nn - (1 - p) ** nn))
            return out
        best = min(np.arange(0, 3.01, 0.05), key=lambda e: sum(cnt[n] * (two_sided(e)[n] - real2[n]) ** 2 for n in real2.index))
        return round(float(best), 2), {"real_two_sided": real2.round(3).to_dict(), "sim_two_sided": {k: round(v, 3) for k, v in two_sided(best).items()}, "fights": int(len(FF))}
    best, info_all = fit_eps(F, xb)
    # by game phase: early fights are trades (two-sided like coin flips), late teamfights one-sided (5 Nov check)
    PHF = {"0-13": F.m < 14, "14-24": (F.m >= 14) & (F.m < 25), "25+": F.m >= 25}
    eps_ph = {}; info_ph = {}
    for k_, msk in PHF.items(): eps_ph[k_], info_ph[k_] = fit_eps(F[msk], xb[msk])
    cal = {"gain": 1.0, "lane_mu": 1.0, "lane_k": 1.0, "fight_eps": best, "style_mode": MODE, "form": "off"}
    if PHASE_EPS: cal["fight_eps_phase"] = eps_ph
    if "zphase" in OPTS: cal["kill_z_phase"] = {"0-13": 1.24, "14-24": 1.48, "25+": 1.26}  # matched to real training games at the final gain (7e)
    if "lt" in OPTS: cal["seg_lane_tier"] = "on"
    res = {"fight_eps": {"value": best, **info_all, "by_phase": {k_: {"value": eps_ph[k_], **info_ph[k_]} for k_ in eps_ph}}}
    print("fight_eps", res["fight_eps"], flush=True)


# ---------- simulation workers ----------
_sim = None
def init(cal_):
    global _sim; _sim = simmod.Sim(P, cal_)
def play(args):
    gid, x, seeds = args; out = []
    for s in seeds:
        g = _sim.run(x, seed=s)
        out.append((gid, g["winner"] == "blue", g["sec"], g["kills"][0] + g["kills"][1], g["towers"][0] + g["towers"][1],
                    len(g["dr"][0]) + len(g["dr"][1]), g["ba"][0] + g["ba"][1], g["grubs"][0] + g["grubs"][1], g["heralds"][0] + g["heralds"][1],
                    g["elders"][0] + g["elders"][1], g["first"].get("baron", ""), g["first"].get("dragon", ""), g["first"].get("tower", ""),
                    g["first"].get("elder", ""), g["g15"], *g["roles15"], *[g["ps"][sd][r]["k"] for sd in ("blue", "red") for r in ROLES],
                    g["capped"], int(len(g["dr"][0]) >= 4 or len(g["dr"][1]) >= 4),
                    g["first_t"].get("dragon", -1), g["first_t"].get("baron", -1), g["first_t"].get("tower", -1), g["roles5"][1] + g["roles5"][3] + g["roles5"][4],
                    g["first"].get("grub", ""), g["first"].get("herald", "")))
    return out
COLS = ["gid", "blue_win", "sec", "kills", "towers", "dragons", "barons", "grubs", "heralds", "elders", "fb", "fd", "ft", "fe", "g15",
        *[f"r15_{r}" for r in ROLES], *[f"k_{sd}_{r}" for sd in ("b", "r") for r in ROLES], "capped", "soul", "fd_t", "fb_t", "ft_t", "prio5", "fg", "fh"]
def run_many(gids, n, cal_, seed0=0):
    jobs = [(g, {k: G[g][k] for k in ("z", "skill_gap", "cg15", "siege_d", "obj_d", "skirm_d", "pace_s", "siege_s", "obj_s")}, [seed0 + 1000 * i + j for j in range(n)]) for i, g in enumerate(gids)]
    with Pool(3, initializer=init, initargs=(cal_,)) as pool:
        rows = [r for chunk in pool.imap(play, jobs, chunksize=4) for r in chunk]
    return pd.DataFrame(rows, columns=COLS)

def logit_slope(z, y):
    b = np.zeros(2); X = np.c_[np.ones(len(z)), z]
    for _ in range(30):
        p = sig(X @ b); H = X.T @ (X * (p * (1 - p))[:, None]) + 1e-6 * np.eye(2); b += np.linalg.solve(H, X.T @ (y - p))
    return b

if __name__ == "__main__":
    prep()
    train = sorted(g for g in G if G[g]["day"] < "2026-09-01" and G[g]["y"] >= 0)
    rng = np.random.default_rng(7); tr = list(rng.choice(train, size=min(300, len(train)), replace=False))
    real_tr = pd.DataFrame({g: G[g]["gd15"] for g in tr}, index=ROLES).T
    real_sd = real_tr.std(); real_team_sd = float(real_tr.sum(axis=1).std()); zt = np.array([G[g]["z"] for g in tr])
    real_slope = float(np.polyfit(zt, real_tr.sum(axis=1), 1)[0])
    hist = []
    for it in range(8):
        S = run_many(tr, 24, cal, seed0=10_000_000 * (it + 1))
        S["z"] = S.gid.map(lambda g: G[g]["z"])
        b = logit_slope(S.z.values, S.blue_win.values.astype(float))
        sim_sd = S[[f"r15_{r}" for r in ROLES]].std().values
        sim_slope = float(np.polyfit(S.z, S[[f"r15_{r}" for r in ROLES]].sum(axis=1), 1)[0])
        hist.append({"iter": it, **cal, "win_slope_on_v1": round(float(b[1]), 3), "win_intercept": round(float(b[0]), 3),
                     "gd15_sd_sim": [round(v) for v in sim_sd], "gd15_sd_real": [round(v) for v in real_sd.values],
                     "gd15_per_v1_sim": round(sim_slope), "gd15_per_v1_real": round(real_slope),
                     "team_gd15_sd_sim": round(float(S[[f"r15_{r}" for r in ROLES]].sum(axis=1).std())), "team_gd15_sd_real": round(real_team_sd)})
        print(hist[-1], flush=True)
        if it == 7: break
        cal["gain"] = round(cal["gain"] / max(0.3, b[1]) ** 0.8, 3)
        # lane noise scaled so the TEAM gold lead at 15 has the real spread (the five lanes move together more in the sim)
        sim_team_sd = float(S[[f"r15_{r}" for r in ROLES]].sum(axis=1).std())
        ratio = (real_team_sd / sim_team_sd) ** 2; cal["lane_k"] = round(max(0.02, cal["lane_k"] * ratio), 3)
        cal["lane_mu"] = round(max(0.0, cal["lane_mu"] * (real_slope / sim_slope if sim_slope > 0 else 1) ** 0.9), 3)
    res["calibration"] = hist; res["cal"] = cal
    # ---------- C. held-out ----------
    test = sorted(g for g in G if G[g]["day"] >= "2026-09-01" and G[g]["y"] >= 0)
    S = run_many(test, NS, cal, seed0=1)
    S.to_csv(os.path.join(OUT, "sim3_heldout_games.csv.gz"), index=False, compression="gzip")
    ps = S.groupby("gid").blue_win.mean().clip(0.5 / NS, 1 - 0.5 / NS)
    T = json.load(open(TJ))
    def who(gids):
        y = np.array([G[g]["y"] for g in gids]); p = ps.loc[gids].values; pv = np.array([G[g]["p_v1"] for g in gids])
        f = lambda q: {"logloss": round(float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q))), 4), "brier": round(float(np.mean((q - y) ** 2)), 4),
                       "fav": round(float(np.mean((q > 0.5) == (y == 1))), 3)}
        bands = pd.cut(p, np.arange(0, 1.01, 0.1)); cb = pd.DataFrame({"p": p, "y": y}).groupby(bands, observed=True).agg(n=("y", "size"), said=("p", "mean"), won=("y", "mean")).round(3)
        return {"n": len(gids), "sim": f(p), "v1": f(pv), "coin": f(np.full(len(y), 0.5)), "mean_abs_gap_to_v1": round(float(np.mean(np.abs(p - pv))), 4),
                "corr_with_v1": round(float(np.corrcoef(p, pv)[0, 1]), 3), "bands": {str(k): v for k, v in cb.to_dict("index").items()}}
    TIM = json.load(open(os.path.join(os.path.dirname(TJ), "timing3.json")))
    def shape(d, real, tim):
        q = lambda s: {"mean": round(float(s.mean()), 2), "sd": round(float(s.std()), 2)}
        bw = d.blue_win
        tw = lambda col: round(float(np.mean(np.where(d[col] == "blue", bw, np.where(d[col] == "red", ~bw, np.nan))[d[col] != ""])), 3)
        k = d[[c for c in d.columns if c.startswith("k_")]].sum()
        share = {r: round(float((k[f"k_b_{r}"] + k[f"k_r_{r}"]) / k.sum()), 4) for r in ROLES}
        g15 = d.g15.abs()
        sim = {"length_min": q(d.sec / 60), "kills_total": q(d.kills), "towers_total": q(d.towers), "dragons_total": q(d.dragons),
               "barons_total": q(d.barons), "grubs_total": q(d.grubs), "heralds_total": q(d.heralds), "elders_total": q(d.elders),
               "blue_win": round(float(bw.mean()), 3), "first_baron_team_wins": tw("fb"), "first_dragon_team_wins": tw("fd"),
               "first_tower_team_wins": tw("ft"), "elder_team_wins": tw("fe"), "role_kill_share": share,
               "gold_lead_15_abs": {"median": round(float(g15.median())), "sd": round(float(g15.std()))},
               "lead_15_team_wins": round(float(np.mean((d.g15 > 0) == bw)), 3), "capped_share": round(float(d.capped.mean()), 4),
               "soul_games": round(float(d.soul.mean()), 3)}
        # timing, against the gol.gg timelines in the same window (timing3.json, from s3_timing.py)
        wt = d.fd_t[d.fd_t > 0] - 300; lead = d.prio5.abs() > 150
        sim["timing"] = {"first_dragon_wait_s": {"within 30": round(float((wt < 30).mean()), 3), "30-90": round(float(((wt >= 30) & (wt < 90)).mean()), 3),
                                                 "90-180": round(float(((wt >= 90) & (wt < 180)).mean()), 3), "180+": round(float((wt >= 180).mean()), 3), "median": int(wt.median())},
                         "first_dragon_blue_share": round(float((d.fd == "blue").mean()), 3),
                         "first_tower_s": {"median": int(d.ft_t[d.ft_t > 0].median()), "p10": int(d.ft_t[d.ft_t > 0].quantile(.1)), "p90": int(d.ft_t[d.ft_t > 0].quantile(.9))},
                         "first_dragon_to_bot_jungle_leader_at_5": round(float(((d.prio5 > 0) == (d.fd == "blue"))[lead & (d.fd != "")].mean()), 3),
                         "grubs_and_first_dragon_split": round(float((d.fg != d.fd)[(d.fg != "") & (d.fd != "")].mean()), 3),
                         "herald_taken": round(float((d.fh != "").mean()), 3), "herald_to_grubs_team": round(float((d.fh == d.fg)[(d.fh != "") & (d.fg != "")].mean()), 3),
                         "first_baron_s": {"median": int(d.fb_t[d.fb_t > 0].median()), "p10": int(d.fb_t[d.fb_t > 0].quantile(.1)), "p90": int(d.fb_t[d.fb_t > 0].quantile(.9)),
                                           "games_with_baron": round(float((d.fb_t > 0).mean()), 3)}}
        rl = {"length_min": real["length_min"], "kills_total": real["kills_total"], "towers_total": real["towers_total"],
              "dragons_total": real["dragons_total"], "barons_total": real["barons_total"], "grubs_total": real["grubs_total"],
              "heralds_total": real["heralds_total"], "elders_total": real["elders_total"], "blue_win": real["blue_win"],
              "first_baron_team_wins": real["first_baron_team_wins"], "first_dragon_team_wins": real["first_dragon_team_wins"],
              "first_tower_team_wins": real["first_tower_team_wins"], "role_kill_share": real["role_kill_share"],
              "gold_lead_15_abs": {"median": real["gold_lead_15"]["median"], "sd": real["gold_lead_15"]["sd"]},
              "lead_15_team_wins": real["lead_15_team_wins"], "soul_games": real["soul_games"],
              "timing": {"first_tower_s": tim.get("first_tower_s"), **{k: tim.get(k) for k in ["first_dragon_wait_s", "first_dragon_blue_share", "first_dragon_to_bot_jungle_leader_at_5",
                                                 "grubs_and_first_dragon_split", "herald_taken", "herald_to_grubs_team", "first_baron_s"]}}}
        return {"sim": sim, "real": rl}
    wg = [g for g in test if G[g]["league"] == "WLDs"]; sg = [g for g in test]
    res["who_wins"] = {"from 1 Sep": who(sg), "Worlds": who(wg)}
    res["shape"] = {"from 1 Sep": shape(S, T["from 1 Sep"], TIM["from 1 Sep"]), "Worlds": shape(S[S.gid.isin(wg)], T["Worlds"], TIM["Worlds"])}
    res["n_sims_per_game"] = NS
    json.dump(res, open(os.path.join(OUT, "test3_results.json"), "w"), indent=1, default=float)
    print(json.dumps({k: res[k] for k in ["cal", "who_wins", "shape"]}, indent=1, default=float))
