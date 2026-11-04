"""Sim session 2, step 6 (read-only): lolalytics synergy (solo queue, Emerald+) for pro teammate pairs.
Pairs (from the pages read): jungle with top, mid, ADC, support (jungle champion's page); ADC with support (ADC's page).
Value = lolalytics delta 1 = win rate together - (each champion's own win rate averaged), percentage points, on the game's patch
(16.17 or 16.20 only: the two patches read). Side value = sum of its pairs; game feature = blue - red.
Tests: (a) link with pro results: side value v the win left after v1 (result - v1 chance), and v pro pair records from s2_pro.py;
(b) win odds beyond v1: train on 16.17 games before 1 Sep, test from 1 Sep and on Worlds (16.20).
(c) the app's metabot duos (DUOS in js/data.js, delta) v lolalytics ADC-support delta 1 on 16.20, same pairs.
usage: python -I s2_syn.py <OE csv> v1_games.csv lola_synergy.txt <data.js> <out_dir>"""
import json, os, re, sys
import numpy as np
import pandas as pd

CSV, V1, SYN, JS, OUT = sys.argv[1:6]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalpha())
lines = open(SYN, encoding="utf-8").read().splitlines()
PRO = json.loads(lines[1].split("=", 1)[1])
LANE = {"t": "top", "m": "mid", "b": "bot", "s": "sup"}
S = {}   # (patch, page_pos, page_champ_key, mate_pos, mate_key) -> (d1, n)
rows = []
for ln in lines[2:]:
    head, _, body = ln.partition(":"); ch, lane, p = head.split("|"); pos = "jng" if lane == "j" else "bot"; patch = "16." + p
    for item in filter(None, body.split(";")):
        m = re.match(r"([tmbs])(\d+),(-?[\d.]+),(\d+)", item)
        if not m: continue
        mp, mi, d1, n = LANE[m.group(1)], int(m.group(2)), float(m.group(3)), int(m.group(4))
        S[(patch, pos, ch, mp, key(PRO[mi]))] = (d1, n); rows.append((patch, pos, ch, mp, PRO[mi], d1, n))
pd.DataFrame(rows, columns=["patch", "page_pos", "page_champion", "mate_pos", "mate", "d1", "games"]).to_csv(os.path.join(OUT, "lola_synergy.csv"), index=False)
R = {"pairs_read": len(S)}
def np_(p):
    a, _, b = str(p).partition("."); return f"{a}.{b}0" if len(b) == 1 else f"{a}.{b.zfill(2)}"
df = pd.read_csv(CSV, low_memory=False, dtype={"patch": str}, usecols=["gameid", "league", "date", "patch", "side", "position", "champion"])
df = df[df.league.isin(MAJOR) & (df.position != "team") & ~((df.league == "WLDs") & (df.date < "2026-10-01"))].copy()
df["patch"] = df.patch.map(np_); df = df[df.patch.isin(["16.17", "16.20"])]
W = df.pivot_table(index=["gameid", "side"], columns="position", values="champion", aggfunc="first")
pt = df.groupby("gameid").patch.first()
def side_val(g, side):
    try: c = W.loc[(g, side)]
    except KeyError: return np.nan, 0
    p = pt[g]; tot, k = 0.0, 0
    for mp in ("top", "mid", "bot", "sup"):
        v = S.get((p, "jng", key(c["jng"]), mp, key(c[mp])))
        if v: tot += v[0]; k += 1
    v = S.get((p, "bot", key(c["bot"]), "sup", key(c["sup"])))
    if v: tot += v[0]; k += 1
    return tot, k
V = pd.read_csv(V1).dropna(subset=["z_v1"]).set_index("gameid"); V["day"] = V.date.str[:10]
F = []
for g in pt.index:
    b, kb = side_val(g, "Blue"); r, kr = side_val(g, "Red")
    F.append((g, b - r, kb, kr))
F = pd.DataFrame(F, columns=["gameid", "syn", "kb", "kr"]).set_index("gameid")
D = V.join(F, how="inner")
R["coverage"] = {"games": len(D), "pairs_found_per_side_avg": round(float((D.kb + D.kr).mean() / 2), 2), "of_possible": 5}
D["res"] = D.blue_win - D.p_v1
R["link_with_pro_win_left_after_v1"] = {s: {"n": int(len(d)), "corr": round(float(np.corrcoef(d.syn, d.res)[0, 1]), 3)}
                                         for s, d in (("16.17", D[D.league != "WLDs"]), ("Worlds 16.20", D[D.league == "WLDs"]), ("all", D))}
def fit(Z, X, y, lam=1.0):
    b = np.zeros(X.shape[1])
    for _ in range(60):
        p = 1 / (1 + np.exp(-(Z + X @ b))); g = X.T @ (p - y) + lam * b
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(X.shape[1]); s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-9: break
    return b
def ll(Z, X, y, b):
    p = np.clip(1 / (1 + np.exp(-(Z + X @ b))), 1e-6, 1 - 1e-6); return round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4)
tr, te, wo = D[D.day < "2026-09-01"], D[D.day >= "2026-09-01"], D[D.league == "WLDs"]
sd = tr.syn.std(); X = lambda d: (d[["syn"]] / sd).values; z0 = lambda d: np.zeros((len(d), 1))
b = fit(tr.z_v1.values, X(tr), tr.blue_win.values)
R["win_test"] = {"games": [len(tr), len(te), len(wo)], "points_per_sd": round(float(sd), 2), "weight_per_sd": round(float(b[0]), 3),
                 "v1": [ll(te.z_v1.values, z0(te), te.blue_win.values, np.zeros(1)), ll(wo.z_v1.values, z0(wo), wo.blue_win.values, np.zeros(1))],
                 "v1 + synergy": [ll(te.z_v1.values, X(te), te.blue_win.values, b), ll(wo.z_v1.values, X(wo), wo.blue_win.values, b)]}
# metabot duos v lolalytics
txt = open(JS, encoding="utf-8").read(); duos = re.search(r"const DUOS=\[(.*?)\];", txt, re.S).group(1)
M = [(a, s, float(d)) for a, s, w, d, n in re.findall(r'\["([^"]+)","([^"]+)",([\d.]+),(-?[\d.]+),(\d+)\]', duos)]
J = [(a, s, d, S.get(("16.20", "bot", key(a), "sup", key(s)), (None,))[0]) for a, s, d in M]
J = [x for x in J if x[3] is not None]
if len(J) >= 5:
    a, b2 = np.array([x[2] for x in J]), np.array([x[3] for x in J])
    R["metabot_v_lolalytics_duos"] = {"pairs": len(J), "of": len(M), "rank_agreement": round(float(pd.Series(a).rank().corr(pd.Series(b2).rank())), 3),
                                      "same_sign": int(np.sum(np.sign(a) == np.sign(b2)))}
json.dump(R, open(os.path.join(OUT, "synfit_results.json"), "w"), indent=1); print(json.dumps(R, indent=1))
# (d) no fitted weight: take lolalytics' delta as the change in win chance (points), at full and half strength
def ll_p(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6); return round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4)
R["direct_use"] = {}
for scale in (1.0, 0.5, 0.25):
    for name, d in (("from_sep", te), ("worlds", wo), ("all 16.17+16.20", D)):
        p = np.clip(d.p_v1 + scale * d.syn / 100, 0.01, 0.99)
        R["direct_use"].setdefault(f"scale {scale}", {})[name] = [ll_p(p.values, d.blue_win.values), ll_p(d.p_v1.values, d.blue_win.values)]
json.dump(R, open(os.path.join(OUT, "synfit_results.json"), "w"), indent=1); print(json.dumps(R["direct_use"], indent=1))
