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
M["split"] = np.where(M.date < "2026-09-01", "train", "test"); M.loc[M.tournament.str.startswith("Worlds"), "split"] = "worlds"
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
        bt = np.sort(base[base.side == sd_].t.values); i = 0
        while i < len(bt):
            j = i
            while j + 1 < len(bt) and bt[j + 1] - bt[j] <= 30: j += 1
            dn = int(((inh.t < bt[i]) & (inh.t > bt[i] - 300) & (inh.side == sd_)).any())
            pstart[sd_].append(bt[i]); PUSH.append((gi.split, sd_, j - i + 1, dn)); i = j + 1
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
                SEG.append((g, m, gi.split, side, lane, done // 5, ll, lead, gi.z * sg, bb, ee, hr, gq, gi.siege_d * sg, gi.siege_s, netk, gi.siege_b if sg > 0 else gi.siege_r, y))
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
SEG = pd.DataFrame(SEG, columns=["gid", "m", "split", "side", "lane", "tier", "lane_lead", "lead", "z", "baron", "elder", "herald3", "grubs", "siege", "siege_s", "net_k", "siege_own", "y"]).dropna()
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
PUSHD = pd.DataFrame(PUSH, columns=["split", "side", "size", "down"])
res = {"games": M.split.value_counts().to_dict()}
dummies = lambda m: np.array([[phase(x) == p for p in PHN[1:]] for x in m], dtype=float)

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
_mu = np.exp(Xg(trs) @ bgt); _r = (trs.y.values - _mu) ** 2 / _mu
res["segments_timing"]["dispersion_by_tier"] = {str(t): round(float(_r[trs.tier.values == t].mean()), 3) for t in (0, 1, 2)}
trb = BASE[BASE.split == "train"]; ybt = (trb.y.values > 0).astype(float); bpt = logit_fit(Xb(trb), ybt)
res["base_push_timing"] = {"coef": dict(zip([n if n != "siege_style" else "siege_style_sum" for n in names_b], np.round(bpt, 4))),
                           **{s_: {"n": int((BASE.split == s_).sum()), "logloss": push_ll(BASE[BASE.split == s_], bpt)} for s_ in ["train", "test", "worlds"]}}
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
    return base if not full else np.c_[base, (d.gd.abs() / 1000).clip(0, 15), d.mon_up, d.buff, d.pace_s]
tr = Fp[Fp.split == "train"]; bf = pois_fit(Xf(tr), tr.y.values); b0 = pois_fit(Xf(tr, False), tr.y.values)
res["fights"] = {"coef": dict(zip(["intercept", *[f"phase {p}" for p in PHN[1:]], "per_1k_abs_lead", "monster_up", "buff_up", "pace_style"], np.round(bf, 4))),
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
json.dump(res, open(os.path.join(OUT, "rates3_results.json"), "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))
