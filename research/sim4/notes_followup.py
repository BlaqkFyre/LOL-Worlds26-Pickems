"""Luke's notes 2-4 (13 Nov 2026 AEST, his answers in chat), checked against the data. Read-only; no sim change (Luke: notes are a
reference, data and tests decide, ask before any code change).
 2  Long games (35+): the ADC and bot lane decide more; kills, objectives, Elder / Baron / dragons / inhibitors; an ADC killed takes
    the team's main damage away.
    a  file, all major games: by game length (under 28, 28-35, 35+), how much each role's deaths and kills go with winning, beyond v1
       (logistic per band: win ~ v1 log-odds + that role's death gap; then kill gap); the ADC's damage share by band
    b  timelines: fights by start time (under 25, 25-35, 35+): the side whose ADC dies first in a fight wins that fight how often, against
       fights where another role dies first; and how often the game ends within 3 minutes of such a fight
    c  file: win rate of the Elder team, the first-Baron team, the side with more dragons, by length band
 3  Comp type sets game length and decides mid and late game, against the opponent's type and strength.
    a  earlier tests (research/comps-plan.md): every draft style and outside scaling label failed held out; summarised, not redone
    b  new, pro-based scaling: each champion-role's result beyond v1 in long games (35+) minus short games (under 28), games before 1 Sep,
       pulled toward 0 (k = 30); a draft = sum of its five. Held out from 1 Sep: does the scaling gap go with winning long games more than
       short ones (logistic: win ~ v1 + gap x long + gap x short)? does the scaling sum go with game length?
 4  First dragon: side and comp matter; weak early comps or junglers can't contest without lane or bot pressure.
    a  the sim's fitted dragon-taker terms (params3.json), already in use
    b  file, held out from 1 Sep: first dragon ~ side + v1 + jungle, mid and bot-duo gold at 10 + draft early tempo (each champion-role's
       gold lead at 10, games before 1 Sep, k = 20)
usage (repo root): python -I research/sim4/notes_followup.py <OE csv> v1_games.csv tl_match.csv tl_events.csv params3.json <out_json>"""
import sys, json
import numpy as np, pandas as pd
CSV, V1, TMF, TEF, PJ, OUT = sys.argv[1:7]
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}; ROLES = ["top", "jng", "mid", "bot", "sup"]; CUT = "2026-09-01"
cols = ["gameid", "league", "date", "side", "position", "champion", "result", "gamelength", "kills", "deaths", "damageshare", "golddiffat10",
        "firstdragon", "dragons", "opp_dragons", "elders", "opp_elders", "firstbaron"]
raw = pd.read_csv(CSV, low_memory=False, usecols=cols)
raw = raw[raw.league.isin(MAJOR) & ~((raw.league == "WLDs") & (raw.date < "2026-10-01")) & (raw.date < "2026-11-10")].copy(); raw["day"] = raw.date.str[:10]
v1 = pd.read_csv(V1).set_index("gameid"); raw["z"] = raw.gameid.map(v1.z_v1); raw = raw.dropna(subset=["z"])
raw.loc[raw.side == "Red", "z"] *= -1
raw["mins"] = raw.gamelength / 60; raw["band"] = pd.cut(raw.mins, [0, 28, 35, 99], labels=["under 28", "28-35", "35+"], right=False)
pl = raw[raw.position.isin(ROLES)]; tm = raw[raw.position == "team"].copy()
def logit(X, y, it=50):
    b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); H = X.T @ (X * (p * (1 - p))[:, None]) + 1e-6 * np.eye(len(b)); b += np.linalg.solve(H, X.T @ (y - p))
    p = 1 / (1 + np.exp(-X @ b)); cov = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]) + 1e-6 * np.eye(len(b)))
    return b, np.sqrt(np.diag(cov))
R = {}
# ---- 2a ----
blue = pl[pl.side == "Blue"].set_index(["gameid", "position"]); red = pl[pl.side == "Red"].set_index(["gameid", "position"])
gap = (blue[["kills", "deaths"]] - red[["kills", "deaths"]]).unstack(); gap.columns = [f"{st}|{r}" for st, r in gap.columns]
g = tm[tm.side == "Blue"].set_index("gameid")[["result", "z", "band", "mins"]].join(gap, how="inner").dropna()
out = {}
for band in ["under 28", "28-35", "35+"]:
    d = g[g.band == band]; row = {"games": len(d)}
    for st in ["deaths", "kills"]:
        for r in ROLES:
            X = np.c_[np.ones(len(d)), d.z, d[f"{st}|{r}"]]; b, se = logit(X, d.result.values.astype(float))
            row[f"{r} {st} gap"] = f"{b[2]:+.3f} (se {se[2]:.3f})"
    out[band] = row
R["2a: per extra death / kill in a role (blue minus red), log-odds of winning beyond v1, by game length"] = out
R["2a: ADC damage share, mean by band"] = {b_: round(float(pl[(pl.position == "bot") & (pl.band == b_)].damageshare.mean()), 3) for b_ in ["under 28", "28-35", "35+"]}
R["2a: ADC damage share, winners v losers, by band"] = {b_: [round(float(pl[(pl.position == "bot") & (pl.band == b_) & (pl.result == w)].damageshare.mean()), 3) for w in (1, 0)] for b_ in ["under 28", "28-35", "35+"]}
# ---- 2b ----
key = lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum())
role_of = {(gg, s.lower(), key(c)): p for gg, s, c, p in zip(pl.gameid, pl.side, pl.champion, pl.position)}
tmm = pd.read_csv(TMF, dtype={"gid": str}).dropna(subset=["gameid"]); tmm = tmm[tmm.gameid != "AMBIGUOUS"].drop_duplicates("gameid")
ev = pd.read_csv(TEF, dtype={"gid": str}); ev = ev[ev.gid.isin(tmm.gid)].merge(tmm[["gid", "gameid", "len"]], on="gid")
rows = []
for gg, d in ev[ev.type == "kill"].sort_values(["gameid", "t"]).groupby("gameid"):
    L = d.len.iloc[0]; grp = np.cumsum(np.r_[True, np.diff(d.t.values) > 20])
    for _, f in d.groupby(grp):
        if len(f) < 2: continue  # fights with 2+ kills: there is a first death and a fight result
        e0 = f.iloc[0]; dying = "red" if e0.side == "blue" else "blue"; vr = role_of.get((gg, dying, key(e0.victim_champ)))
        if vr is None: continue
        won = (f.side == dying).sum() > (f.side != dying).sum(); lost = (f.side == dying).sum() < (f.side != dying).sum()
        t0 = int(f.t.min()); ends = (L - int(f.t.max())) <= 180
        rows.append((t0, vr, won, lost, ends, (f.side != dying).sum() - (f.side == dying).sum()))
FB = pd.DataFrame(rows, columns=["t", "first_dead", "dying_side_won", "dying_side_lost", "game_ends_within_3", "kill_edge_to_other_side"])
FB["when"] = pd.cut(FB.t, [0, 1500, 2100, 9999], labels=["under 25", "25-35", "35+"], right=False)
R["2b: fights with 2+ kills, by the role that dies first: share of fights the dying side still wins / loses, and the game ending within 3 min"] = {
    w: {r: {"fights": int(((FB.when == w) & (FB.first_dead == r)).sum()),
            "dying side wins fight": round(float(FB[(FB.when == w) & (FB.first_dead == r)].dying_side_won.mean()), 3),
            "dying side loses fight": round(float(FB[(FB.when == w) & (FB.first_dead == r)].dying_side_lost.mean()), 3),
            "game ends within 3 min": round(float(FB[(FB.when == w) & (FB.first_dead == r)].game_ends_within_3.mean()), 3)} for r in ROLES} for w in ["under 25", "25-35", "35+"]}
# ---- 2c ----
t2 = tm.copy(); t2["more_drag"] = np.sign(t2.dragons - t2.opp_dragons)
R["2c: win rate by game length"] = {b_: {"took an Elder": round(float(t2[(t2.band == b_) & (t2.elders > 0) & (t2.opp_elders == 0)].result.mean()), 3),
                                          "games with an Elder (one team only)": int(((t2.band == b_) & (t2.elders > 0) & (t2.opp_elders == 0)).sum()),
                                          "first Baron": round(float(t2[(t2.band == b_) & (t2.firstbaron == 1)].result.mean()), 3),
                                          "more dragons": round(float(t2[(t2.band == b_) & (t2.more_drag > 0)].result.mean()), 3)} for b_ in ["under 28", "28-35", "35+"]}
R["2c: games by length band"] = {b_: int((tm[tm.side == "Blue"].band == b_).sum()) for b_ in ["under 28", "28-35", "35+"]}
# ---- 3b ----
p_ = 1 / (1 + np.exp(-pl.z)); pl = pl.assign(res_v1=pl.result - p_)
tr = pl[pl.day < CUT]
sc = tr[tr.band == "35+"].groupby(["champion", "position"]).res_v1.agg(["sum", "count"]); ss = tr[tr.band == "under 28"].groupby(["champion", "position"]).res_v1.agg(["sum", "count"])
SC = (sc["sum"] / (sc["count"] + 30)).sub(ss["sum"] / (ss["count"] + 30), fill_value=0).to_dict()
pl = pl.assign(scal=[SC.get((c, r), 0.0) for c, r in zip(pl.champion, pl.position)])
dr = pl.groupby(["gameid", "side"]).scal.sum().unstack()
G = tm[tm.side == "Blue"].set_index("gameid")[["result", "z", "band", "mins", "day", "league"]].join((dr.Blue - dr.Red).rename("gap")).join((dr.Blue + dr.Red).rename("sum")).dropna()
for nm, m in {"train (before 1 Sep)": G.day < CUT, "from 1 Sep": G.day >= CUT, "Worlds": G.league == "WLDs"}.items():
    d = G[m]; X = np.c_[np.ones(len(d)), d.z, d.gap * (d.band == "35+"), d.gap * (d.band == "under 28"), d.gap * (d.band == "28-35")]
    b, se = logit(X, d.result.values.astype(float))
    R.setdefault("3b: scaling gap (blue minus red) and winning, beyond v1: log-odds per unit in long / short / middle games", {})[nm] = {
        "games": len(d), "35+": f"{b[2]:+.2f} (se {se[2]:.2f})", "under 28": f"{b[3]:+.2f} (se {se[3]:.2f})", "28-35": f"{b[4]:+.2f} (se {se[4]:.2f})",
        "corr of scaling sum with game length": round(float(np.corrcoef(d["sum"], d.mins)[0, 1]), 3), "scaling gap sd": round(float(d.gap.std()), 3)}
# ---- 4 ----
R["4a: the sim's fitted dragon taker (params3.json, already in use), per 1k gold unless noted"] = json.load(open(PJ))["taker"]["dragon"]
gd10 = (blue.golddiffat10).unstack(); tr_ = pl[pl.day < CUT].copy()
x = pd.concat([tr_[["position", "champion", "golddiffat10"]]]); cv = x.groupby(["position", "champion"]).golddiffat10.agg(["sum", "count"]); CV = (cv["sum"] / (cv["count"] + 20)).to_dict()
pl = pl.assign(tempo=[CV.get((r, c), 0.0) for c, r in zip(pl.champion, pl.position)])
tp = pl.groupby(["gameid", "side"]).tempo.sum().unstack()
D = tm[tm.side == "Blue"].set_index("gameid")[["firstdragon", "z", "day", "league"]].join(gd10[["jng", "mid"]]).join((gd10.bot + gd10.sup).rename("botduo")).join(((tp.Blue - tp.Red) / 1000).rename("tempo_gap")).dropna()
for nm, m in {"train": D.day < CUT, "from 1 Sep": D.day >= CUT, "Worlds": D.league == "WLDs"}.items():
    d = D[m]; X = np.c_[np.ones(len(d)), d.z, d.jng / 1000, d.mid / 1000, d.botduo / 1000, d.tempo_gap]; b, se = logit(X, d.firstdragon.values.astype(float))
    R.setdefault("4b: blue takes the first dragon (log-odds): side (intercept), v1, gold at 10 per 1k (jungle, mid, bot duo), draft early tempo per 1k", {})[nm] = {
        "games": len(d), "blue share": round(float(d.firstdragon.mean()), 3), **{k_: f"{v_:+.3f} (se {s_:.3f})" for k_, v_, s_ in zip(["blue side", "v1", "jungle", "mid", "bot duo", "early tempo"], b, se)}}
json.dump(R, open(OUT, "w"), indent=1, default=str); print(json.dumps(R, indent=1, default=str))
