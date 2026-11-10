"""Tower context research (Luke, 7 Nov): towers by lane x tier for all lanes; what happens just before a tower falls (kills by role,
dragons, Herald, grubs, Baron); side; and whether the lane's champions (measured siege) move it. Research only; nothing set by hand.
Data: gol.gg timelines matched to the Oracle's Elixir file (tl_events.csv, tl_gold.csv, tl_games.csv, tl_match.csv).
Panel: one row per (game, attacking side, lane, minute) while the defender's next tower in that lane (T1-T3) is standing.
  y = the attacker takes that tower during the minute.
  Inputs (events in the 120 s before the minute starts): attacker killed the enemy laner of this lane (bot = ADC or support),
  the enemy jungler, an enemy laner of another lane; attacker lost its own laner(s) of this lane; attacker took a dragon, Herald,
  grubs, Baron. Controls: tier, 5-minute period, attacker gold lead (per 1k), attacker is blue.
  Siege: measured tower damage of the champions (share of team damage to towers in major games before 1 Sep, minus the role average,
  pulled toward 0 with k = 20), attacker minus defender, for this lane's players and for the whole team.
One logistic fit per lane, fitted on games before 1 Sep, refitted on games from 1 Sep (Worlds included).
Pass = same sign and |t| >= 2 on both sets.
usage: python -I s3_tower_context.py <OE csv> <tl_events.csv> <tl_gold.csv> <tl_games.csv> <tl_match.csv> <out json>"""
import json, re, sys, unicodedata
import numpy as np
import pandas as pd

CSV, TLE, TLG, TLGAMES, TLM, OUT = sys.argv[1:7]
key = lambda s: re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())
MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
LANES = ["TOP", "MID", "BOT"]
LANE_POS = {"TOP": {"top"}, "MID": {"mid"}, "BOT": {"bot", "sup"}}

o = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "side", "position", "champion", "damagetotowers"])
P = o[o.position != "team"].copy(); P["k"] = P.champion.map(key)
# measured siege label (same as s3_style_validate.py)
Pm = P[P.league.isin(MAJOR) & ~((P.league == "WLDs") & (P.date < "2026-10-01"))].copy()
Pm["td_share"] = Pm.damagetotowers / Pm.groupby(["gameid", "side"]).damagetotowers.transform("sum")
pre = Pm[Pm.date < "2026-09-01"].dropna(subset=["td_share"])
rm = pre.groupby("position").td_share.mean()
cr = pre.groupby(["k", "position"]).td_share.agg(["sum", "count"])
cr["td"] = (cr["sum"] - cr["count"] * rm.reindex(cr.index.get_level_values(1)).values) / (cr["count"] + 20)
TD = cr.td.to_dict()

M = pd.read_csv(TLM, dtype={"gid": str}).dropna(subset=["gameid"])
G = pd.read_csv(TLGAMES, dtype={"gid": str}).set_index("gid")
M = M[M.gid.isin(G.index)]
gid2game = dict(zip(M.gid, M.gameid))
date = {g: G.date[g] for g in M.gid}
# roles and siege per game side from the file
R = P[P.gameid.isin(M.gameid)]
role_of, siege_lane, siege_team = {}, {}, {}
for (gm, sd), d in R.groupby(["gameid", "side"]):
    s = sd.lower()
    role_of[(gm, s)] = {k: p for k, p in zip(d.k, d.position)}
    tds = {p: TD.get((k, p), 0.0) for k, p in zip(d.k, d.position)}
    siege_team[(gm, s)] = sum(tds.values())
    for ln in LANES: siege_lane[(gm, s, ln)] = sum(v for p, v in tds.items() if p in LANE_POS[ln])

E = pd.read_csv(TLE, dtype={"gid": str}); E = E[E.gid.isin(gid2game)]
Gd = pd.read_csv(TLG, dtype={"gid": str}); Gd = Gd[(Gd.kind == "gold") & Gd.gid.isin(gid2game)]
gold = Gd.groupby(["gid", "side", "minute"]).value.sum().unstack("side")
OPP = {"blue": "red", "red": "blue"}

res = {"games": int(len(gid2game))}
# ---- 1. lane x tier, all lanes (non-nexus towers; side = the team that took it)
tw = E[(E.type == "tower") & ~E.detail.str.contains("NEXUS")].copy()
tw["tier"] = tw.detail.str[:2]; tw["lane"] = tw.detail.str[3:]
tw = tw.sort_values(["gid", "side", "lane", "t"])
tw["prev_t"] = tw.groupby(["gid", "side", "lane"]).t.shift()
n2 = 2 * len(gid2game)
lt = []
for (tier, lane), d in tw.groupby(["tier", "lane"]):
    row = {"tower": f"{tier} {lane}", "falls_per_team_game": round(len(d) / n2, 3), "median_min": round(d.t.median() / 60, 1),
           "q25_min": round(d.t.quantile(.25) / 60, 1), "q75_min": round(d.t.quantile(.75) / 60, 1)}
    if tier != "T1": row["median_gap_from_prev_tier_s"] = int(d.dropna(subset=["prev_t"]).eval("t - prev_t").median())
    for s in ("blue", "red"):
        x = d[d.side == s]; row[f"{s}_takes_share"] = round(len(x) / len(gid2game), 3); row[f"{s}_median_min"] = round(x.t.median() / 60, 1)
    lt.append(row)
res["lane_tier"] = lt
ft = tw.sort_values("t").groupby("gid").head(1)
res["first_tower_lane_by_side"] = {s: {ln: round(float((d.lane == ln).mean()), 3) for ln in LANES} | {"n": int(len(d))}
                                   for s, d in ft.groupby("side")}

# ---- 2. panel
ev = E[E.type.isin(["kill", "dragon", "herald", "grub", "baron"])].copy()
rows = []; cov = {"kills": 0, "victim_role_found": 0}; vroles = {}
for gid, ge in E.groupby("gid"):
    gm = gid2game[gid]; end = int(G.len[gid]); mins = end // 60
    gt = tw[tw.gid == gid]
    kills = ge[ge.type == "kill"]
    for s in ("blue", "red"):
        o_ = OPP[s]; ro = role_of.get((gm, o_), {}); rs = role_of.get((gm, s), {})
        kv = kills.assign(vrole=[(ro if sd == s else rs).get(key(v), "") for sd, v in zip(kills.side, kills.victim_champ)])
        my_k = kv[kv.side == s]; their_k = kv[kv.side == o_]
        cov["kills"] += len(my_k); cov["victim_role_found"] += int((my_k.vrole != "").sum())
        for v_ in my_k.vrole: vroles[v_ or "not found"] = vroles.get(v_ or "not found", 0) + 1
        objs = {t_: ge[(ge.type == t_) & (ge.side == s)].t.values for t_ in ("dragon", "herald", "grub", "baron")}
        for ln in LANES:
            down = gt[(gt.side == s) & (gt.lane == ln)].sort_values("t").t.values  # attacker's takes in this lane, in tier order
            for m in range(1, mins + 1):
                a, b = 60 * m, 60 * m + 60
                k_taken = int((down < a).sum())
                if k_taken >= 3: break
                w0 = a - 120
                win = lambda ts: int(((ts >= w0) & (ts < a)).sum() > 0)
                mk = my_k[(my_k.t >= w0) & (my_k.t < a)]; tk = their_k[(their_k.t >= w0) & (their_k.t < a)]
                g_ = gold.loc[(gid, m)] if (gid, m) in gold.index else None
                rows.append({"gid": gid, "lane": ln, "side": s, "m": m, "tier": k_taken + 1,
                             "y": int(((down >= a) & (down < b)).sum() > 0),
                             "k_lane": int(mk.vrole.isin(LANE_POS[ln]).any()), "k_jng": int((mk.vrole == "jng").any()),
                             "k_other": int((~mk.vrole.isin(LANE_POS[ln] | {"jng", ""})).any()),
                             "d_lane": int(tk.vrole.isin(LANE_POS[ln]).any()),
                             "dragon": win(objs["dragon"]), "herald": win(objs["herald"]), "grub": win(objs["grub"]), "baron": win(objs["baron"]),
                             "lead": np.nan if g_ is None else (g_[s] - g_[o_]) / 1000, "blue": int(s == "blue"),
                             "siege_lane": siege_lane.get((gm, s, ln), 0) - siege_lane.get((gm, o_, ln), 0),
                             "siege_team": siege_team.get((gm, s), 0) - siege_team.get((gm, o_), 0),
                             "test": int(date[gid] >= "2026-09-01")})
D = pd.DataFrame(rows).dropna(subset=["lead"])
D["siege_lane_z"] = D.siege_lane / D.siege_lane.std(); D["siege_team_z"] = D.siege_team / D.siege_team.std()
res["panel_rows"] = int(len(D)); res["tower_minutes"] = int(D.y.sum())
res["kill_victim_roles"] = {**cov, "by_role": vroles}
res["nexus_towers_left_out"] = int((E.type == "tower").sum() - len(tw)); res["tower_labels_used"] = sorted(tw.detail.unique().tolist())

def logit(X, y, it=50, l2=1.0):  # small ridge, as in s3_rates.py, so an input that never co-occurs with a tower (grubs in mid) stays finite
    b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + l2 * np.eye(X.shape[1]); b += np.linalg.solve(H, X.T @ (y - p) - l2 * b)
    p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p)
    se = np.sqrt(np.diag(np.linalg.inv(X.T @ (X * W[:, None]) + l2 * np.eye(X.shape[1]))))
    return b, se

INP = ["k_lane", "k_jng", "k_other", "d_lane", "dragon", "herald", "grub", "baron", "lead", "blue", "siege_lane_z", "siege_team_z"]
def design(d):
    per = np.clip(d.m // 5, 1, 8)
    cols = [np.ones(len(d))] + [(d.tier == t).astype(float).values for t in (2, 3)] + [(per == p).astype(float).values for p in range(2, 9)]
    return np.c_[tuple(cols) + tuple(d[c].values.astype(float) for c in INP)], 1 + 2 + 7
fits = {}
for ln in LANES:
    out = {}
    for name, d in (("train", D[(D.lane == ln) & (D.test == 0)]), ("test", D[(D.lane == ln) & (D.test == 1)])):
        X, off = design(d); b, se = logit(X, d.y.values.astype(float))
        out[name] = {"n": int(len(d)), "towers": int(d.y.sum()),
                     "coef": {c: [round(float(b[off + i]), 3), round(float(b[off + i] / se[off + i]), 2)] for i, c in enumerate(INP)}}
    out["passes"] = [c for c in INP if out["train"]["coef"][c][1] * out["test"]["coef"][c][1] > 0
                     and abs(out["train"]["coef"][c][1]) >= 2 and abs(out["test"]["coef"][c][1]) >= 2]
    fits[ln] = out
res["fits"] = fits
res["fit_note"] = "coef = [log-odds per unit, t]; events = within the 120 s before the minute; lead per 1k gold; siege per sd"
# descriptive: share of tower minutes v other at-risk minutes with each event
res["event_share"] = {ln: {c: [round(float(d[d.y == 1][c].mean()), 3), round(float(d[d.y == 0][c].mean()), 3)]
                           for c in ["k_lane", "k_jng", "k_other", "d_lane", "dragon", "herald", "grub", "baron"]}
                      for ln, d in D.groupby("lane")}
res["event_share_note"] = "[share of tower-falling minutes with the event in the 120 s before, share of other at-risk minutes]"
json.dump(res, open(OUT, "w"), indent=1, default=float)
pd.set_option("display.width", 220)
print(pd.DataFrame(lt).to_string(index=False)); print(json.dumps(res["first_tower_lane_by_side"]))
print("rows", len(D), "tower minutes", int(D.y.sum()))
for ln in LANES:
    f = fits[ln]; print(f"\n{ln} train n={f['train']['n']} towers={f['train']['towers']}  test n={f['test']['n']} towers={f['test']['towers']}  passes={f['passes']}")
    for c in INP: print(f"  {c:13s} train {f['train']['coef'][c]}  test {f['test']['coef'][c]}")
print(json.dumps(res["event_share"], indent=0))
