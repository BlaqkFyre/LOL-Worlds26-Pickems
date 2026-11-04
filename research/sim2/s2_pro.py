"""Sim session 2, step 5 (read-only): pro-only synergy and lane matchups, in the relevant patch window.
All values from earlier days only (no look-ahead), pulled toward 0 with k games:
  Synergy: teammate pairs (jng-top, jng-mid, jng-bot, jng-sup, bot-sup, mid-sup); value = mean win residual (result - v1 chance)
           of that champion pair on the same team. Game feature = blue pairs' sum - red pairs' sum.
  Lanes:   champion v champion in the same role (bot lane also as a duo: ADC+support v ADC+support); value = mean lane gold at 15
           left after the two players' laning skills (as step 4), both directions. Game feature = sum over lanes.
Windows: "meta" = only games on patches 16.15, 16.16, 16.17, 16.20 (the relevant ones); "season" = all games, 30-day half-life.
Tests: lane value v the later lane result (correlation), and win odds beyond v1. Train: meta-window games before 1 Sep;
test from 1 Sep and Worlds.
usage: python -I s2_pro.py <OE csv> v1_games.csv gfeat.csv <out_dir>"""
import json, os, sys
from collections import defaultdict
import numpy as np
import pandas as pd

CSV, V1, GF, OUT = sys.argv[1:5]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
META = {"16.15", "16.16", "16.17", "16.20"}
SKILL = {"top": "e_laning", "jng": "e_early", "mid": "e_laning", "bot": "e_lane_own"}
PAIRS = [("jng", "top"), ("jng", "mid"), ("jng", "bot"), ("jng", "sup"), ("bot", "sup"), ("mid", "sup")]
def np_(p):
    a, _, b = str(p).partition("."); return f"{a}.{b}0" if len(b) == 1 else f"{a}.{b.zfill(2)}"
df = pd.read_csv(CSV, low_memory=False, dtype={"patch": str},
                 usecols=["gameid", "league", "date", "patch", "side", "position", "champion", "golddiffat15", "result"])
df = df[df.league.isin(MAJOR) & (df.position != "team") & ~((df.league == "WLDs") & (df.date < "2026-10-01"))].copy()
df["patch"] = df.patch.map(np_); df["day"] = df.date.str[:10]
gf = pd.read_csv(GF)
gf["skill"] = [r[SKILL[r.position]] if r.position in SKILL else np.nan for _, r in gf.iterrows()]
df = df.merge(gf[["gameid", "side", "position", "skill"]], on=["gameid", "side", "position"], how="left")
V = pd.read_csv(V1).set_index("gameid"); pv = V.p_v1.to_dict()
# one record per game: champions and lane values per side
games = {}
for g, d in df.groupby("gameid"):
    x = {"day": d.day.iloc[0], "patch": d.patch.iloc[0], "league": d.league.iloc[0]}
    for r in d.itertuples(index=False):
        x[(r.side, r.position)] = (r.champion, r.golddiffat15, r.skill, r.result)
    games[g] = x
# lane residual: gold at 15 minus what the skill gap predicts (fitted before 1 Sep, per role)
slope = {}
for pos in ["top", "jng", "mid", "bot"]:
    xs, ys = [], []
    for g, x in games.items():
        b, r = x.get(("Blue", pos)), x.get(("Red", pos))
        if b and r and x["day"] < "2026-09-01" and not np.isnan(b[1]) and not np.isnan(b[2]) and not np.isnan(r[2]):
            xs.append(b[2] - r[2]); ys.append(b[1])
    slope[pos] = np.polyfit(xs, ys, 1)
def lane_res(x, pos):
    b, r = x.get(("Blue", pos)), x.get(("Red", pos))
    if not (b and r) or np.isnan(b[1]) or np.isnan(b[2]) or np.isnan(r[2]): return np.nan
    return b[1] - np.polyval(slope[pos], b[2] - r[2])
def duo_res(x):
    v = [x.get(("Blue", p)) for p in ("bot", "sup")]
    if not all(v) or any(np.isnan(t[1]) for t in v): return np.nan
    return v[0][1] + v[1][1]
order = sorted(games, key=lambda g: (games[g]["day"], g))
def run(window, k_syn, k_lane, hl=30.0):
    syn, lane, duo = defaultdict(lambda: [0.0, 0.0, 0]), defaultdict(lambda: [0.0, 0.0, 0]), defaultdict(lambda: [0.0, 0.0, 0])
    t0 = pd.Timestamp("2026-01-01")
    def val(acc, key, t, k):
        S, N, tl = acc[key] if key in acc else (0.0, 0.0, t)
        f = 1.0 if window == "meta" else 0.5 ** ((t - tl) / hl)
        return S * f / (N * f + k), N * f
    def add(acc, key, t, v):
        S, N, tl = acc[key] if key in acc else (0.0, 0.0, t)
        f = 1.0 if window == "meta" else 0.5 ** ((t - tl) / hl); acc[key] = [S * f + v, N * f + 1, t]
    rows = []; days = defaultdict(list)
    for g in order: days[games[g]["day"]].append(g)
    for d in sorted(days):
        t = (pd.Timestamp(d) - t0).days
        for g in days[d]:
            x = games[g]; use = window == "season" or x["patch"] in META
            f = {"gameid": g, "syn": 0.0, "lane": 0.0, "n_syn": 0.0, "n_lane": 0.0}
            if use:
                for side, sg in (("Blue", 1), ("Red", -1)):
                    for a, b in PAIRS:
                        ca, cb = x.get((side, a)), x.get((side, b))
                        if ca and cb:
                            v, n = val(syn, (a, ca[0], b, cb[0]), t, k_syn); f["syn"] += sg * v; f["n_syn"] += n
                for pos in ["top", "jng", "mid"]:
                    b_, r_ = x.get(("Blue", pos)), x.get(("Red", pos))
                    if b_ and r_:
                        v1_, n1 = val(lane, (pos, b_[0], r_[0]), t, k_lane); v2_, n2 = val(lane, (pos, r_[0], b_[0]), t, k_lane)
                        f["lane"] += (v1_ - v2_) / 2; f["n_lane"] += n1 + n2
                bb, bs, rb, rs = (x.get(("Blue", "bot")), x.get(("Blue", "sup")), x.get(("Red", "bot")), x.get(("Red", "sup")))
                if bb and bs and rb and rs:
                    v1_, n1 = val(duo, (bb[0], bs[0], rb[0], rs[0]), t, k_lane); v2_, n2 = val(duo, (rb[0], rs[0], bb[0], bs[0]), t, k_lane)
                    f["duo"] = (v1_ - v2_) / 2
                for pos in ["top", "jng", "mid"]:
                    b_, r_ = x.get(("Blue", pos)), x.get(("Red", pos))
                    if b_ and r_:
                        v1_, _ = val(lane, (pos, b_[0], r_[0]), t, k_lane); v2_, _ = val(lane, (pos, r_[0], b_[0]), t, k_lane)
                        f["lane_" + pos] = (v1_ - v2_) / 2; f["res_" + pos] = lane_res(x, pos)
                f["res_duo"] = duo_res(x)
            rows.append(f)
        for g in days[d]:   # update after the day
            x = games[g]
            if window == "meta" and x["patch"] not in META: continue
            p = pv.get(g)
            for side in ("Blue", "Red"):
                res = None
                if p is not None and not np.isnan(p):
                    win = x.get((side, "top"), (None, None, None, np.nan))[3]
                    res = win - (p if side == "Blue" else 1 - p)
                if res is not None and not np.isnan(res):
                    for a, b in PAIRS:
                        ca, cb = x.get((side, a)), x.get((side, b))
                        if ca and cb: add(syn, (a, ca[0], b, cb[0]), t, res)
            for pos in ["top", "jng", "mid"]:
                b_, r_ = x.get(("Blue", pos)), x.get(("Red", pos)); lr = lane_res(x, pos)
                if b_ and r_ and not np.isnan(lr):
                    add(lane, (pos, b_[0], r_[0]), t, lr); add(lane, (pos, r_[0], b_[0]), t, -lr)
            bb, bs, rb, rs = (x.get(("Blue", "bot")), x.get(("Blue", "sup")), x.get(("Red", "bot")), x.get(("Red", "sup")))
            dr = duo_res(x)
            if bb and bs and rb and rs and not np.isnan(dr):
                add(duo, (bb[0], bs[0], rb[0], rs[0]), t, dr); add(duo, (rb[0], rs[0], bb[0], bs[0]), t, -dr)
    F = pd.DataFrame(rows).set_index("gameid")
    for c in ["duo", "lane_top", "lane_jng", "lane_mid", "res_top", "res_jng", "res_mid", "res_duo"]:
        if c not in F: F[c] = np.nan
    F["lane_all"] = F.lane + F.duo.fillna(0)
    return F
def fit(Z, X, y, lam=1.0):
    b = np.zeros(X.shape[1])
    for _ in range(60):
        p = 1 / (1 + np.exp(-(Z + X @ b))); g = X.T @ (p - y) + lam * b
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(X.shape[1]); s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-9: break
    return b
def ll(Z, X, y, b):
    p = np.clip(1 / (1 + np.exp(-(Z + X @ b))), 1e-6, 1 - 1e-6); return round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4)
G = V.dropna(subset=["z_v1"]).drop(columns=["patch"], errors="ignore"); G["day"] = G.date.str[:10]
R = {}
for window in ("meta", "season"):
    for k in (5, 20):
        F = run(window, k, k); D = G.join(F, how="inner")
        if window == "meta": D = D.join(pd.Series({g: games[g]["patch"] for g in games}, name="pt")); D = D[D.pt.isin(META)]
        tr, te, wo = D[D.day < "2026-09-01"], D[D.day >= "2026-09-01"], D[D.league == "WLDs"]
        key = f"{window} k={k}"; R[key] = {"games": [len(tr), len(te), len(wo)]}
        # lane result link (later games only: from 1 Sep)
        lt = {}
        for pos, fv, rv in (("top", "lane_top", "res_top"), ("jng", "lane_jng", "res_jng"), ("mid", "lane_mid", "res_mid"), ("bot duo", "duo", "res_duo")):
            S = te[[fv, rv]].dropna(); S = S[S[fv] != 0]
            if len(S) >= 20: lt[pos] = {"n": len(S), "corr": round(float(np.corrcoef(S[fv], S[rv])[0, 1]), 3)}
        R[key]["lane_link_from_sep"] = lt
        z0 = lambda d: np.zeros((len(d), 1))
        R[key]["v1"] = [ll(te.z_v1.values, z0(te), te.blue_win.values, np.zeros(1)), ll(wo.z_v1.values, z0(wo), wo.blue_win.values, np.zeros(1))]
        for name, cols in {"synergy": ["syn"], "lanes": ["lane_all"], "synergy + lanes": ["syn", "lane_all"]}.items():
            sd = tr[cols].std().replace(0, 1); X = lambda d: (d[cols].fillna(0) / sd).values
            b = fit(tr.z_v1.values, X(tr), tr.blue_win.values)
            R[key][name] = {"weights_per_sd": dict(zip(cols, np.round(b, 3).tolist())), "from_sep": ll(te.z_v1.values, X(te), te.blue_win.values, b),
                            "worlds": ll(wo.z_v1.values, X(wo), wo.blue_win.values, b)}
        R[key]["share_of_test_games_with_a_prior_pair"] = {"synergy": round(float((te.n_syn > 0).mean()), 3), "lanes": round(float((te.n_lane > 0).mean()), 3)}
json.dump(R, open(os.path.join(OUT, "profit_results.json"), "w"), indent=1)
print(json.dumps(R, indent=1))
