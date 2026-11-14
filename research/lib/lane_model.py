"""The step 1 lane-edge model (moved here from research/laning/s5_lane_edges.py on 14 Nov 2026 so every script shares one copy).
  lane_rows(minor=False)  one row per game x role, blue player's side: players (pb, pr), champions (cb, cr), earlier games on the champion
                          (nb, nr), gold edges y10 / y15, CS edges c10 / c15, the current sim's inputs (z_v1, skill_gap, cg15), day, ts (days), league, major
  Model(blocks, k, hl)    per role: intercept + player + champion + matchup + comfort + player x champion (+ team strength), shrunk
  Current()               the current sim's lane inputs, fitted linearly per role
  pregame_preds(target)   the model's pre-game expected edge for every game x role, never fitted on that game (cross-fitted before
                          config.SPLIT, fitted before SPLIT for 2026 games after it, fitted on every earlier day for Worlds); cached"""
import json
import numpy as np, pandas as pd
from . import config, data
from .runlog import sha256
ROLES = config.ROLES

def lane_rows(minor=False):
    o = data.oe(["gameid", "league", "date", "patch", "side", "position", "playerid", "playername", "champion", "golddiffat10", "golddiffat15", "csdiffat10", "csdiffat15"])
    o = o[o.position.isin(ROLES)].copy()
    o["pid"] = o.playerid.fillna("name:" + o.playername.astype(str)); o["day"] = o.date.str[:10]
    o["major"] = o.league.isin(config.MAJOR); o = o[o.major | (minor & (o.patch == config.WORLDS_PATCH))]
    # comfort: the player's games on that champion (any role, every row in the file, the qualifier included) before this game's day
    allg = data.oe(["gameid", "date", "position", "playerid", "playername", "champion"], raw=True)
    allg = allg[allg.position.isin(ROLES)].copy(); allg["pid"] = allg.playerid.fillna("name:" + allg.playername.astype(str)); allg["day"] = allg.date.str[:10]
    cnt = allg.groupby(["pid", "champion", "day"]).size().rename("n").reset_index().sort_values("day")
    cnt["before"] = cnt.groupby(["pid", "champion"]).n.cumsum() - cnt.n
    o = o.merge(cnt[["pid", "champion", "day", "before"]], on=["pid", "champion", "day"], how="left")
    b, r = o[o.side == "Blue"].set_index(["gameid", "position"]), o[o.side == "Red"].set_index(["gameid", "position"])
    J = b.join(r[["pid", "champion", "before", "golddiffat15"]], rsuffix="_r", how="inner").reset_index()
    J = J.dropna(subset=["golddiffat15"]).rename(columns={"pid": "pb", "pid_r": "pr", "champion": "cb", "champion_r": "cr", "before": "nb", "before_r": "nr"})
    J["y15"], J["y10"] = J.golddiffat15, J.golddiffat10
    J["c15"], J["c10"] = J.csdiffat15, J.csdiffat10  # CS edges (added 14 Nov for the farm contest)
    J["ts"] = pd.to_datetime(J.day).astype("int64") // 86_400_000_000_000
    data.fingerprint(config.LANE_FEATURES)
    feat = pd.read_csv(config.LANE_FEATURES); J = J.merge(feat[["gameid", "position", "z_v1", "skill_gap", "cg15"]], on=["gameid", "position"], how="left")
    names = o.groupby("pid").playername.agg(lambda s: s.value_counts().index[0]).to_dict()
    return J, cnt, names

def ids(a, c):  # shared index for two columns
    u = pd.Index(pd.unique(pd.concat([a, c])));
    return u.get_indexer(a), u.get_indexer(c), len(u)

class Model:
    """per role fit; blocks: player, champ, pair, comfort, pc. k_* shrink; hl_p / hl_c half-lives (days, None = no fade)"""
    def __init__(s, blocks, k, hl): s.blocks, s.k, s.hl = blocks, k, hl
    def fit(s, D, t_ref, rounds=25):
        s.par = {}
        for role in ROLES:
            d = D[D.position == role]; y = d.y.values
            age = t_ref - d.ts.values
            wp = 0.5 ** (age / s.hl["p"]) if s.hl["p"] else np.ones(len(d)); wc = 0.5 ** (age / s.hl["c"]) if s.hl["c"] else np.ones(len(d))
            E = {}
            if "player" in s.blocks: E["player"] = (*ids(d.pb, d.pr), wp, s.k["player"], pd.Index(pd.unique(pd.concat([d.pb, d.pr]))))
            if "champ" in s.blocks: E["champ"] = (*ids(d.cb, d.cr), wc, s.k["champ"], pd.Index(pd.unique(pd.concat([d.cb, d.cr]))))
            if "pc" in s.blocks:
                a, c = d.pb + "|" + d.cb, d.pr + "|" + d.cr; E["pc"] = (*ids(a, c), wp, s.k["pc"], pd.Index(pd.unique(pd.concat([a, c]))))
            if "pair" in s.blocks:
                key = np.where(d.cb < d.cr, d.cb + "|" + d.cr, d.cr + "|" + d.cb); sg = np.where(d.cb < d.cr, 1.0, -1.0)
                ux = pd.Index(pd.unique(key)); E["pair"] = (ux.get_indexer(key), sg, len(ux), wc, s.k["pair"], ux)
            x_cf = (np.log1p(d.nb.fillna(0).values) - np.log1p(d.nr.fillna(0).values)) if "comfort" in s.blocks else None
            x_tm = d.z_v1.fillna(0).values if "team" in s.blocks else None
            eff = {n: np.zeros(e[2]) for n, e in E.items()}; a0 = 0.0; cf = 0.0; ct = 0.0
            def pred():
                p = np.full(len(d), a0)
                for n, e in E.items():
                    if n == "pair": p += e[1] * eff[n][e[0]]
                    else: p += eff[n][e[0]] - eff[n][e[1]]
                return p + (cf * x_cf if x_cf is not None else 0) + (ct * x_tm if x_tm is not None else 0)
            for _ in range(rounds):
                a0 += np.average(y - pred(), weights=wp)
                for n, e in E.items():
                    res = y - pred()
                    if n == "pair":
                        ix, sg, m, w, k, _ = e; num = np.bincount(ix, w * sg * res, m); den = np.bincount(ix, w, m)
                        eff[n] = (num + eff[n] * den) / (den + k)
                    else:
                        ib, ir, m, w, k, _ = e; num = np.bincount(ib, w * res, m) - np.bincount(ir, w * res, m)
                        den = np.bincount(ib, w, m) + np.bincount(ir, w, m)
                        eff[n] = eff[n] + 0.5 * ((num + eff[n] * den) / (den + k) - eff[n])  # half step: two entities per row
                if x_cf is not None:
                    res = y - pred() + cf * x_cf; cf = float(np.sum(wp * x_cf * res) / max(1e-9, np.sum(wp * x_cf ** 2)))
                if x_tm is not None:
                    res = y - pred() + ct * x_tm; ct = float(np.sum(wp * x_tm * res) / max(1e-9, np.sum(wp * x_tm ** 2)))
            s.par[role] = {"a": a0, "cf": cf, "ct": ct, "eff": {n: dict(zip(E[n][-1], eff[n])) for n in E}}
        return s
    def predict(s, D):
        out = np.zeros(len(D))
        for role in ROLES:
            m = (D.position == role).values; d = D[m]; P = s.par[role]; p = np.full(len(d), P["a"])
            for n, ef in P["eff"].items():
                if n == "player": p += d.pb.map(ef).fillna(0).values - d.pr.map(ef).fillna(0).values
                elif n == "champ": p += d.cb.map(ef).fillna(0).values - d.cr.map(ef).fillna(0).values
                elif n == "pc": p += (d.pb + "|" + d.cb).map(ef).fillna(0).values - (d.pr + "|" + d.cr).map(ef).fillna(0).values
                elif n == "pair":
                    key = np.where(d.cb < d.cr, d.cb + "|" + d.cr, d.cr + "|" + d.cb); sg = np.where(d.cb < d.cr, 1.0, -1.0)
                    p += sg * pd.Series(key).map(ef).fillna(0).values
            if P["cf"]: p += P["cf"] * (np.log1p(d.nb.fillna(0).values) - np.log1p(d.nr.fillna(0).values))
            if P["ct"]: p += P["ct"] * d.z_v1.fillna(0).values
            out[m] = p
        return out

class Current:  # the app's lane inputs, fitted linearly per role on the same training games
    def fit(s, D, t_ref):
        s.b = {}
        for role in ROLES:
            d = D[(D.position == role)].dropna(subset=["skill_gap", "cg15", "z_v1"]); X = np.c_[np.ones(len(d)), d.skill_gap, d.cg15, d.z_v1]
            s.b[role] = np.linalg.lstsq(X, d.y.values, rcond=None)[0]
        return s
    def predict(s, D):
        out = np.zeros(len(D))
        for role in ROLES:
            m = (D.position == role).values; d = D[m]; X = np.c_[np.ones(len(d)), d.skill_gap.fillna(0), d.cg15.fillna(0), d.z_v1.fillna(0)]
            out[m] = X @ s.b[role]
        return out


def day0(d): return int(pd.Timestamp(d).value // 86_400_000_000_000)
FULL = ["player", "champ", "pair", "comfort", "pc"]

def pregame_preds(target="y10", settings=None):
    """pre-game expected edge per (gameid, position), blue minus red, never fitted on the game itself. settings = {"k", "half_life_days"}
    (default: the latest saved lane_edges result). Cached in research/local/cache by the file's SHA-256 and the settings."""
    if settings is None:
        settings = json.load(open(config.MODEL_DIR / "laning" / "lane_edges.json"))[target]["chosen on training games (fit < 1 Aug, judge Aug)"]
    tag = f"{sha256(config.OE_CSV)[:12]}_{sha256(config.LANE_FEATURES)[:8]}_{target}_" + "_".join(f"{k}{v}" for k, v in sorted(settings["k"].items())) + f"_hl{settings['half_life_days']['p']}-{settings['half_life_days']['c']}"
    cache = config.CACHE_DIR / f"pregame_{tag}.parquet"
    if cache.exists(): return pd.read_parquet(cache)
    J, _, _ = lane_rows(); J["y"] = J[target]; D = J.dropna(subset=["y"]).copy(); K, HL = settings["k"], settings["half_life_days"]
    pred = pd.Series(np.nan, index=D.index); pre = D[D.day < config.SPLIT]
    gids = np.array(sorted(pre.gameid.unique())); fold = {g: i % 5 for i, g in enumerate(gids)}
    for f in range(5):
        te = pre[pre.gameid.map(fold) == f]; pred[te.index] = Model(FULL, K, HL).fit(pre[pre.gameid.map(fold) != f], day0(config.SPLIT)).predict(te)
    te = D[(D.day >= config.SPLIT) & (D.league != "WLDs")]; pred[te.index] = Model(FULL, K, HL).fit(pre, day0(config.SPLIT)).predict(te)
    for d in sorted(D[D.league == "WLDs"].day.unique()):
        te = D[(D.day == d) & (D.league == "WLDs")]; tr = D[D.day < d]
        assert tr.day.max() < d
        pred[te.index] = Model(FULL, K, HL).fit(tr, day0(d)).predict(te)
    out = D[["gameid", "position", "day", "league", "z_v1"]].assign(pred=pred.values)
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True); tmp = cache.with_suffix(".tmp"); out.to_parquet(tmp, index=False); tmp.replace(cache)
    return out
