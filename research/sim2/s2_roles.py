"""Sim session 2, part 2, step 7 (read-only): every draft input tested role by role (Luke, 4-5 Nov), each alone on top of v1.
Per game and role, blue minus red, from earlier days only (no look-ahead):
  comf_n    log(1 + the player's earlier games on that champion, all leagues incl. minor)
  comf_res  the player's win residual (result - v1 chance) on that champion, pulled toward 0 (k = 30 games)
  champ     champion-role win residual, 90-day half-life, pulled toward 0 (k = 100)
  solo_wr   lolalytics Emerald+ win rate in that lane on the game's patch, minus the lane average (16.11+ only)
  lane_solo lolalytics matchup d1 v the opposing champion in the same role, both ways (16.15-16.17, 16.20)
  lane_pro  pro lane gold at 15 (after the two players' laning skills) of that champion pair, earlier games on 16.15+ only (k = 5)
Pairs (teammates): jng-top, jng-mid, jng-bot, jng-sup, bot-sup, mid-sup:
  syn_pro   pro win residual of that teammate pair, earlier games on 16.15+ only (k = 5)
  syn_solo  lolalytics synergy d1 (jng pairs and bot-sup; 16.17 and 16.20 only)
Test per feature: logit = z_v1 + b * x / sd(x). Check: fit Feb-Jun, score Jul-Aug. Test: fit Feb-Aug, score from 1 Sep and Worlds.
A feature passes only if it beats v1 on BOTH Jul-Aug and from 1 Sep.
usage: python -I s2_roles.py <OE csv> v1_games.csv gfeat.csv lola_tiers_all.csv lola_counters.csv lola_synergy.txt <out_dir>"""
import json, os, re, sys
from collections import defaultdict
import numpy as np
import pandas as pd

CSV, V1, GF, TIERS, CNT, SYN, OUT = sys.argv[1:8]; os.makedirs(OUT, exist_ok=True)
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
ROLES = ["top", "jng", "mid", "bot", "sup"]
LANE = {"top": "top", "jng": "jungle", "mid": "middle", "bot": "bottom", "sup": "support"}
PAIRS = [("jng", "top"), ("jng", "mid"), ("jng", "bot"), ("jng", "sup"), ("bot", "sup"), ("mid", "sup")]
META = {"16.15", "16.16", "16.17", "16.20"}
SKILL = {"top": "e_laning", "jng": "e_early", "mid": "e_laning", "bot": "e_lane_own", "sup": "e_playmaking"}
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalpha())
def np_(p):
    a, _, b = str(p).partition("."); return f"{a}.{b}0" if len(b) == 1 else f"{a}.{b.zfill(2)}"
raw = pd.read_csv(CSV, low_memory=False, dtype={"patch": str},
                  usecols=["gameid", "league", "date", "patch", "side", "position", "playerid", "champion", "result", "golddiffat15"])
raw = raw[(raw.position != "team") & ~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy()
raw["patch"] = raw.patch.map(np_); raw["day"] = raw.date.str[:10]; raw["major"] = raw.league.isin(MAJOR)
V = pd.read_csv(V1); pv = V.set_index("gameid").p_v1.to_dict()
raw["p_side"] = raw.gameid.map(pv); red = raw.side == "Red"; raw.loc[red, "p_side"] = 1 - raw.loc[red, "p_side"]
raw["res"] = raw.result - raw.p_side
gf = pd.read_csv(GF)
gf["skill"] = [r[SKILL[r.position]] for _, r in gf.iterrows()]
raw = raw.merge(gf[["gameid", "side", "position", "skill"]], on=["gameid", "side", "position"], how="left")
# outside tables
L = pd.read_csv(TIERS, dtype={"patch": str}); L["patch"] = L.patch.map(np_); L = L[L.games >= 300]
avg = L.groupby(["patch", "lane"]).apply(lambda d: np.average(d.wr, weights=d.games)).rename("la")
L = L.join(avg, on=["patch", "lane"]); SOLOWR = {(r.patch, r.lane, key(r.name)): r.wr - r.la for r in L.itertuples()}
C = pd.read_csv(CNT, dtype={"patch": str}); C["patch"] = C.patch.map(np_)
D1 = {(r.patch, r.position, r.vslane, key(r.champion), key(r.vs_champion)): r.d1 for r in C.itertuples()}
lines = open(SYN, encoding="utf-8").read().splitlines(); PRO = json.loads(lines[1].split("=", 1)[1])
SY = {}
for ln in lines[2:]:
    head, _, body = ln.partition(":"); ch, lane, p = head.split("|"); pos = "jng" if lane == "j" else "bot"
    for m in re.finditer(r"([tmbs])(\d+),(-?[\d.]+),(\d+)", body):
        mp = {"t": "top", "m": "mid", "b": "bot", "s": "sup"}[m.group(1)]
        SY[("16." + p, pos, key(ch), mp, key(PRO[int(m.group(2))]))] = float(m.group(3))
def solo_lane(patch, pos, a, b):
    x = D1.get((patch, pos, LANE[pos], key(a), key(b))); y = D1.get((patch, pos, LANE[pos], key(b), key(a)))
    v = [s for s in (x, None if y is None else -y) if s is not None]; return float(np.mean(v)) if v else 0.0
def solo_syn(patch, a_pos, a, b_pos, b):
    v = SY.get((patch, a_pos, key(a), b_pos, key(b)))
    if v is None: v = SY.get((patch, b_pos, key(b), a_pos, key(a)))
    return v if v is not None else 0.0
# lane residual slope per role (fitted before 1 Sep)
maj = raw[raw.major]
BL = maj[maj.side == "Blue"].set_index(["gameid", "position"]); RD = maj[maj.side == "Red"].set_index(["gameid", "position"])
LP = BL[["day", "golddiffat15", "skill", "champion"]].join(RD[["skill", "champion"]], rsuffix="_r").reset_index()
SL = {}
for pos in ROLES:
    d = LP[(LP.position == pos) & (LP.day < "2026-09-01")].dropna(subset=["golddiffat15", "skill", "skill_r"])
    SL[pos] = np.polyfit(d.skill - d.skill_r, d.golddiffat15, 1)
LP["lres"] = [r.golddiffat15 - np.polyval(SL[r.position], r.skill - r.skill_r) if pd.notna(r.skill) and pd.notna(r.skill_r) and pd.notna(r.golddiffat15) else np.nan
              for r in LP.itertuples()]
lres = {(r.gameid, r.position): r.lres for r in LP.itertuples()}
# one pass over days
t0 = pd.Timestamp("2026-01-01")
acc_ch, acc_pc, cnt, acc_lp, acc_sp = {}, {}, defaultdict(int), defaultdict(lambda: [0.0, 0.0]), defaultdict(lambda: [0.0, 0.0])
def dec(acc, k, t, hl):
    S, N, tl = acc.get(k, (0.0, 0.0, t)); f = 0.5 ** ((t - tl) / hl) if hl else 1.0; return S * f, N * f
def upd(acc, k, t, hl, v):
    S, N = dec(acc, k, t, hl); acc[k] = (S + v, N + 1.0, t)
feats = {}
for d, rows in raw.groupby("day", sort=True):
    t = (pd.Timestamp(d) - t0).days
    mj = rows[rows.major]
    for g, gr in mj.groupby("gameid"):
        f = defaultdict(float); patch = gr.patch.iloc[0]
        side = {(r.side, r.position): r for r in gr.itertuples(index=False)}
        for (sd, pos), r in side.items():
            sg = 1.0 if sd == "Blue" else -1.0
            f[f"comf_n|{pos}"] += sg * np.log1p(cnt[(r.playerid, r.champion)])
            S, N = dec(acc_pc, (r.playerid, r.champion), t, None); f[f"comf_res|{pos}"] += sg * S / (N + 30)
            S, N = dec(acc_ch, (r.champion, pos), t, 90.0); f[f"champ|{pos}"] += sg * S / (N + 100)
            f[f"solo_wr|{pos}"] += sg * SOLOWR.get((patch, LANE[pos], key(r.champion)), 0.0) / 100
        for pos in ROLES:
            b, rr = side.get(("Blue", pos)), side.get(("Red", pos))
            if b and rr:
                f[f"lane_solo|{pos}"] = solo_lane(patch, pos, b.champion, rr.champion) / 100
                if patch in META:
                    s1, n1 = acc_lp[(pos, b.champion, rr.champion)]; s2, n2 = acc_lp[(pos, rr.champion, b.champion)]
                    f[f"lane_pro|{pos}"] = (s1 / (n1 + 5) - s2 / (n2 + 5)) / 2 / 1000
        for a, c in PAIRS:
            for sd, sg in (("Blue", 1.0), ("Red", -1.0)):
                x, y = side.get((sd, a)), side.get((sd, c))
                if x and y:
                    if patch in META:
                        s, n = acc_sp[(a, x.champion, c, y.champion)]; f[f"syn_pro|{a}-{c}"] += sg * s / (n + 5)
                    if patch in ("16.17", "16.20"):
                        f[f"syn_solo|{a}-{c}"] += sg * solo_syn(patch, a, x.champion, c, y.champion) / 100
        feats[g] = f
    # update after the day
    for r in rows.itertuples(index=False):
        cnt[(r.playerid, r.champion)] += 1
        if r.major and pd.notna(r.res):
            upd(acc_pc, (r.playerid, r.champion), t, None, r.res); upd(acc_ch, (r.champion, r.position), t, 90.0, r.res)
    for g, gr in mj.groupby("gameid"):
        patch = gr.patch.iloc[0]
        if patch not in META: continue
        side = {(r.side, r.position): r for r in gr.itertuples(index=False)}
        for pos in ROLES:
            b, rr = side.get(("Blue", pos)), side.get(("Red", pos)); lr = lres.get((g, pos), np.nan)
            if b and rr and pd.notna(lr):
                acc_lp[(pos, b.champion, rr.champion)][0] += lr; acc_lp[(pos, b.champion, rr.champion)][1] += 1
                acc_lp[(pos, rr.champion, b.champion)][0] -= lr; acc_lp[(pos, rr.champion, b.champion)][1] += 1
        for sd in ("Blue", "Red"):
            rs = [r.res for (s2, _), r in side.items() if s2 == sd and pd.notna(r.res)]
            if not rs: continue
            res = rs[0]
            for a, c in PAIRS:
                x, y = side.get((sd, a)), side.get((sd, c))
                if x and y: acc_sp[(a, x.champion, c, y.champion)][0] += res; acc_sp[(a, x.champion, c, y.champion)][1] += 1
F = pd.DataFrame.from_dict(feats, orient="index").fillna(0.0)
G = V.dropna(subset=["z_v1"]).drop(columns=["patch"], errors="ignore").set_index("gameid"); G["day"] = G.date.str[:10]
D = G.join(F, how="inner").fillna(0.0)
def fit(Z, X, y, lam=1.0):
    b = np.zeros(X.shape[1])
    for _ in range(60):
        p = 1 / (1 + np.exp(-(Z + X @ b))); g = X.T @ (p - y) + lam * b
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(X.shape[1]); s = np.linalg.solve(H, g); b -= s
        if np.max(np.abs(s)) < 1e-9: break
    return b
def ll(Z, X, y, b):
    p = np.clip(1 / (1 + np.exp(-(Z + X @ b))), 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
sp = lambda a, z: D[(D.day >= a) & (D.day < z)]
trv, va, tr, te, wo = sp("2026-02-01", "2026-07-01"), sp("2026-07-01", "2026-09-01"), sp("2026-02-01", "2026-09-01"), sp("2026-09-01", "2027-01-01"), D[D.league == "WLDs"]
z0 = np.zeros(1)
base = {n: ll(d.z_v1.values, np.zeros((len(d), 1)), d.blue_win.values, z0) for n, d in (("jul_aug", va), ("from_sep", te), ("worlds", wo))}
rows = []
for c in sorted(F.columns):
    sd = tr[c].std()
    if not sd or np.isnan(sd): continue
    X = lambda d: (d[[c]] / sd).values
    bv = fit(trv.z_v1.values, X(trv), trv.blue_win.values); b = fit(tr.z_v1.values, X(tr), tr.blue_win.values)
    r = {"input": c.split("|")[0], "role": c.split("|")[1], "weight_per_sd": round(float(b[0]), 3),
         "games_with_value_from_sep": int((te[c] != 0).sum()),
         "d_jul_aug": round(ll(va.z_v1.values, X(va), va.blue_win.values, bv) - base["jul_aug"], 4),
         "d_from_sep": round(ll(te.z_v1.values, X(te), te.blue_win.values, b) - base["from_sep"], 4),
         "d_worlds": round(ll(wo.z_v1.values, X(wo), wo.blue_win.values, b) - base["worlds"], 4)}
    r["passes"] = bool(r["d_jul_aug"] < 0 and r["d_from_sep"] < 0)
    rows.append(r)
T = pd.DataFrame(rows).sort_values(["input", "role"])
T.to_csv(os.path.join(OUT, "roles_results.csv"), index=False)
json.dump({"v1": {k: round(v, 4) for k, v in base.items()}, "games": [len(va), len(te), len(wo)]}, open(os.path.join(OUT, "roles_base.json"), "w"))
pd.set_option("display.width", 200); print("v1:", {k: round(v, 4) for k, v in base.items()}); print(T.to_string(index=False))
