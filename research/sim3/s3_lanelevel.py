"""Lane-level play, first measurement (12 Nov, read-only): how well do each lane's own players and champions predict
that lane's early game? Nothing here feeds the sim yet.
Lanes: top, jng, mid, and the bot duo (bot + sup together).
Events (major games, the file; blue minus red): the lane's gold lead at 15; the lane's kills minus deaths by 15;
for the bot duo also first dragon.
Inputs (all known before the game; every input stays in, none is dropped for being small):
  z            v1's pre-game log-odds (team + players)
  skill        the lane's session 1 lane skill gap (as s3_lanes.py; from lanes3_features.csv)
  champ gold   champion lane value gap, gold at 15 (as s3_lanes.py; training games only)
  champ kd     the same for kills minus deaths by 15 (training games only, pulled toward 0 with k = 20 as s3_lanes.py)
  strength     champion-role result minus v1's expected, earlier games (as s3_roleevents.py)
  comfort      log(1 + the player's earlier games on the champion) (as s3_roleevents.py)
  synergy, together   bot duo only: ADC + support champion pair, and games played together (as s3_roleevents.py)
Three models per event, plain least squares (logistic for first dragon), fitted on games before 1 Sep:
  A  z only      B  z + skill + champ gold (what the sim's laning uses now)      C  every input
Scored on training games, from 1 Sep, and Worlds: share of the spread explained (R2 against the training average).
usage: python -I s3_lanelevel.py <OE csv> v1_games.csv lanes3_features.csv <out_json> [tl_match.csv tl_events.csv <fit_json> <features_csv>]

With the four extra arguments it also writes the fits for the sim's lane-level option (cal["lane_level"] = "on"; s3_test.py ... ll):
  fit_json      per role: the gold lead at 15 from z, every lane input (bot and sup also get the duo's synergy and time
                together) AND the early events that move gold: the role's own kills, deaths and assists by 15 (blue minus
                red), so in the sim a kill moves the lane's gold by its fitted worth. Plates (version 3, 12 Nov): a second
                stage on the timeline games only (the file has no plates by lane or time; its turretplates is the whole game's
                count): what stage 1 leaves unexplained, on the plates taken before 15:00 in the role's own lane and in the
                other lanes (jungle: any lane). The leftover spread is then measured on those timeline games;
                how the five lanes' leftover leads move together (training games only); the same model without the events
                (the lane's expected lead before the game); and the early-kill lean: for kills before 15:00 in the timelines,
                which role on the killing side gets the kill and which role on the other side dies, against that role's
                expected lead before the game (one role-choice model each: role shares + one lean)
  features_csv  per game and role: m0 = the fitted lead without the z and event terms (the sim adds those itself);
                e0 = the expected lead before the game without its z term
S3_CUTOFF (date) = fit on games before it (default 1 Sep), as the other fit scripts."""
import os, sys, json
from collections import defaultdict
import numpy as np
import pandas as pd

CSV, V1, LF, OUT = sys.argv[1:5]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}; ROLES = ["top", "jng", "mid", "bot", "sup"]
CUT = os.environ.get("S3_CUTOFF", "2026-09-01"); K = 20
c = ["gameid", "league", "date", "side", "position", "playerid", "champion", "result", "golddiffat15", "killsat15", "deathsat15", "assistsat15", "turretplates", "firstdragon"]
raw = pd.read_csv(CSV, low_memory=False, usecols=c)
raw = raw[~((raw.league == "WLDs") & (raw.date < "2026-10-01"))].copy(); raw["day"] = raw.date.str[:10]
v1 = pd.read_csv(V1).set_index("gameid")
PL = raw[raw.position.isin(ROLES)].copy(); TM = raw[raw.position == "team"]
PL["p"] = PL.gameid.map(v1.p_v1); PL.loc[PL.side == "Red", "p"] = 1 - PL.loc[PL.side == "Red", "p"]

# pre-game history inputs, built day by day from earlier days only (same definitions as s3_roleevents.py)
comf = defaultdict(int); tog = defaultdict(int); st_s = defaultdict(float); st_n = defaultdict(int); sy_s = defaultdict(float); sy_n = defaultdict(int)
feat = {}
for day, dd in PL.groupby("day", sort=True):
    sides = [(k, x.set_index("position")) for k, x in dd.groupby(["gameid", "side"])]
    sides = [(k, x) for k, x in sides if set(ROLES) <= set(x.index) and x.index.is_unique]
    for (g, s), x in sides:
        f = {}
        for r in ROLES:
            pid, ch = x.at[r, "playerid"], x.at[r, "champion"]
            f[f"comfort_{r}"] = np.log1p(comf[(pid, ch)]) if pid == pid else np.nan
            f[f"strength_{r}"] = st_s[(ch, r)] / (st_n[(ch, r)] + 100)
        pa, pb = x.at["bot", "playerid"], x.at["sup", "playerid"]
        f["together"] = np.log1p(tog[frozenset((pa, pb))]) if pa == pa and pb == pb else np.nan
        k = (x.at["bot", "champion"], x.at["sup", "champion"]); f["synergy"] = sy_s[k] / (sy_n[k] + 30)
        feat[(g, s)] = f
    for (g, s), x in sides:
        for r in ROLES:
            pid, ch = x.at[r, "playerid"], x.at[r, "champion"]
            if pid == pid: comf[(pid, ch)] += 1
            if x.at[r, "p"] == x.at[r, "p"]: st_s[(ch, r)] += x.at[r, "result"] - x.at[r, "p"]; st_n[(ch, r)] += 1
        pa, pb = x.at["bot", "playerid"], x.at["sup", "playerid"]
        if pa == pa and pb == pb: tog[frozenset((pa, pb))] += 1
        if x.at["bot", "p"] == x.at["bot", "p"]:
            k = (x.at["bot", "champion"], x.at["sup", "champion"]); sy_s[k] += x.at["bot", "result"] - x.at["bot", "p"]; sy_n[k] += 1
F = pd.DataFrame.from_dict(feat, orient="index"); F.index = pd.MultiIndex.from_tuples(F.index, names=["gameid", "side"])
D = F.xs("Blue", level="side") - F.xs("Red", level="side").reindex(F.xs("Blue", level="side").index)

lf = pd.read_csv(LF)
games = lf[lf.position == "top"].set_index("gameid")[["day", "league", "z_v1"]]
G = games.rename(columns={"z_v1": "z"}).copy()
for r in ROLES:
    q = lf[lf.position == r].set_index("gameid")
    G[f"skill_{r}"] = q.skill_gap; G[f"cgold_{r}"] = q.cg15; G[f"gd_{r}"] = q.gd15
P2 = PL[PL.gameid.isin(G.index)].copy(); P2["kd"] = P2.killsat15 - P2.deathsat15
kdb = P2[P2.side == "Blue"].pivot_table(index="gameid", columns="position", values="kd")
kdr = P2[P2.side == "Red"].pivot_table(index="gameid", columns="position", values="kd")
chb = P2[P2.side == "Blue"].pivot_table(index="gameid", columns="position", values="champion", aggfunc="first")
chr_ = P2[P2.side == "Red"].pivot_table(index="gameid", columns="position", values="champion", aggfunc="first")
TR = G.day < CUT
for r in ROLES:
    G[f"kd_{r}"] = (kdb[r] - kdr[r]).reindex(G.index)
    # champion kills-minus-deaths value from training games, each champion's own side of the lane
    x = pd.concat([pd.DataFrame({"c": chb[r].reindex(G.index)[TR], "v": G[f"kd_{r}"][TR]}),
                   pd.DataFrame({"c": chr_[r].reindex(G.index)[TR], "v": -G[f"kd_{r}"][TR]})]).dropna()
    g = x.groupby("c").v.agg(["sum", "count"]); cv = (g["sum"] / (g["count"] + K)).to_dict()
    G[f"ckd_{r}"] = [cv.get(a, 0) - cv.get(b, 0) for a, b in zip(chb[r].reindex(G.index), chr_[r].reindex(G.index))]
G = G.join(D.reindex(G.index))
G["fd"] = TM[TM.side == "Blue"].set_index("gameid").firstdragon.reindex(G.index)
for a in ["gd", "kd"]: G[f"{a}_duo"] = G[f"{a}_bot"] + G[f"{a}_sup"]

LANES = {"top": ["top"], "jng": ["jng"], "mid": ["mid"], "duo": ["bot", "sup"]}
def inputs(lane, model, ev):
    rs = LANES[lane]
    if model == "A": return []
    cols = [f"skill_{r}" for r in rs] + [f"cgold_{r}" for r in rs]
    if model == "C":
        cols += [f"ckd_{r}" for r in rs] + [f"strength_{r}" for r in rs] + [f"comfort_{r}" for r in rs]
        if lane == "duo": cols += ["synergy", "together"]
    return cols
def lfit(X, y, l2=1e-6):
    bb = np.zeros(X.shape[1])
    for _ in range(60):
        p = 1 / (1 + np.exp(-X @ bb)); bb += np.linalg.solve(X.T @ (X * (p * (1 - p))[:, None]) + l2 * np.eye(len(bb)), X.T @ (y - p) - l2 * bb)
    return bb
ll = lambda p, y: float(-np.mean(y * np.log(np.clip(p, 1e-6, 1 - 1e-6)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1))))

res = {"cutoff": CUT, "events": {}}
tests = [(l, e) for l in LANES for e in ["gd", "kd"]] + [("duo", "fd")]
for lane, ev in tests:
    yc = "fd" if ev == "fd" else f"{ev}_{lane}"
    allc = inputs(lane, "C", ev)
    d = G.dropna(subset=[yc, "z"] + allc)  # the same games for all three models
    tr = d[d.day < CUT]; sets = {"train": tr, "from 1 Sep": d[d.day >= CUT], "Worlds": d[(d.day >= CUT) & (d.league == "WLDs")]}
    out = {"n": {k: len(v) for k, v in sets.items()}, "sd_train": round(float(tr[yc].std()), 3), "models": {}}
    for m in "ABC":
        cols = inputs(lane, m, ev); sd = tr[cols].std().replace(0, 1) if cols else None
        X = lambda q: np.c_[np.ones(len(q)), q.z] if not cols else np.c_[np.ones(len(q)), q.z, (q[cols] / sd).values]
        o = {}
        if ev == "fd":
            b = lfit(X(tr), tr[yc].values)
            for nm, q in sets.items(): o[nm] = round(ll(1 / (1 + np.exp(-X(q) @ b)), q[yc].values), 4)
            o["measure"] = "log loss (lower is better)"
        else:
            b, *_ = np.linalg.lstsq(X(tr), tr[yc], rcond=None); base = tr[yc].mean()
            for nm, q in sets.items(): o[nm] = round(float(1 - ((q[yc] - X(q) @ b) ** 2).sum() / ((q[yc] - base) ** 2).sum()), 4)
            o["measure"] = "R2 (share of spread explained; higher is better)"
        o["weights_per_sd"] = {k: round(float(v), 3) for k, v in zip(["const", "z"] + cols, b)}
        out["models"][m] = o
    if ev != "fd": out["corr_gold_with_kd"] = round(float(d[f"gd_{lane}"].corr(d[f"kd_{lane}"])), 3)
    res["events"][f"{lane} {ev}"] = out
json.dump(res, open(OUT, "w"), indent=1)
for k, v in res["events"].items():
    print(k, v["n"], "sd", v["sd_train"], "corr gold-kd", v.get("corr_gold_with_kd"))
    for m in "ABC": print("  ", m, {s: v["models"][m][s] for s in ["train", "from 1 Sep", "Worlds"]})
    print("   C weights", v["models"]["C"]["weights_per_sd"])

if len(sys.argv) > 8:
    TMF, TEF, FITJ, FEATC = sys.argv[5:9]
    HIST = [c_ for c_ in G.columns if c_.startswith(("comfort_", "strength_")) or c_ in ("synergy", "together")]
    G[HIST] = G[HIST].fillna(0)  # no earlier history for a player: no gap
    piv = lambda col: (P2[P2.side == "Blue"].pivot_table(index="gameid", columns="position", values=col)
                       - P2[P2.side == "Red"].pivot_table(index="gameid", columns="position", values=col)).reindex(G.index)
    Kd, Dd, Ad = piv("killsat15"), piv("deathsat15"), piv("assistsat15")
    # plates before 15:00 by lane, blue minus red (timeline games only)
    tm_ = pd.read_csv(TMF, dtype={"gid": str}).dropna(subset=["gameid"]); tm_ = tm_[tm_.gameid.isin(G.index)]
    pe = pd.read_csv(TEF, dtype={"gid": str}); pe = pe[(pe.type == "plate") & (pe.t < 900) & pe.gid.isin(tm_.gid)]
    PLD = pe.assign(sg=np.where(pe.side == "blue", 1.0, -1.0)).pivot_table(index="gid", columns="detail", values="sg", aggfunc="sum").reindex(tm_.gid).fillna(0.0)
    PLD.index = tm_.gameid.values; PLD = PLD.reindex(columns=["TOP", "MID", "BOT"]).fillna(0.0); PLD = PLD[~PLD.index.duplicated()]
    OWN = {"top": "TOP", "jng": None, "mid": "MID", "bot": "BOT", "sup": "BOT"}
    def plate_x(r, idx):  # own-lane and other-lane plate gaps for a role (jungle: one column, any lane)
        q = PLD.reindex(idx); tot = q.sum(axis=1)
        return np.c_[tot.values] if OWN[r] is None else np.c_[q[OWN[r]].values, (tot - q[OWN[r]]).values]
    for r in ROLES: G[f"ev_k_{r}"] = Kd[r]; G[f"ev_d_{r}"] = Dd[r]; G[f"ev_a_{r}"] = Ad[r]
    fit = {"cutoff": CUT, "inputs": {}, "coef": {}, "coef_pregame": {}, "event_gold": {}, "r2": {}, "r2_pregame": {}, "plates": {}}
    resid = {}; M0 = pd.DataFrame(index=G.index)
    for r in ROLES:
        cols = [f"skill_{r}", f"cgold_{r}", f"ckd_{r}", f"strength_{r}", f"comfort_{r}"] + (["synergy", "together"] if r in ("bot", "sup") else [])
        evc = [f"ev_k_{r}", f"ev_d_{r}", f"ev_a_{r}"]
        d = G.dropna(subset=[f"gd_{r}", "z"] + evc); tr = d[d.day < CUT]; base = tr[f"gd_{r}"].mean()
        sets = [("train", tr), ("from cutoff", d[d.day >= CUT]), ("Worlds", d[(d.day >= CUT) & (d.league == "WLDs")])]
        r2 = lambda X, b: {nm: round(float(1 - ((q[f"gd_{r}"] - X(q) @ b) ** 2).sum() / ((q[f"gd_{r}"] - base) ** 2).sum()), 4) for nm, q in sets if len(q)}
        X = lambda q: np.c_[np.ones(len(q)), q.z, q[cols].values, q[evc].values]   # with the events
        X0 = lambda q: np.c_[np.ones(len(q)), q.z, q[cols].values]                 # before the game
        b, *_ = np.linalg.lstsq(X(tr), tr[f"gd_{r}"], rcond=None); b0, *_ = np.linalg.lstsq(X0(tr), tr[f"gd_{r}"], rcond=None)
        nc = len(cols)
        fit["inputs"][r] = cols; fit["coef"][r] = {"const": float(b[0]), "z": float(b[1]), **{c_: float(v) for c_, v in zip(cols, b[2:2 + nc])}}
        # stage 2 (timeline games): the plates before 15:00. Plates go with the stage 1 inputs (stronger teams and lanes with kills take
        # more of them), so stage 1's weights already hold part of what plates do. Paying plates on top of those weights counted that part
        # twice (first run, 12 Nov: the sim's team lead at 15 followed team strength 1,441 gold per unit against 748 real). So: the plates'
        # own worth is fitted on the part of the plate gap the stage 1 inputs don't predict, and the stage 1 weights give back the share
        # that belongs to plates (the usual two-step form of fitting everything together).
        dt = d[d.index.isin(PLD.index)]; r1 = dt[f"gd_{r}"].values - X(dt) @ b; Xp = plate_x(r, dt.index); ttr = (dt.day < CUT).values
        Gm, *_ = np.linalg.lstsq(X(dt)[ttr], Xp[ttr], rcond=None)   # plate gap predicted from the stage 1 inputs
        b2, *_ = np.linalg.lstsq((Xp - X(dt) @ Gm)[ttr], r1[ttr], rcond=None)
        b_stage1 = b; b = b - Gm @ b2
        fit["coef"][r] = {"const": float(b[0]), "z": float(b[1]), **{c_: float(v) for c_, v in zip(cols, b[2:2 + nc])}}
        own_v, oth_v = float(b2[0]), float(b2[-1])
        fit["event_gold"][r] = {"own_kill": float(b[2 + nc]), "own_death": float(b[3 + nc]), "own_assist": float(b[4 + nc]), "own_lane_plate": own_v, "other_lane_plate": oth_v}
        sc_ = lambda msk, pred: round(float(1 - ((dt[f"gd_{r}"].values[msk] - pred[msk]) ** 2).sum() / ((dt[f"gd_{r}"].values[msk] - base) ** 2).sum()), 4) if msk.sum() else None
        p1 = X(dt) @ b_stage1; p2 = X(dt) @ b + Xp @ b2; wl = (dt.league == "WLDs").values
        fit["plates"][r] = {"n_train": int(ttr.sum()), "n_from_cutoff": int((~ttr).sum()),
                            "r2_timeline_games": {"train": {"no plates": sc_(ttr, p1), "with plates": sc_(ttr, p2)}, "from cutoff": {"no plates": sc_(~ttr, p1), "with plates": sc_(~ttr, p2)},
                                                  "Worlds": {"no plates": sc_(~ttr & wl, p1), "with plates": sc_(~ttr & wl, p2)}}}
        fit["coef_pregame"][r] = {"const": float(b0[0]), "z": float(b0[1]), **{c_: float(v) for c_, v in zip(cols, b0[2:])}}
        fit["r2"][r] = r2(X, b); fit["r2_pregame"][r] = r2(X0, b0)
        resid[r] = pd.Series((dt[f"gd_{r}"].values - p2)[ttr], index=dt.index[ttr])  # leftover after the plates, timeline training games
        M0[f"m0_{r}"] = b[0] + G[cols].values @ b[2:2 + nc]; M0[f"e0_{r}"] = b0[0] + G[cols].values @ b0[2:]
        G[f"exp_{r}"] = M0[f"e0_{r}"] + b0[1] * G.z
    R15 = pd.DataFrame(resid).dropna()[ROLES]
    fit["cov15"] = R15.cov().round(0).values.tolist(); fit["resid_corr15"] = R15.corr().round(3).values.tolist()
    fit["resid_sd15"] = [round(float(v)) for v in R15.std()]
    # early-kill lean (timelines): killer role among the killing side's five, victim role among the other side's five,
    # against each role's expected lead before the game (so nothing in the sim looks ahead at the lane's result)
    key = lambda s_: "".join(ch for ch in str(s_).lower() if ch.isalnum())
    tm = pd.read_csv(TMF, dtype={"gid": str}).dropna(subset=["gameid"]); tm = tm[tm.gameid.isin(G.index)]
    ev = pd.read_csv(TEF, dtype={"gid": str}); ev = ev[(ev.type == "kill") & (ev.t < 900) & ev.gid.isin(tm.gid)]
    ev = ev.merge(tm[["gid", "gameid"]], on="gid")
    pm = PL[PL.gameid.isin(tm.gameid)]; role_of = {(g, s.lower(), key(c_)): ROLES.index(p_) for g, s, c_, p_ in zip(pm.gameid, pm.side, pm.champion, pm.position)}
    rows = []
    for e in ev.itertuples():
        o = "red" if e.side == "blue" else "blue"
        k_ = role_of.get((e.gameid, e.side, key(e.champ))); v_ = role_of.get((e.gameid, o, key(e.victim_champ)))
        lead = np.array([G.at[e.gameid, f"exp_{r}"] for r in ROLES], float) / 1000
        if np.isnan(lead).any(): continue
        sg = 1 if e.side == "blue" else -1
        rows.append((e.gameid, G.at[e.gameid, "day"], G.at[e.gameid, "league"], k_, v_, *(sg * lead)))  # expected leads, killing side's view
    KL = pd.DataFrame(rows, columns=["gameid", "day", "league", "killer", "victim"] + ROLES)
    def clogit(ch, L):  # choice among 5 roles: role intercepts (top = 0) + lean * that role's expected lead
        par = np.zeros(5); Y = np.eye(5)[ch]
        for _ in range(40):
            u = np.r_[0, par[:4]][None, :] + par[4] * L; pr = np.exp(u - u.max(1, keepdims=True)); pr /= pr.sum(1, keepdims=True)
            Xd = np.concatenate([np.repeat(np.eye(5)[None, :, 1:], len(L), 0), L[:, :, None]], axis=2)  # n x 5 alternatives x 5 params
            g_ = ((Y - pr)[:, :, None] * Xd).sum((0, 1)); xb = (pr[:, :, None] * Xd).sum(1)
            H = np.einsum("ni,nij,nik->jk", pr, Xd, Xd) - xb.T @ xb
            par = par + np.linalg.solve(H + 1e-8 * np.eye(5), g_)
        return par
    def cl_ll(par, ch, L):
        u = np.r_[0, par[:4]][None, :] + par[4] * L; pr = np.exp(u - u.max(1, keepdims=True)); pr /= pr.sum(1, keepdims=True)
        return round(float(-np.mean(np.log(pr[np.arange(len(ch)), ch]))), 4)
    fit["kill_role"] = {"kills_before_15": int(len(KL)), "killer_matched": int(KL.killer.notna().sum()), "victim_matched": int(KL.victim.notna().sum())}
    for who, sgn in [("killer", 1.0), ("victim", -1.0)]:
        d = KL.dropna(subset=[who]); ch = d[who].astype(int).values; L = sgn * d[ROLES].values  # victim: leads from the dying side's own view
        trm = (d.day < CUT).values; par = clogit(ch[trm], L[trm]); shares = np.bincount(ch[trm], minlength=5) / trm.sum()
        flat = np.r_[np.log(shares[1:] / shares[0]), 0.0]
        out = {"role_intercepts": [0.0] + [float(v) for v in par[:4]], "lean_per_1k_expected_lead": float(par[4]), "n_train": int(trm.sum()),
               "train_share": [round(float(v), 4) for v in shares], "logloss": {}}
        for nm, msk in [("train", trm), ("from cutoff", ~trm), ("Worlds", (~trm) & (d.league == "WLDs").values)]:
            if msk.sum(): out["logloss"][nm] = {"n": int(msk.sum()), "role shares only": cl_ll(flat, ch[msk], L[msk]), "with lean": cl_ll(par, ch[msk], L[msk])}
        fit["kill_role"][who] = out
    json.dump(fit, open(FITJ, "w"), indent=1)
    M0.round(2).to_csv(FEATC, index_label="gameid")
    for r in ROLES: print(r, "plates", fit["plates"][r])
    for r in ROLES: print(r, "with events", fit["r2"][r], "| before the game", fit["r2_pregame"][r], "| event gold", {k: round(v) for k, v in fit["event_gold"][r].items()}, "| z", round(fit["coef"][r]["z"]), "v", round(fit["coef_pregame"][r]["z"]))
    print("leftover sd", fit["resid_sd15"]); print("leftover corr", fit["resid_corr15"])
    for w in ("killer", "victim"): print(w, round(fit["kill_role"][w]["lean_per_1k_expected_lead"], 3), fit["kill_role"][w]["logloss"])
