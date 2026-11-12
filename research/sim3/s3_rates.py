"""Sim session 3, step 5 (read-only): per-minute rates for the game-state sim, from gol.gg timelines matched to the file.
Three rate models, each fitted on games before 1 Sep and judged on games from 1 Sep and Worlds (Poisson / log loss v a
phase-only baseline):
  (segments and base pushes also take the side's net kills this minute: real towers fall after won fights, which is
   why slow, low-kill games are the long ones)
  (segments also take whether a push is already rolling in that lane, and T3 x Baron: real inhibitor turrets usually fall in the
   same push as the T2, mostly under Baron)
  segments    tower damage segments a side takes in a lane in a minute (gol.gg "plates": 5 per tower on these patches, the
              tower falls with its 5th) ~ lane lead, team lead, v1 strength, Baron / Elder buff, Herald, grubs, tier, phase
  base        inhibitors, nexus towers and nexus a side takes in a minute once a lane is open ~ team lead, v1, buffs,
              enemy inhibitors down, open lanes. The sim uses it as a push: the chance of any base take this minute
              (logistic: does a push start), then its size from real pushes (base takes under 30 s apart), by whether an
              enemy inhibitor was already down when it started
  fights      fights starting in a minute (kills 20 s+ apart start a new fight) ~ phase, gold lead size, monster up, buff up
  monsters    chance a dragon / grubs / Herald / Baron / Elder that is up gets taken this minute ~ minutes since spawn,
              gold lead size, a fight this minute
Spawns: dragon 5:00 then 5:00 after each take, Elder 6:00 after soul, grubs 8:00, Herald 15:00, Baron 20:00 then 6:00
after each take (from the earliest takes in the timelines). Buffs: Baron 3:00, Elder 2:30. Inhibitors back after 5:00.
Draft style (s3_comp.py, champion styles from games before 1 Sep): pace (both drafts) in the fight rate, siege (own minus
enemy draft) in tower segments and base structures.
usage: python -I s3_rates.py tl_match.csv tl_events.csv tl_gold.csv v1_games.csv <out_dir> comp3_games.csv"""
import os, sys, json
import numpy as np
import pandas as pd

TM, TE, TGo, V1, OUT = sys.argv[1:6]; os.makedirs(OUT, exist_ok=True)
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.gameid != "AMBIGUOUS")].drop_duplicates("gameid")
v1 = pd.read_csv(V1).set_index("gameid"); M["z"] = M.gameid.map(v1.z_v1); M = M[M.z.notna()].copy()
# Walk-forward (11 Nov): with S3_CUTOFF set, fit on every game before that date (Worlds games before it included); without it,
# the fixed test exactly as before.
CUT = os.environ.get("S3_CUTOFF", "2026-09-01"); WF = "S3_CUTOFF" in os.environ
M["split"] = np.where(M.date < CUT, "train", "test"); M.loc[M.tournament.str.startswith("Worlds") & ((M.date >= CUT) | (not WF)), "split"] = "worlds"
comp = pd.read_csv(sys.argv[6]).set_index("gameid")
M["siege_d"] = M.gameid.map(comp.siege_blue - comp.siege_red).fillna(0); M["siege_s"] = M.gameid.map(comp.siege_blue + comp.siege_red).fillna(0)
M["obj_s"] = M.gameid.map(comp.objectives_blue + comp.objectives_red).fillna(0);
M["siege_b"] = M.gameid.map(comp.siege_blue).fillna(0); M["siege_r"] = M.gameid.map(comp.siege_red).fillna(0); M["pace_s"] = M.gameid.map(comp.pace_blue + comp.pace_red).fillna(0)
info = M.set_index("gid")
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(M.gid)].copy(); ev["m"] = ev.t // 60
go = pd.read_csv(TGo, dtype={"gid": str}); go = go[go.gid.isin(M.gid) & (go.kind == "gold")]
go["sv"] = go.value * np.where(go.side == "blue", 1, -1)
GD = go.groupby(["gid", "minute"]).sv.sum().to_dict()
SP = {"dragon": 300, "grub": 480, "herald": 900, "baron": 1200}
PH = [0, 14, 20, 25, 30, 35, 999]; PHN = ["0-13", "14-19", "20-24", "25-29", "30-34", "35+"]
phase = lambda m: PHN[np.searchsorted(PH, m, side="right") - 1]

def pois_fit(X, y, l2=1.0, it=60):
    b = np.zeros(X.shape[1]); b[0] = np.log(max(y.mean(), 1e-3))
    for _ in range(it):
        mu = np.exp(X @ b); H = X.T @ (X * mu[:, None]) + l2 * np.eye(len(b)); g = X.T @ (y - mu) - l2 * b
        b += np.linalg.solve(H, g)
    return b
def logit_fit(X, y, l2=1.0, it=60):
    b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); H = X.T @ (X * (p * (1 - p))[:, None]) + l2 * np.eye(len(b)); g = X.T @ (y - p) - l2 * b
        b += np.linalg.solve(H, g)
    return b
pdev = lambda mu, y: float(np.mean(mu - y * np.log(np.maximum(mu, 1e-9))))  # Poisson loss (lower is better)
lg = lambda p, y: float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

# ---------- build per game-minute state ----------
SEG, BASE, Fp, Mo, PUSH = [], [], [], [], []
RD = go.groupby(["gid", "minute", "role"]).sv.sum().to_dict()
def idn_any(e, t0, by):  # side `by` has an enemy inhibitor down (it took one in the last 5 min)
    i = e[(e.type == "inhib") & (e.side == by)]; return bool(((i.t <= t0) & (i.t > t0 - 300)).any())
for g, gi in info.iterrows():
    e = ev[ev.gid == g].sort_values("t"); L = int(gi.len) // 60
    kills = e[e.type == "kill"].t.values; ksides = e[e.type == "kill"].side.values
    fstart = kills[np.r_[True, np.diff(kills) > 20]] if len(kills) else np.array([])
    st = e[e.type.isin(["tower", "inhib", "nexus"])]
    bar = e[e.type == "baron"]; eld = e[(e.type == "dragon") & (e.detail == "elder")]
    inh = e[e.type == "inhib"]; t3 = e[(e.type == "tower") & e.detail.str.startswith("T3", na=False)]
    pla = e[e.type == "plate"]  # tower segments: 5 per tower, the tower falls with its 5th
    base = e[(e.type.isin(["inhib", "nexus"])) | ((e.type == "tower") & e.detail.str.contains("NEXUS", na=False))]
    # base pushes: base takes by one side less than 30 s apart are one push (real pushes run across minute boundaries)
    pstart = {"blue": [], "red": []}
    for sd_ in ("blue", "red"):
        bt = np.sort(base[base.side == sd_].t.values); i = 0; nex_t = base[(base.side == sd_) & (base.type == "nexus")].t.values
        while i < len(bt):
            j = i
            while j + 1 < len(bt) and bt[j + 1] - bt[j] <= 30: j += 1
            dn = int(((inh.t < bt[i]) & (inh.t > bt[i] - 300) & (inh.side == sd_)).any())
            pstart[sd_].append(bt[i]); PUSH.append((gi.split, sd_, j - i + 1, dn, g, int(bt[i] // 60), int(((nex_t >= bt[i]) & (nex_t <= bt[j])).any()))); i = j + 1
    pstart = {k: np.array(v) for k, v in pstart.items()}
    he = e[e.type == "herald"]; gr = e[e.type == "grub"]
    # monster windows
    drag = e[e.type == "dragon"]; up = []
    nxt = SP["dragon"]; soul = {"blue": 0, "red": 0}; elder_mode = False
    for r in drag.itertuples():
        up.append(("elder" if r.detail == "elder" else "dragon", nxt, r.t))
        if r.detail != "elder": soul[r.side] += 1
        if max(soul.values()) >= 4: elder_mode = True
        nxt = r.t + (360 if elder_mode else 300)
    up.append(("elder" if elder_mode else "dragon", nxt, None))
    up.append(("grub", SP["grub"], gr.t.min() if len(gr) else None))
    up.append(("herald", SP["herald"], he.t.min() if len(he) else None))
    nb = SP["baron"]
    for r in bar.itertuples(): up.append(("baron", nb, r.t)); nb = r.t + 360
    up.append(("baron", nb, None))
    for m in range(L + 1):
        t0, t1 = 60 * m, 60 * m + 60
        gd = GD.get((g, m), np.nan)
        nf = int(((fstart >= t0) & (fstart < t1)).sum())
        mon_up = any(s_ <= t0 and (tk is None or tk >= t0) for k, s_, tk in up if k in ("dragon", "baron", "elder"))
        buff_any = bool(((bar.t <= t0) & (bar.t > t0 - 180)).any() or ((eld.t <= t0) & (eld.t > t0 - 150)).any())
        Fp.append((g, m, gi.split, gd, nf, int(mon_up), int(buff_any), gi.pace_s))
        for side, sg in [("blue", 1), ("red", -1)]:
            lead = gd * sg / 1000 if gd == gd else np.nan
            inm = (kills >= t0) & (kills < t1); netk = int(((ksides == side) & inm).sum() - ((ksides != side) & inm).sum())  # this side's net kills this minute
            bb = int(((bar.t <= t0) & (bar.t > t0 - 180) & (bar.side == side)).any())
            ee = int(((eld.t <= t0) & (eld.t > t0 - 150) & (eld.side == side)).any())
            idn = int(((inh.t <= t0) & (inh.t > t0 - 300) & (inh.side == side)).sum())
            hr = int(((he.t <= t0) & (he.t > t0 - 180) & (he.side == side)).any())
            gq = int(((gr.t <= t0) & (gr.side == side)).sum())
            opn = 0; just = 0
            for lane, roles in [("TOP", ["top"]), ("MID", ["mid"]), ("BOT", ["bot", "sup"])]:
                lt = pla[(pla.side == side) & (pla.detail == lane)].t.values
                if len(lt) >= 15 and lt[14] < t1:  # lane open by the end of this minute (the sim takes towers before base, in the same minute)
                    opn += 1; just += int(lt[14] >= t0 - 60)
                done = int((lt < t0).sum())
                if done >= 15: continue
                ll = sum(RD.get((g, m, ro), np.nan) for ro in roles) * sg / 1000
                y = int(((lt >= t0) & (lt < t1)).sum())
                SEG.append((g, m, gi.split, side, lane, done // 5, ll, lead, gi.z * sg, bb, ee, hr, gq, gi.siege_d * sg, gi.siege_s, netk, gi.siege_b if sg > 0 else gi.siege_r, y, done % 5))
            if opn:
                tk = base[(base.t >= t0) & (base.t < t1) & (base.side == side)]
                prev = int(((base.t >= t0 - 60) & (base.t < t0) & (base.side == side)).any())  # kept pushing last minute
                npush_start = int(((pstart[side] >= t0) & (pstart[side] < t1)).sum())
                BASE.append((g, m, gi.split, side, lead, gi.z * sg, bb, ee, idn, opn, gi.siege_d * sg, gi.siege_s, int(just > 0), prev, netk, gi.siege_b if sg > 0 else gi.siege_r, npush_start,
                             int((tk.type != "inhib").sum()) if idn else 0, len(tk) if idn else 0))
        fdi = next(i for i, u in enumerate(up) if u[0] == "dragon") if any(u[0] == "dragon" for u in up) else -1
        for ui, (k, s_, tk) in enumerate(up):
            if s_ <= t0 + 59 and (tk is None or tk >= t0) and s_ < 60 * (L + 1):
                if tk is not None and tk < max(t0, s_): continue
                Mo.append((g, m, gi.split, k, max(0, (t0 - s_) // 60), abs(gd) / 1000 if gd == gd else np.nan, nf > 0,
                           int(tk is not None and t0 <= tk < t1), int(ui == fdi), gi.obj_s))
SEG = pd.DataFrame(SEG, columns=["gid", "m", "split", "side", "lane", "tier", "lane_lead", "lead", "z", "baron", "elder", "herald3", "grubs", "siege", "siege_s", "net_k", "siege_own", "y", "in_tower"]).dropna()
# a push already rolling in this lane: segments this side took in the same lane the minute before (consecutive minutes only)
SEG = SEG.sort_values(["gid", "side", "lane", "m"])
_g = SEG.groupby(["gid", "side", "lane"])
SEG["prev_seg"] = np.where(_g.m.diff() == 1, _g.y.shift(1), 0); SEG["prev_seg"] = SEG.prev_seg.fillna(0)
# tower pushes: a lane's segments by one side less than 30 s apart are one push
_PS = []
for (g_, sd_, ln_), d_ in ev[ev.type == "plate"].sort_values("t").groupby(["gid", "side", "detail"]):
    tt = d_.t.values; i = 0
    while i < len(tt):
        j = i
        while j + 1 < len(tt) and tt[j + 1] - tt[j] <= 30: j += 1
        _PS.append((g_, sd_, ln_, int(tt[i] // 60), i // 5, j - i + 1)); i = j + 1
SPUSH = pd.DataFrame(_PS, columns=["gid", "side", "lane", "m", "tier0", "size"])
SPUSH["split"] = SPUSH.gid.map(info.split)
SEG = SEG.merge(SPUSH.groupby(["gid", "side", "lane", "m"]).size().rename("push").reset_index(), on=["gid", "side", "lane", "m"], how="left")
SEG["push"] = SEG.push.fillna(0)
BASE = pd.DataFrame(BASE, columns=["gid", "m", "split", "side", "lead", "z", "baron", "elder", "inhib_down", "open", "siege", "siege_s", "just_opened", "prev_push", "net_k", "siege_own", "y", "nx_taken", "taken_inhib_down"]).dropna()
Fp = pd.DataFrame(Fp, columns=["gid", "m", "split", "gd", "y", "mon_up", "buff", "pace_s"]).dropna()
Mo = pd.DataFrame(Mo, columns=["gid", "m", "split", "kind", "since", "alead", "fight", "y", "first", "obj_s"]).dropna()
PUSHD = pd.DataFrame(PUSH, columns=["split", "side", "size", "down", "gid", "m", "ends"])
res = {"games": M.split.value_counts().to_dict()}
dummies = lambda m: np.array([[phase(x) == p for p in PHN[1:]] for x in m], dtype=float).reshape(len(m), len(PHN) - 1)  # reshape: keeps its columns when a window has no minutes (walk-forward)

def score(name, X, d, b, b0):
    return {s: {"n": int((d.split == s).sum()), "loss": round(pdev(np.exp(X(d[d.split == s]) @ b), d[d.split == s].y.values), 4),
                "baseline": round(pdev(np.exp(X(d[d.split == s], False) @ b0), d[d.split == s].y.values), 4)} for s in ["train", "test", "worlds"]}
def dispersion(X, d, b):  # Pearson dispersion of the fitted rate on training minutes, by phase (1 = as even as Poisson)
    mu = np.exp(X(d) @ b); r = (d.y.values - mu) ** 2 / mu
    return {p: round(float(r[np.array([phase(x) == p for x in d.m.values])].mean()), 3) for p in PHN if (np.array([phase(x) == p for x in d.m.values])).any()}
SC = "siege"  # which draft-siege column the segment and base fits use (switched below for the timing-only version)
# tower segments, lane by lane (a tower falls with its 5th segment)
def Xg(d, full=True):
    base = np.c_[np.ones(len(d)), dummies(d.m.values), d.tier == 1, d.tier == 2, d.lane == "MID", d.lane == "BOT"].astype(float)
    if not full: return base
    return np.c_[base, d.lane_lead.clip(-8, 8), d.lead.clip(-15, 15), d.z, d.baron, d.elder, d.herald3, d.grubs, d.net_k.clip(-5, 5), d.prev_seg.clip(0, 5), (d.tier == 2) * d.baron, d[SC]]
names_g = ["intercept", *[f"phase {p}" for p in PHN[1:]], "tier T2", "tier T3", "mid", "bot",
           "per_1k_lane_lead", "per_1k_team_lead", "per_v1_logit", "baron", "elder", "herald_last_3min", "own_grubs", "net_kills_this_minute", "lane_segments_last_minute", "T3_x_baron", "siege_style"]
tr = SEG[SEG.split == "train"]; bgs = pois_fit(Xg(tr), tr.y.values); b0 = pois_fit(Xg(tr, False), tr.y.values)
res["segments"] = {"coef": dict(zip(names_g, np.round(bgs, 4))), **score("seg", Xg, SEG, bgs, b0), "dispersion_by_phase": dispersion(Xg, tr, bgs),
                   "check_5_per_tower": "every T1/T2/T3 in the timelines fell on its 5th/10th/15th segment"}
# base structures (inhibitors, nexus towers, nexus) once a lane is open
def Xb(d, full=True):
    base = np.c_[np.ones(len(d)), (d.m >= 25), (d.m >= 35)].astype(float)
    if not full: return base
    return np.c_[base, d.lead.clip(-15, 15), d.z, d.baron, d.elder, d.inhib_down, d.open, d[SC], d.just_opened, d.prev_push, d.net_k.clip(-5, 5)]
names_b = ["intercept", "from 25", "from 35", "per_1k_lead", "per_v1_logit", "baron", "elder", "enemy_inhibs_down", "open_lanes", "siege_style", "lane_just_opened", "base_take_last_minute", "net_kills_this_minute"]
tr = BASE[BASE.split == "train"]; bb_ = pois_fit(Xb(tr), tr.y.values); b0 = pois_fit(Xb(tr, False), tr.y.values)
res["base_structures"] = {"coef": dict(zip(names_b, np.round(bb_, 4))), **score("base", Xb, BASE, bb_, b0), "dispersion_by_phase": dispersion(Xb, tr, bb_)}
# base pushes: whether a side takes any base structure this minute (logistic), then how many (real sizes, training)
yb = (tr.y.values > 0).astype(float); bp = logit_fit(Xb(tr), yb); bp0 = logit_fit(Xb(tr, False), yb)
def push_ll(d, b, full=True):
    p = np.clip(1 / (1 + np.exp(-Xb(d, full) @ b)), 1e-6, 1 - 1e-6); return round(lg(p, (d.y.values > 0).astype(float)), 4)
res["base_push"] = {"coef": dict(zip(names_b, np.round(bp, 4))),
                    "size_dist": {str(k): round(float(v), 4) for k, v in tr.y[tr.y > 0].clip(upper=6).value_counts(normalize=True).sort_index().items()},
                    "size_dist_by_state": {st: {str(k): round(float(v), 4) for k, v in q["size"].clip(upper=6).value_counts(normalize=True).sort_index().items()}
                                           for st, q in [("no_inhib_down", PUSHD[(PUSHD.split == "train") & (PUSHD.down == 0)]),
                                                         ("inhib_down", PUSHD[(PUSHD.split == "train") & (PUSHD.down == 1)])]},
                    **{s: {"n": int((BASE.split == s).sum()), "logloss": push_ll(BASE[BASE.split == s], bp),
                           "baseline": push_ll(BASE[BASE.split == s], bp0, False)} for s in ["train", "test", "worlds"]}}
# timing-only versions: both drafts' siege together (speeds up or slows down sieges for both sides, decides nothing)
SC = "siege_s"
trs = SEG[SEG.split == "train"]; bgt = pois_fit(Xg(trs), trs.y.values); b0t = pois_fit(Xg(trs, False), trs.y.values)
res["segments_timing"] = {"coef": dict(zip(names_g[:-1] + ["siege_style_sum"], np.round(bgt, 4))), **score("seg", Xg, SEG, bgt, b0t)}
# tower pushes: chance a push starts this minute (logistic, timing-only inputs), then its size from real pushes (training)
ypt = (trs.push.values > 0).astype(float); bsp = logit_fit(Xg(trs), ypt); bsp0 = logit_fit(Xg(trs, False), ypt)
def spush_ll(d, b, full=True):
    p = np.clip(1 / (1 + np.exp(-Xg(d, full) @ b)), 1e-6, 1 - 1e-6); return round(lg(p, (d.push.values > 0).astype(float)), 4)
_tp = SPUSH[SPUSH.split == "train"].copy(); _tp["key"] = np.where((_tp.tier0 == 0) & (_tp.m < 14), "0_early", _tp.tier0.astype(str))
res["segment_push"] = {"coef": dict(zip(names_g[:-1] + ["siege_style_sum"], np.round(bsp, 4))),
                       "size_dist": {k: {str(z): round(float(v), 4) for z, v in d["size"].clip(upper=15).value_counts(normalize=True).sort_index().items()} for k, d in _tp.groupby("key")},
                       **{s_: {"n": int((SEG.split == s_).sum()), "logloss": spush_ll(SEG[SEG.split == s_], bsp), "baseline": spush_ll(SEG[SEG.split == s_], bsp0, False)}
                          for s_ in ["train", "test", "worlds"]}}
# within-game versions (6 Nov): each game-side's average lane lead and team lead over the game added as inputs (Mundlak), so the
# lead terms measure "ahead right now" rather than "the stronger team in this game" (which pooled fits mix in)
SEG["m_lane_lead"] = SEG.groupby(["gid", "side", "lane"]).lane_lead.transform("mean"); SEG["m_lead"] = SEG.groupby(["gid", "side"]).lead.transform("mean")
XgW = lambda d: np.c_[Xg(d), d.m_lane_lead.clip(-8, 8), d.m_lead.clip(-15, 15)]
trsW = SEG[SEG.split == "train"]; bspW = logit_fit(XgW(trsW), (trsW.push.values > 0).astype(float))
_llW = lambda d, b: round(lg(np.clip(1 / (1 + np.exp(-XgW(d) @ b)), 1e-6, 1 - 1e-6), (d.push.values > 0).astype(float)), 4)
res["segment_push_within"] = {"coef": dict(zip(names_g[:-1] + ["siege_style_sum", "game_mean_lane_lead", "game_mean_team_lead"], np.round(bspW, 4))),
                              "pooled_lane_lead": round(float(bsp[names_g.index("per_1k_lane_lead")]), 4), "pooled_team_lead": round(float(bsp[names_g.index("per_1k_team_lead")]), 4)}
# lane x tier version (6 Nov): real side-lane T2s hold much longer after their T1 than mid's (T1 to T2 median: top 547 s, mid 371 s,
# bot 516 s), which an additive lane + tier model averages away; four interaction terms, judged on held-out pushes
# 12 Nov: two more terms for the first tower while plates are up (before 14:00). Real mid lanes lose far fewer plates than side lanes
# (1.3 a side by 14:00 against 2.0 top and 2.1 bot) but more tower hits afterwards, which one "mid" term for the whole game averages away
# (the sim's first tower was mid 25% of the time; real 12-15%). A third term: the segments already down on this tower (0-4), since real
# pushes often start on a tower that is already damaged (side lanes before 14:00: half of pushes start with 1-4 segments down).
# Tested 12 Nov and NOT kept: the first tower stayed mid 24% of the time and games came out 1.5 min too short. Off unless S3_EARLY_LANE=1.
EARLY_LANE = bool(os.environ.get("S3_EARLY_LANE"))
# 12 Nov (spread of game length): tier x game-phase terms. With one fixed difficulty per tier for the whole game the sim's inner towers fall
# too early (first T2 median 21.4 min v real 24.8; first inhibitor by 21.9 min in 10% of sim games v 24.7 real), which gives quiet short games
# (11.6% under 24 min v 2.4% real). Real teams almost never take T2s and T3s early, whatever the lead. Opt-in: S3_TIER_PHASE=1.
TIER_PHASE = bool(os.environ.get("S3_TIER_PHASE"))
# Same switch, one more term each for tower pushes and fight starts: "minutes_before_14" (minute - 14 before 14:00, else 0). The first
# phase (0:00-13:59) had one flat rate, but real plates go from 0.09 a minute (0-3 min) to 1.68 (11-14 min) and kills from 0.13 to 0.80,
# so the sim took plates and kills far too early (kills a minute 0-5 min: sim 0.49, real 0.25; first tower by 8:30 in 10% of sim games, real 12:09).
TPN = ([f"T{t + 1} x phase {p_}" for t in (1, 2) for p_ in PHN[1:]] + ["minutes_before_14"]) if TIER_PHASE else []
LTN = ["T2 x mid", "T2 x bot", "T3 x mid", "T3 x bot"] + (["T1 early x mid", "T1 early x bot", "tower_segments_down"] if EARLY_LANE else []) + TPN
def LT(d):
    c = [(d.tier == 1) & (d.lane == "MID"), (d.tier == 1) & (d.lane == "BOT"), (d.tier == 2) & (d.lane == "MID"), (d.tier == 2) & (d.lane == "BOT")]
    if EARLY_LANE: c += [(d.tier == 0) & (d.m < 14) & (d.lane == "MID"), (d.tier == 0) & (d.m < 14) & (d.lane == "BOT"), d.in_tower]
    if TIER_PHASE:
        ph_ = np.array([phase(x) for x in d.m.values])
        c += [(d.tier.values == t) & (ph_ == p_) for t in (1, 2) for p_ in PHN[1:]] + [np.minimum(d.m.values, 14) - 14]
    return np.c_[tuple(c)].astype(float)
XgLT = lambda d, full=True: np.c_[Xg(d), LT(d)] if full else Xg(d, False)
bspLT = logit_fit(XgLT(trs), ypt)
_llLT = lambda d, b: round(lg(np.clip(1 / (1 + np.exp(-XgLT(d) @ b)), 1e-6, 1 - 1e-6), (d.push.values > 0).astype(float)), 4)
res["segment_push_lane_tier"] = {"coef": dict(zip(names_g[:-1] + ["siege_style_sum"] + LTN, np.round(bspLT, 4))),
                                 **{s_: {"n": int((SEG.split == s_).sum()), "logloss": _llLT(SEG[SEG.split == s_], bspLT), "additive": spush_ll(SEG[SEG.split == s_], bsp)}
                                    for s_ in ["train", "test", "worlds"]}}
_mu = np.exp(Xg(trs) @ bgt); _r = (trs.y.values - _mu) ** 2 / _mu
res["segments_timing"]["dispersion_by_tier"] = {str(t): round(float(_r[trs.tier.values == t].mean()), 3) for t in (0, 1, 2)}
trb = BASE[BASE.split == "train"]; ybt = (trb.y.values > 0).astype(float); bpt = logit_fit(Xb(trb), ybt)
BASE["m_lead"] = BASE.groupby(["gid", "side"]).lead.transform("mean"); trb = BASE[BASE.split == "train"]
XbW = lambda d: np.c_[Xb(d), d.m_lead.clip(-15, 15)]
bptW = logit_fit(XbW(trb), (trb.y.values > 0).astype(float))
res["base_push_within"] = {"coef": dict(zip([n if n != "siege_style" else "siege_style_sum" for n in names_b] + ["game_mean_lead"], np.round(bptW, 4)))}
res["base_push_timing"] = {"coef": dict(zip([n if n != "siege_style" else "siege_style_sum" for n in names_b], np.round(bpt, 4))),
                           **{s_: {"n": int((BASE.split == s_).sum()), "logloss": push_ll(BASE[BASE.split == s_], bpt)} for s_ in ["train", "test", "worlds"]}}
# won fights turn into towers and endings (10 Nov, report 7g): real sides that clearly win a minute's fighting take a structure and win
# soon after far more often than the sim's. The pooled fits carry this minute's kills edge (net kills) only, as a straight line; added:
# last minute's kills edge, and a "clear fight win" flag (kills edge of N+ this minute or last: dead enemies leave the map open).
# N is chosen on training games only (11 Nov; the first run's 4+ had been picked after seeing held-out games): fit on the earlier half
# of the training timeline dates, check on the later half, N from none / 2 / 3 / 4 / 5; then the final fit uses all training games.
_kk = ev[ev.type == "kill"].groupby(["gid", "m", "side"]).size().unstack("side").reindex(columns=["blue", "red"]).fillna(0)
NKB = (_kk.blue - _kk.red).to_dict()
def fight_terms(d, c):
    sg = np.where(d.side == "blue", 1, -1)
    prev = np.array([NKB.get((g_, m_ - 1), 0.0) for g_, m_ in zip(d.gid, d.m)]) * sg
    cols = [np.clip(prev, -5, 5)]
    if c is not None: cols.append(((d.net_k >= c) | (prev >= c)).astype(float))
    return np.c_[tuple(cols)]
_trd = sorted(set(info[info.split == "train"].date)); CUTD = _trd[len(_trd) // 2]; _dte = info.date.to_dict()
def choose_cut(T_, X0, y_):
    early = (T_.gid.map(_dte) < CUTD).values; tab = {}
    for c in (None, 2, 3, 4, 5):
        X1 = np.c_[X0, fight_terms(T_, c)]; b_ = logit_fit(X1[early], y_[early])
        tab["none" if c is None else f"{c}+"] = round(lg(np.clip(1 / (1 + np.exp(-X1[~early] @ b_)), 1e-6, 1 - 1e-6), y_[~early]), 5)
    b0_ = logit_fit(X0[early], y_[early]); base_ = round(lg(np.clip(1 / (1 + np.exp(-X0[~early] @ b0_)), 1e-6, 1 - 1e-6), y_[~early]), 5)
    best = min(tab, key=tab.get)
    return (None if best == "none" else int(best[0])), {"split_date": CUTD, "n_fit": int(early.sum()), "n_check": int((~early).sum()),
                                                        "this_minute_only": base_, "with_last_minute_and_cutoff": tab, "chosen": best}
cS, chkS = choose_cut(trs, XgLT(trs), ypt)
XgF = lambda d: np.c_[XgLT(d), fight_terms(d, cS)]
bspF = logit_fit(XgF(trs), ypt)
_llF = lambda d, b: round(lg(np.clip(1 / (1 + np.exp(-XgF(d) @ b)), 1e-6, 1 - 1e-6), (d.push.values > 0).astype(float)), 4)
_fn = lambda c: ["net_kills_last_minute"] + (["clear_fight_win"] if c is not None else [])
res["segment_push_fight"] = {"coef": dict(zip(names_g[:-1] + ["siege_style_sum"] + LTN + _fn(cS), np.round(bspF, 4))),
                             "clear_fight_cutoff": cS, "cutoff_check_training_only": chkS,
                             **{s_: {"n": int((SEG.split == s_).sum()), "logloss": _llF(SEG[SEG.split == s_], bspF), "lane_tier": _llLT(SEG[SEG.split == s_], bspLT)}
                                for s_ in ["train", "test", "worlds"]}}
trb = BASE[BASE.split == "train"]
cB, chkB = choose_cut(trb, Xb(trb), (trb.y.values > 0).astype(float))
XbF = lambda d: np.c_[Xb(d), fight_terms(d, cB)]
bptF = logit_fit(XbF(trb), (trb.y.values > 0).astype(float))
_llbF = lambda d, b: round(lg(np.clip(1 / (1 + np.exp(-XbF(d) @ b)), 1e-6, 1 - 1e-6), (d.y.values > 0).astype(float)), 4)
res["base_push_fight"] = {"coef": dict(zip([n if n != "siege_style" else "siege_style_sum" for n in names_b] + _fn(cB), np.round(bptF, 4))),
                          "clear_fight_cutoff": cB, "cutoff_check_training_only": chkB,
                          **{s_: {"n": int((BASE.split == s_).sum()), "logloss": _llbF(BASE[BASE.split == s_], bptF), "timing": push_ll(BASE[BASE.split == s_], bpt)}
                             for s_ in ["train", "test", "worlds"]}}
# simplest version (11 Nov): last minute's kills edge only, no clear-fight-win flag (nothing to choose)
XgFs = lambda d: np.c_[XgLT(d), fight_terms(d, None)]; bspFs = logit_fit(XgFs(trs), ypt)
_llFs = lambda d: round(lg(np.clip(1 / (1 + np.exp(-XgFs(d) @ bspFs)), 1e-6, 1 - 1e-6), (d.push.values > 0).astype(float)), 4)
res["segment_push_fight_simple"] = {"coef": dict(zip(names_g[:-1] + ["siege_style_sum"] + LTN + ["net_kills_last_minute"], np.round(bspFs, 4))),
                                    **{s_: {"n": int((SEG.split == s_).sum()), "logloss": _llFs(SEG[SEG.split == s_]), "lane_tier": _llLT(SEG[SEG.split == s_], bspLT)} for s_ in ["train", "test", "worlds"]}}
XbFs = lambda d: np.c_[Xb(d), fight_terms(d, None)]; bptFs = logit_fit(XbFs(trb), (trb.y.values > 0).astype(float))
_llbFs = lambda d: round(lg(np.clip(1 / (1 + np.exp(-XbFs(d) @ bptFs)), 1e-6, 1 - 1e-6), (d.y.values > 0).astype(float)), 4)
res["base_push_fight_simple"] = {"coef": dict(zip([n if n != "siege_style" else "siege_style_sum" for n in names_b] + ["net_kills_last_minute"], np.round(bptFs, 4))),
                                 **{s_: {"n": int((BASE.split == s_).sum()), "logloss": _llbFs(BASE[BASE.split == s_]), "timing": push_ll(BASE[BASE.split == s_], bpt)} for s_ in ["train", "test", "worlds"]}}
# endings after won fights (12 Nov; the spread of game length and kills). Real games end soon after a clearly won fight far more often
# than the sim's (7g), so in the sim bloody games don't end early and long games keep fighting. Two fitted pieces, training games only:
#   start  the base-push chance with the kills edge of this and last minute counting more as the game goes on (death timers grow with
#          game time, so the same fight win leaves the base open for longer): two "x time" terms, time = (minute - 25) / 10
#   size   real pushes come in two kinds: small (1-2 structures) or the push that ends the game (the nexus falls in it; 45% of pushes
#          that start with no inhibitor down take 4). So: the chance a push ends the game, on the two minutes' kills edge, an enemy
#          inhibitor already down, game time and kills edge x time; then the size from real pushes of that kind (by inhibitor state).
#          The sim drew the size from one table per inhibitor state, whatever the fight.
_tm = lambda d: (d.m.values - 25) / 10
XbE = lambda d: np.c_[XbFs(d), d.net_k.clip(-5, 5).values * _tm(d), fight_terms(d, None)[:, 0] * _tm(d)]
bptE = logit_fit(XbE(trb), (trb.y.values > 0).astype(float))
_llbE = lambda d: round(lg(np.clip(1 / (1 + np.exp(-XbE(d) @ bptE)), 1e-6, 1 - 1e-6), (d.y.values > 0).astype(float)), 4)
PUSHD["nk2"] = np.clip([(NKB.get((g_, m_), 0.0) + NKB.get((g_, m_ - 1), 0.0)) * (1 if s_ == "blue" else -1) for g_, m_, s_ in zip(PUSHD.gid, PUSHD.m, PUSHD.side)], -5, 8)
XsE = lambda d, full=True: np.c_[np.ones(len(d)), d.down, d.nk2, (d.m - 25) / 10, d.nk2 * (d.m - 25) / 10] if full else np.c_[np.ones(len(d)), d.down]
_ptr = PUSHD[PUSHD.split == "train"]; bsE = logit_fit(XsE(_ptr), _ptr.ends.values.astype(float)); bsE0 = logit_fit(XsE(_ptr, False), _ptr.ends.values.astype(float))
_ell = lambda d, b_, full=True: round(lg(np.clip(1 / (1 + np.exp(-XsE(d, full) @ b_)), 1e-6, 1 - 1e-6), d.ends.values.astype(float)), 4)
_tab = lambda q: {str(k): round(float(v), 4) for k, v in q["size"].clip(upper=6).value_counts(normalize=True).sort_index().items()}
res["endings"] = {"start": {"coef": dict(zip([n if n != "siege_style" else "siege_style_sum" for n in names_b] + ["net_kills_last_minute", "net_kills_this_minute_x_time", "net_kills_last_minute_x_time"], np.round(bptE, 4))),
                            **{s_: {"n": int((BASE.split == s_).sum()), "logloss": _llbE(BASE[BASE.split == s_]), "no_time_terms": _llbFs(BASE[BASE.split == s_])} for s_ in ["train", "test", "worlds"]}},
                  "ends_game": {"coef": dict(zip(["intercept", "enemy_inhib_down", "kills_edge_2min", "time", "kills_edge_2min_x_time"], np.round(bsE, 4))),
                                "note": "chance that a base push ends the game; time = (minute - 25) / 10; kills edge of this and last minute, clipped to -5..8",
                                "train_share": round(float(_ptr.ends.mean()), 4),
                                **{s_: {"n": int((PUSHD.split == s_).sum()), "logloss": _ell(PUSHD[PUSHD.split == s_], bsE), "inhib_state_only": _ell(PUSHD[PUSHD.split == s_], bsE0, False)}
                                   for s_ in ["train", "test", "worlds"] if (PUSHD.split == s_).any()}},
                  "size_by_kind": {f"{st}|{kd}": _tab(_ptr[(_ptr.down == dn) & (_ptr.ends == en)]) for st, dn in [("no_inhib_down", 0), ("inhib_down", 1)] for kd, en in [("ends", 1), ("other", 0)]}}
# comps option A: own draft's siege style x own lead (a siege comp that is ahead takes towers faster)
XgA = lambda d, full=True: np.c_[Xg(d, full), d.siege_own * d.lead.clip(-15, 15)] if full else Xg(d, False)
bgA = pois_fit(XgA(trs), trs.y.values)
res["segments_A"] = {"coef": dict(zip(names_g[:-1] + ["siege_style_sum", "own_siege_x_lead"], np.round(bgA, 4))),
                     **{s_: {"n": int((SEG.split == s_).sum()), "loss": round(pdev(np.exp(XgA(SEG[SEG.split == s_]) @ bgA), SEG[SEG.split == s_].y.values), 4),
                             "timing_only": round(pdev(np.exp(Xg(SEG[SEG.split == s_]) @ bgt), SEG[SEG.split == s_].y.values), 4)} for s_ in ["train", "test", "worlds"]},
                     "note": "baseline here = the timing-only model"}
XbA = lambda d, full=True: np.c_[Xb(d, full), d.siege_own * d.lead.clip(-15, 15)] if full else Xb(d, False)
bpA = logit_fit(XbA(trb), ybt)
def push_llA(d, b):
    p = np.clip(1 / (1 + np.exp(-XbA(d) @ b)), 1e-6, 1 - 1e-6); return round(lg(p, (d.y.values > 0).astype(float)), 4)
res["base_push_A"] = {"coef": dict(zip([n if n != "siege_style" else "siege_style_sum" for n in names_b] + ["own_siege_x_lead"], np.round(bpA, 4))),
                      **{s_: {"n": int((BASE.split == s_).sum()), "logloss": push_llA(BASE[BASE.split == s_], bpA),
                              "timing_only": push_ll(BASE[BASE.split == s_], bpt)} for s_ in ["train", "test", "worlds"]}}
SC = "siege"
k = BASE[BASE.taken_inhib_down > 0]
res["nexus_tier_share_when_inhib_down"] = {"structures": int(k.taken_inhib_down.sum()), "share_nexus_tier": round(float(k.nx_taken.sum() / max(k.taken_inhib_down.sum(), 1)), 3)}
TT = ev[ev.type == "tower"].copy(); TT["lane"] = TT.detail.str.extract(r"(TOP|MID|BOT)", expand=False); TT["tier"] = TT.detail.str[:2]
T1 = TT[(TT.tier == "T1") & ~TT.detail.str.contains("NEXUS")].sort_values("t")
res["first_tower_lane_share"] = T1.groupby("gid").head(1).lane.value_counts(normalize=True).round(3).to_dict()
res["first_tower_time_s"] = {"median": int(T1.groupby("gid").t.min().median()), "p10": int(T1.groupby("gid").t.min().quantile(.1)),
                             "p90": int(T1.groupby("gid").t.min().quantile(.9))}
# fights
def Xf(d, full=True):
    base = np.c_[np.ones(len(d)), dummies(d.m.values)]
    if TIER_PHASE: base = np.c_[base, np.minimum(d.m.values, 14) - 14]  # in the phase-only comparison too
    return base if not full else np.c_[base, (d.gd.abs() / 1000).clip(0, 15), d.mon_up, d.buff, d.pace_s]
tr = Fp[Fp.split == "train"]; bf = pois_fit(Xf(tr), tr.y.values); b0 = pois_fit(Xf(tr, False), tr.y.values)
res["fights"] = {"coef": dict(zip(["intercept", *[f"phase {p}" for p in PHN[1:]], *(["minutes_before_14"] if TIER_PHASE else []), "per_1k_abs_lead", "monster_up", "buff_up", "pace_style"], np.round(bf, 4))),
                 **{s: {"n": int((Fp.split == s).sum()), "loss": round(pdev(np.exp(Xf(Fp[Fp.split == s]) @ bf), Fp[Fp.split == s].y.values), 4),
                        "phase_only": round(pdev(np.exp(Xf(Fp[Fp.split == s], False) @ b0), Fp[Fp.split == s].y.values), 4)} for s in ["train", "test", "worlds"]}}
res["fights"]["dispersion_by_phase"] = dispersion(Xf, tr, bf)
# monsters
res["monsters"] = {}
for k in ["dragon", "grub", "herald", "baron", "elder"]:
    d = Mo[Mo.kind == k]
    X = lambda q: np.c_[np.ones(len(q)), (q.since == 0), (q.since == 1), (q.since >= 4), q.alead.clip(0, 15), q.fight, q["first"], q.obj_s]
    trd = d[d.split == "train"]
    if len(trd) < 40: continue
    b = logit_fit(X(trd), trd.y.values, l2=2.0)
    out = {"coef": dict(zip(["intercept", "spawn_minute", "1_min_after", "4+_min_after", "per_1k_abs_lead", "fight_this_minute", "first_dragon", "objectives_style_sum"], np.round(b, 4))),
           "minutes_up": len(d), "taken": int(d.y.sum())}
    for s in ["train", "test", "worlds"]:
        q = d[d.split == s]
        if len(q) > 5: out[s] = {"n": len(q), "logloss": round(lg(np.clip(1 / (1 + np.exp(-X(q) @ b)), 1e-6, 1 - 1e-6), q.y.values), 4),
                                 "base": round(lg(np.full(len(q), trd.y.mean()), q.y.values), 4)}
    res["monsters"][k] = out
# ---------- game tempo: does a game's fighting and pushing run above / below the fitted rates together? ----------
# per game: observed v expected fights (fight model) and tower pushes (segment_push model); method of moments for the spread of
# a game-level multiplier (Poisson / Bernoulli noise removed) and the link between the two; training games, then held out
SC = "siege_s"
Fp_ = Fp.copy(); Fp_["e"] = np.exp(Xf(Fp_) @ bf)
SG_ = SEG.copy(); SG_["e"] = 1 / (1 + np.exp(-Xg(SG_) @ bsp)); SG_["o"] = (SG_.push > 0).astype(float)
SC = "siege"
TG = Fp_.groupby("gid").agg(of=("y", "sum"), ef=("e", "sum"), split=("split", "first")).join(SG_.groupby("gid").agg(op=("o", "sum"), ep=("e", "sum")))
TG = TG.dropna()
def tempo(d):
    vf = float(((d.of - d.ef) ** 2 - d.ef).sum() / (d.ef ** 2).sum()); vp = float(((d.op - d.ep) ** 2 - d.ep).sum() / (d.ep ** 2).sum())
    cfp = float(((d.of - d.ef) * (d.op - d.ep)).sum() / (d.ef * d.ep).sum())
    return {"games": len(d), "fight_var": round(vf, 4), "push_var": round(vp, 4), "cov": round(cfp, 4),
            "corr": round(cfp / np.sqrt(max(vf, 1e-9) * max(vp, 1e-9)), 3) if vf > 0 and vp > 0 else None,
            "raw_ratio_corr": round(float(np.corrcoef(d.of / d.ef, d.op / d.ep)[0, 1]), 3)}
res["tempo"] = {s_: tempo(TG[TG.split == s_]) for s_ in ["train", "test", "worlds"]}
TG.to_csv(os.path.join(OUT, "tempo_games.csv"))
json.dump(res, open(os.path.join(OUT, "rates3_results.json"), "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))
