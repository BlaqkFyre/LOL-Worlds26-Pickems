"""Sim session 3, steps 4-5 (read-only): what happens minute by minute, from gol.gg timelines matched to the file.
For every matched game and minute: the gold lead at the start of the minute (team and per role, from gol.gg's per-minute
gold), v1's pre-game log-odds, and what happened in that minute. Fitted from this:
  fights     kills grouped into fights (a gap of 20 s+ starts a new fight); how often a fight starts per minute by game
             phase and state; how many die; who wins it (gold lead, v1 strength, buffs)
  gold       what each event is worth to the gold lead (regression of the minute's change in gold lead on its events)
  objectives first spawn, the wait from spawn to take, and who takes it (gold lead, jungle and lane leads, side, v1)
  towers     how often a tower falls per minute by phase, which lane, who takes it
  ending     how often the game ends in a minute once an inhibitor is down (by gold lead and Baron buff)
Fit on games before 1 Sep; judged on games from 1 Sep (log loss / counts). Worlds shown on its own.
Draft style (s3_comp.py, champion styles from games before 1 Sep): objectives (blue minus red draft) in who takes each
monster; skirmish (blue minus red) in who wins kills before 15:00.
usage: python -I s3_events.py tl_match.csv tl_games.csv tl_events.csv tl_gold.csv v1_games.csv <out_dir> comp3_games.csv"""
import os, sys, json
import numpy as np
import pandas as pd

TM, TG, TE, TGo, V1, OUT = sys.argv[1:7]; os.makedirs(OUT, exist_ok=True)
ROLES = ["top", "jng", "mid", "bot", "sup"]
M = pd.read_csv(TM, dtype={"gid": str}); M = M[M.gameid.notna() & (M.gameid != "AMBIGUOUS")]
M = M.drop_duplicates("gameid")
v1 = pd.read_csv(V1).set_index("gameid")
M["z"] = M.gameid.map(v1.z_v1); M["league"] = M.gameid.map(v1.league)
M = M[M.z.notna()].copy()
comp = pd.read_csv(sys.argv[7]).set_index("gameid")
M["obj_d"] = M.gameid.map(comp.objectives_blue - comp.objectives_red).fillna(0)
M["skirm_d"] = M.gameid.map(comp.skirmish_blue - comp.skirmish_red).fillna(0)
M["split"] = np.where(M.date < "2026-09-01", "train", "test"); M.loc[M.tournament.str.startswith("Worlds"), "split"] = "worlds"
ev = pd.read_csv(TE, dtype={"gid": str}); ev = ev[ev.gid.isin(M.gid)].copy()
go = pd.read_csv(TGo, dtype={"gid": str}); go = go[go.gid.isin(M.gid) & (go.kind == "gold")]
sgn = np.where(go.side == "blue", 1, -1)
go["sv"] = go.value * sgn
GDm = go.groupby(["gid", "minute"]).sv.sum()                       # team gold lead (blue - red) at minute
RDm = go.pivot_table(index=["gid", "minute"], columns="role", values="sv", aggfunc="sum")  # per-role lead
sp = lambda g: M.set_index("gid").loc[g]
info = M.set_index("gid")
res = {"games": M.split.value_counts().to_dict()}
lg = lambda p, y: float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

def logit_fit(X, y, l2=1.0, it=50):
    b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + l2 * np.eye(len(b)); g = X.T @ (y - p) - l2 * b
        b += np.linalg.solve(H, g)
    return b

# ---------- minute panel ----------
ev["m"] = ev.t // 60
rows = []
for g, gi in info.iterrows():
    L = int(gi.len) // 60
    e = ev[ev.gid == g]
    for m in range(0, L + 1):
        gd = GDm.get((g, m), np.nan)
        rows.append((g, m, gd))
P = pd.DataFrame(rows, columns=["gid", "m", "gd"])
P = P.join(RDm, on=["gid", "m"])
P["z"] = P.gid.map(info.z); P["split"] = P.gid.map(info.split)

# ---------- fights ----------
K = ev[ev.type == "kill"].sort_values(["gid", "t"]).copy()
K["new"] = (K.groupby("gid").t.diff().fillna(999) > 20).astype(int)
K["fight"] = K.groupby("gid").new.cumsum()
F = K.groupby(["gid", "fight"]).agg(t=("t", "min"), t_end=("t", "max"), n=("t", "size"),
                                     blue=("side", lambda s: int((s == "blue").sum()))).reset_index()
F["red"] = F.n - F.blue; F["m"] = F.t // 60
F = F.merge(P[["gid", "m", "gd", "jng", "mid", "z", "split"]], on=["gid", "m"], how="left")
# buffs active at the fight: Baron (3 min) / Elder (2.5 min) by side
def buff(g, t, typ, dur):
    e = ev[(ev.gid == g) & (ev.type == typ) & (ev.t <= t) & (ev.t > t - dur)]
    if typ == "dragon": e = e[e.detail == "elder"]
    return (int((e.side == "blue").any()) - int((e.side == "red").any()))
BAR = ev[ev.type == "baron"]; DRA = ev[ev.type == "dragon"]
def buffs(df):
    b, el = [], []
    for r in df.itertuples():
        x = BAR[(BAR.gid == r.gid) & (BAR.t <= r.t) & (BAR.t > r.t - 180)]
        b.append(int((x.side == "blue").any()) - int((x.side == "red").any()))
        y = DRA[(DRA.gid == r.gid) & (DRA.detail == "elder") & (DRA.t <= r.t) & (DRA.t > r.t - 150)]
        el.append(int((y.side == "blue").any()) - int((y.side == "red").any()))
    df["baron"] = b; df["elder"] = el
    return df
F = buffs(F)
F["phase"] = pd.cut(F.m, [-1, 13, 24, 34, 999], labels=["0-13", "14-24", "25-34", "35+"])
res["fight_size"] = {str(k): v for k, v in F.n.value_counts(normalize=True).sort_index().round(4).items()}
res["fight_size_table"] = {str(ph): {str(k): round(float(v), 4) for k, v in d.n.clip(upper=8).value_counts(normalize=True).sort_index().items()}
                           for ph, d in F.groupby("phase", observed=True)}
mf = F[F.n >= 2]
res["two_sided_share_by_size"] = {str(k): round(float(((d.blue > 0) & (d.red > 0)).mean()), 3) for k, d in mf.groupby(mf.n.clip(upper=6))}
res["fight_size_by_phase"] = F.groupby("phase", observed=True).n.agg(["mean", "count"]).round(3).to_dict()
# fights per minute by phase (exposure = minutes played in that phase)
P["phase"] = pd.cut(P.m, [-1, 13, 24, 34, 999], labels=["0-13", "14-24", "25-34", "35+"])
fpm = F.groupby(["phase"], observed=True).size() / P.groupby("phase", observed=True).size()
res["fights_per_minute"] = fpm.round(4).to_dict()
# per-minute fight rate by minute (smoothed shape for the sim)
fr = (F.groupby("m").size() / P.groupby("m").size()).fillna(0)
res["fights_per_minute_by_minute"] = fr.loc[0:45].round(4).to_dict()
# fight winner: share of the fight's kills won by blue ~ gold lead, v1, buffs (binomial on kills)
Fw = F.dropna(subset=["gd"]).copy()
Fw["skirm_early"] = Fw.gid.map(info.skirm_d) * (Fw.m < 15)
def Xf(d): return np.c_[np.ones(len(d)), d.gd / 1000, d.z, d.baron, d.elder, d.skirm_early]
yk = np.r_[np.ones(int(Fw.blue.sum())), np.zeros(int(Fw.red.sum()))]
Xk = np.r_[np.repeat(Xf(Fw), Fw.blue.values.astype(int), axis=0), np.repeat(Xf(Fw), Fw.red.values.astype(int), axis=0)]
spl = np.r_[np.repeat(Fw.split.values, Fw.blue.values.astype(int)), np.repeat(Fw.split.values, Fw.red.values.astype(int))]
tr = spl == "train"; bk = logit_fit(Xk[tr], yk[tr])
res["kill_side"] = {"coef": dict(zip(["intercept", "per_1k_gold_lead", "per_v1_logit", "baron", "elder", "skirmish_style_early"], np.round(bk, 4))),
                    **{s: {"n": int((spl == s).sum()), "logloss": round(lg(1 / (1 + np.exp(-Xk[spl == s] @ bk)), yk[spl == s]), 4),
                           "base": round(lg(np.full((spl == s).sum(), yk[tr].mean()), yk[spl == s]), 4)} for s in ["train", "test", "worlds"]}}
# timing-only version: no draft term in who gets the kill
bkt = logit_fit(Xk[tr][:, :5], yk[tr])
res["kill_side_timing"] = {"coef": dict(zip(["intercept", "per_1k_gold_lead", "per_v1_logit", "baron", "elder"], np.round(bkt, 4))),
                           **{s_: {"n": int((spl == s_).sum()), "logloss": round(lg(1 / (1 + np.exp(-Xk[spl == s_][:, :5] @ bkt)), yk[spl == s_]), 4)}
                              for s_ in ["train", "test", "worlds"]}}
# within-game version: the pooled gold-lead effect partly reflects "this team is stronger in this game" (beyond v1). Fit with a
# separate baseline per game (game dummies, ridge 1), training games; the game effects' spread minus their noise = game form
_gid = np.r_[np.repeat(Fw.gid.values, Fw.blue.values.astype(int)), np.repeat(Fw.gid.values, Fw.red.values.astype(int))]
_tg = pd.Index(sorted(set(_gid[tr]))); _gi = _tg.get_indexer(_gid[tr])
_D = np.zeros((tr.sum(), len(_tg))); _D[np.arange(tr.sum()), _gi] = 1
_X = np.c_[Xk[tr][:, :5], _D]; _l2 = np.r_[1e-3, 1, 1, 1, 1, np.ones(len(_tg))]
bw = np.zeros(_X.shape[1])
for _ in range(40):
    _p = 1 / (1 + np.exp(-_X @ bw)); _W = _p * (1 - _p)
    bw += np.linalg.solve(_X.T @ (_X * _W[:, None]) + np.diag(_l2), _X.T @ (yk[tr] - _p) - _l2 * bw)
_fe = bw[5:]; _info = np.array([(_W[_gi == j]).sum() for j in range(len(_tg))])
_v = float(np.var(_fe) - np.mean(1 / (_info + 1)))
res["kill_side_within"] = {"coef": dict(zip(["intercept", "per_1k_gold_lead", "per_v1_logit", "baron", "elder"], np.round(bw[:5], 4))),
                           "game_form_sd": round(float(np.sqrt(max(_v, 0.0))), 4), "games": len(_tg),
                           "note": "per_v1_logit is not identified within a game (v1 is constant in a game); the sim keeps the pooled v1 term"}
# fights cluster around objectives: share of fights starting within 60 s before an epic monster take
OBJ = ev[ev.type.isin(["dragon", "baron", "herald", "grub"])]
near = []
for r in F.itertuples():
    o = OBJ[(OBJ.gid == r.gid) & (OBJ.t >= r.t) & (OBJ.t <= r.t + 60)]
    near.append(o.type.iloc[0] if len(o) else "")
F["near_obj"] = near
res["fights_near_objective"] = F.near_obj.replace("", "none").value_counts(normalize=True).round(3).to_dict()

# ---------- gold per event ----------
cnt = ev.assign(v=np.where(ev.side == "blue", 1, -1)).pivot_table(index=["gid", "m"], columns="type", values="v", aggfunc="sum", fill_value=0)
Q = P.join(cnt, on=["gid", "m"]).fillna({c: 0 for c in cnt.columns})
Q["gd_next"] = Q.groupby("gid").gd.shift(-1); Q["dgd"] = Q.gd_next - Q.gd
Q = Q.dropna(subset=["dgd"])
Q["plate_early"] = np.where(Q.m < 14, Q.get("plate", 0), 0); Q["plate"] = Q.get("plate", 0) - Q.plate_early
Q["dragon_n"] = Q.get("dragon", 0)
ecol = [c for c in ["kill", "tower", "plate_early", "plate", "dragon_n", "grub", "herald", "baron", "inhib"] if c in Q.columns]
qt = Q[Q.split == "train"]
Xg = np.c_[np.ones(len(qt)), qt[ecol].values, qt.z.values]
bg, *_ = np.linalg.lstsq(Xg, qt.dgd.values, rcond=None)
res["gold_per_event"] = dict(zip(["drift", *ecol, "per_v1_logit_per_min"], np.round(bg, 1)))
res["gold_noise_sd_per_min"] = round(float(np.std(qt.dgd.values - Xg @ bg)), 1)
# lead decay / comeback: does the minute's change depend on the lead itself (bounties, catch-up)?
Xg2 = np.c_[Xg, qt.gd.values / 1000, (qt.gd.values / 1000) * (qt.m.values >= 20)]
bg2, *_ = np.linalg.lstsq(Xg2, qt.dgd.values, rcond=None)
res["gold_lead_feedback"] = {"per_1k_lead": round(float(bg2[-2]), 1), "extra_per_1k_after_20": round(float(bg2[-1]), 1)}
# how a minute's team gold swing lands on each role (slope of the role's change on the team's change), training games
RG = go.pivot_table(index=["gid", "minute"], columns="role", values="sv", aggfunc="sum").sort_index()
DG = RG.groupby(level=0).diff().dropna(); DG["team"] = DG[ROLES].sum(axis=1)
DG = DG[DG.index.get_level_values(0).map(info.split) == "train"]; mmin = DG.index.get_level_values(1)
res["gold_swing_share"] = {ph: {r: round(float(np.polyfit(q.team, q[r], 1)[0]), 4) for r in ROLES}
                           for ph, q in [("laning", DG[(mmin >= 1) & (mmin < 15)]), ("after", DG[mmin >= 15])]}

# ---------- objectives: spawn, wait, taker ----------
first = ev.groupby(["gid", "type"]).t.min().unstack()
res["first_take_time_s"] = {t: {"min": int(first[t].min()), "p10": int(first[t].quantile(.1)), "median": int(first[t].median()),
                                "p90": int(first[t].quantile(.9)), "share_games": round(float(first[t].notna().mean()), 3)}
                            for t in ["kill", "dragon", "grub", "herald", "baron", "tower", "inhib", "nexus"] if t in first}
OB = ev[ev.type.isin(["dragon", "grub", "herald", "baron"])].copy().sort_values(["gid", "t"])
OB["m"] = OB.t // 60
OB = OB.merge(P[["gid", "m", "gd", "top", "jng", "mid", "bot", "sup", "z", "split"]], on=["gid", "m"], how="left")
OB["blue"] = (OB.side == "blue").astype(int)
OB["elder"] = (OB.type == "dragon") & (OB.detail == "elder")
OB["kind"] = np.where(OB.elder, "elder", OB.type)
OB["bot2"] = OB.bot.fillna(0) + OB.sup.fillna(0)
KK = ev[ev.type == "kill"][["gid", "t", "side"]]
OB["net60"] = [int(((KK.gid == r.gid) & (KK.t <= r.t) & (KK.t > r.t - 60) & (KK.side == "blue")).sum()
                   - ((KK.gid == r.gid) & (KK.t <= r.t) & (KK.t > r.t - 60) & (KK.side == "red")).sum()) for r in OB.itertuples()]
OB["net60k"] = OB.net60 * 1000  # so the /1000 scaling below leaves it per kill
OB["objk"] = OB.gid.map(info.obj_d) * 1000  # draft objectives style, blue minus red
OB["objgd"] = OB.gid.map(info.obj_d) * OB.gd  # comps option A: objectives draft difference x gold lead (per 1k after /1000)
OB["first1k"] = 0
fdx = OB[OB.kind == "dragon"].sort_values("t").groupby("gid").head(1).index; OB.loc[fdx, "first1k"] = 1000  # the game's first dragon
# who takes each monster; "taker_timing" leaves the draft objective style out (timing-only draft styles)
for tkey, drop in [("taker", ()), ("taker_timing", ("objk",)), ("taker_A", ("objk",))]:
    res[tkey] = {}
    for kind, feats0 in [("dragon", ["gd", "jng", "bot2", "mid", "net60k", "objk", "first1k"]), ("grub", ["gd", "jng", "top", "mid", "net60k", "objk"]),
                        ("herald", ["gd", "jng", "top", "mid", "net60k", "objk"]), ("baron", ["gd", "net60k", "objk"]), ("elder", ["gd", "net60k", "objk"])]:
        feats = [f for f in feats0 if f not in drop] + (["objgd"] if tkey == "taker_A" else [])
        d = OB[(OB.kind == kind)].dropna(subset=["gd"])
        if kind == "grub": d = d.drop_duplicates(["gid", "m", "side"])
        X = lambda q: np.c_[np.ones(len(q)), q[feats].values / 1000, q.z.values]
        trd = d[d.split == "train"]
        if len(trd) < 30: continue
        b = logit_fit(X(trd), trd.blue.values, l2=2.0)
        out = {"coef": dict(zip(["blue_side", *[f + "_per_1k" for f in feats], "per_v1_logit"], np.round(b, 4)))}
        for s in ["train", "test", "worlds"]:
            q = d[d.split == s]
            if len(q): out[s] = {"n": len(q), "logloss": round(lg(1 / (1 + np.exp(-X(q) @ b)), q.blue.values), 4),
                                 "base": round(lg(np.full(len(q), trd.blue.mean()), q.blue.values), 4), "blue_share": round(float(q.blue.mean()), 3)}
        res[tkey][kind] = out
# dragon timing: wait from spawn (first at the earliest observed time, then 5 min after the last take) to take
SPAWN = {"dragon": int(first.dragon.min()) if "dragon" in first else 300}
wait = []
for g, d in OB[OB.kind.isin(["dragon", "elder"])].groupby("gid"):
    prev = None
    for r in d.itertuples():
        sp_ = SPAWN["dragon"] if prev is None else prev + 300 if r.kind == "dragon" else None
        if sp_ is not None and r.kind == "dragon": wait.append((g, r.Index, r.t - sp_, r.gd, r.bot2, r.jng, r.split, len(wait)))
        prev = r.t
W = pd.DataFrame(wait, columns=["gid", "i", "wait", "gd", "bot2", "jng", "split", "k"])
res["dragon_wait_s"] = {"n": len(W), "p10": int(W.wait.quantile(.1)), "median": int(W.wait.median()), "p90": int(W.wait.quantile(.9)),
                        "share_under_60s": round(float((W.wait < 60).mean()), 3),
                        "corr_abs_lead": round(float(W.wait.corr(W.gd.abs())), 3)}
gsp = ev[ev.type == "grub"].groupby(["gid", "side"]).size().unstack(fill_value=0)
res["grubs_split"] = {"games": len(gsp), "one_team_all": round(float(((gsp.min(axis=1) == 0)).mean()), 3),
                      "total_dist": gsp.sum(axis=1).value_counts(normalize=True).round(3).to_dict()}
dseq = ev[(ev.type == "dragon") & (ev.detail != "elder")].sort_values(["gid", "t"]).groupby("gid").detail.apply(list)
res["dragon_types"] = {"first_two_share": pd.Series([x for l in dseq for x in l[:2]]).value_counts(normalize=True).round(3).to_dict(),
                       "third_on_same_as_third": round(float(np.mean([all(y == l[2] for y in l[2:]) for l in dseq if len(l) >= 4])), 3),
                       "first_two_differ": round(float(np.mean([l[0] != l[1] for l in dseq if len(l) >= 2])), 3)}
# objectives by side: blue side's share of each (map side matters for dragon v Baron pit)
res["blue_share_by_objective"] = OB.groupby("kind").blue.agg(["mean", "size"]).round(3).to_dict()

# ---------- towers ----------
T = ev[ev.type == "tower"].copy()
T["tier"] = T.detail.str.extract(r"(T\d|NEXUS)", expand=False); T["lane"] = T.detail.str.extract(r"(TOP|MID|BOT)", expand=False)
T["m"] = T.t // 60
T = T.merge(P[["gid", "m", "gd", "z", "split"]], on=["gid", "m"], how="left")
res["towers"] = {"first_time_by_tier_s": T.groupby("tier").t.median().round(0).to_dict(),
                 "lane_share_of_first_tower": T.sort_values("t").groupby("gid").head(1).lane.value_counts(normalize=True).round(3).to_dict(),
                 "per_game": round(len(T) / len(M), 2)}
Tw = T.dropna(subset=["gd"]); Tw["blue"] = (Tw.side == "blue").astype(int)
X = lambda q: np.c_[np.ones(len(q)), q.gd / 1000, q.z]
b = logit_fit(X(Tw[Tw.split == "train"]), Tw[Tw.split == "train"].blue.values)
res["tower_taker"] = {"coef": dict(zip(["blue_side", "per_1k_gold_lead", "per_v1_logit"], np.round(b, 4))),
                      **{s: {"n": int((Tw.split == s).sum()), "logloss": round(lg(1 / (1 + np.exp(-X(Tw[Tw.split == s]) @ b)), Tw[Tw.split == s].blue.values), 4)}
                         for s in ["train", "test", "worlds"]}}
tpm = (T.groupby("m").size() / P.groupby("m").size()).fillna(0)
res["towers_per_minute_by_minute"] = tpm.loc[0:45].round(4).to_dict()

# ---------- ending ----------
NX = ev[ev.type == "nexus"].groupby("gid").t.min()
INH = ev[ev.type == "inhib"].groupby("gid").t.min()
res["ending"] = {"games_with_nexus_row": round(float(M.gid.isin(NX.index).mean()), 3),
                 "first_inhib_to_end_s": {"median": int((info.len - INH).dropna().median()), "p10": int((info.len - INH).dropna().quantile(.1)),
                                          "p90": int((info.len - INH).dropna().quantile(.9))},
                 "length_s": {s: {"median": int(info[info.split == s].len.median()), "p10": int(info[info.split == s].len.quantile(.1)),
                                  "p90": int(info[info.split == s].len.quantile(.9))} for s in ["train", "test", "worlds"]},
                 "games_without_inhib": round(float(1 - M.gid.isin(INH.index).mean()), 3)}
# who wins: gold lead at 15/20/25 -> result (how decisive leads are, for checks)
for mm in [15, 20, 25]:
    d = P[P.m == mm].dropna(subset=["gd"]).copy(); d["y"] = (d.gid.map(info.win) == "blue").astype(int)
    b = logit_fit(np.c_[np.ones(len(d)), d.gd / 1000, d.z][d.split == "train"], d.y[d.split == "train"].values)
    res.setdefault("lead_to_win", {})[f"@{mm}"] = {"per_1k": round(float(b[1]), 4), "per_v1_logit": round(float(b[2]), 4), "n": len(d)}

F.to_csv(os.path.join(OUT, "tl_fights.csv"), index=False)
json.dump(res, open(os.path.join(OUT, "events3_results.json"), "w"), indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
print(json.dumps(res, indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o)))
