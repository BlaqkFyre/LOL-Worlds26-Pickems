"""Sim session 1, step 3a: per player-game skill values (the agreed role table), then pre-game estimates.
Each metric is z-scored within its role (mean/sd from games before 1 Sep); a feature = mean of its metrics' z.
Pre-game estimate for a player = decayed (90-day half-life) weighted mean of their earlier games, shrunk toward 0 by n0
pseudo-games. Steadiness = shrunk spread of the player's per-game core score (laning + damage + KDA).
usage: python -I playerprep.py <csv> <games.csv> <n0> <out_rows.csv> <out_gamefeats.csv> <out_now.csv>"""
import sys
import numpy as np
import pandas as pd

CSV, GAMES, N0, OUT_ROWS, OUT_GF, OUT_NOW = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5], sys.argv[6]
HL = 90.0
MAJOR = ["LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"]
df = pd.read_csv(CSV, low_memory=False)
df = df[df.league.isin(MAJOR) & ~((df.league == "WLDs") & (df.date < "2026-10-01"))]
games = set(pd.read_csv(GAMES).gameid)
df = df[df.gameid.isin(games)]
team = df[df.position == "team"].set_index(["gameid", "side"])
p = df[df.position != "team"].copy()
mins = p.gamelength / 60.0
p["kp"] = (p.kills + p.assists) / p.teamkills.where(p.teamkills > 0)
p["d30"] = p.deaths / mins * 30
p["fbinv"] = p.firstbloodkill.fillna(0) + p.firstbloodassist.fillna(0)
p["ka15"] = p.killsat15 + p.assistsat15
tk15 = p.groupby(["gameid", "side"]).killsat15.transform("sum")
p["ka15share"] = p.ka15 / tk15.where(tk15 > 0)
p["towersdpm"] = p.damagetotowers / mins
p["dmgperdeath"] = np.log1p(p.damagetochampions / p.deaths.clip(lower=1))
p["wcpm_ctrl"] = p.controlwardsbought / mins
p["lateds"] = p.damageshare.where(p.gamelength > 33 * 60)
p["kapm"] = (p.kills + p.assists) / mins
p["dmgeff"] = p.damagetochampions / p.totalgold.where(p.totalgold > 0)
for col in ("dragons", "heralds", "void_grubs", "barons"):
    mine = [team.loc[(g, s), col] if (g, s) in team.index else np.nan for g, s in zip(p.gameid, p.side)]
    opp = [team.loc[(g, "Red" if s == "Blue" else "Blue"), col] if (g, s) in team.index else np.nan for g, s in zip(p.gameid, p.side)]
    mine, opp = np.array(mine, float), np.array(opp, float)
    p["obj_" + col] = np.where(mine + opp > 0, mine / np.where(mine + opp > 0, mine + opp, 1), np.nan)
# bot duo lane: ADC + support gold/xp/cs leads at 15 summed per side
duo = p[p.position.isin(["bot", "sup"])].groupby(["gameid", "side"])[["golddiffat15", "xpdiffat15", "csdiffat15"]].sum(min_count=2)
p = p.join(duo.add_prefix("duo_"), on=["gameid", "side"])

FEAT = {  # role -> feature -> [(metric, sign)]
 "top": {"laning": [("golddiffat15", 1), ("xpdiffat15", 1), ("csdiffat15", 1)],
         "teamfight": [("kp", 1), ("damageshare", 1)],
         "cons_side": [("towersdpm", 1), ("golddiffat25", 1), ("xpdiffat25", 1)],
         "cons_dur": [("damagetakenperminute", 1), ("damagemitigatedperminute", 1), ("d30", -1)],
         # replacement candidates, fixed before any results (3 Nov): Teamfight, steadiness
         "alt_tf_kp": [("kp", 1)], "alt_tf_dmg": [("damageshare", 1)], "alt_tf_dpm": [("dpm", 1)], "alt_tf_kapm": [("kapm", 1)],
         "alt_st_d15": [("deathsat15", -1)]},
 "jng": {"early": [("ka15", 1), ("fbinv", 1), ("xpdiffat15", 1)],
         "objectives": [("obj_dragons", 1), ("obj_heralds", 1), ("obj_void_grubs", 1), ("obj_barons", 1)],
         "teamfight": [("kp", 1), ("damageshare", 1), ("d30", -1)]},
 "mid": {"laning": [("golddiffat15", 1), ("xpdiffat15", 1), ("csdiffat15", 1)],
         "mapimpact": [("ka15share", 1), ("fbinv", 1)],
         "damage": [("damageshare", 1), ("dpm", 1)],
         "alt_mi_ka15": [("ka15", 1)], "alt_mi_fb": [("fbinv", 1)], "alt_mi_vis": [("vspm", 1)], "alt_mi_kp": [("kp", 1)]},
 "bot": {"lane_own": [("golddiffat15", 1), ("xpdiffat15", 1), ("csdiffat15", 1)],
         "lane_duo": [("duo_golddiffat15", 1), ("duo_xpdiffat15", 1), ("duo_csdiffat15", 1)],
         "damage": [("damageshare", 1), ("dpm", 1)],
         "positioning": [("d30", -1), ("dmgperdeath", 1)],
         "lategame": [("golddiffat25", 1), ("xpdiffat25", 1), ("lateds", 1)],
         "alt_dm_dpm": [("dpm", 1)], "alt_dm_share": [("damageshare", 1)], "alt_dm_eff": [("dmgeff", 1)]},
 "sup": {"playmaking": [("kp", 1), ("fbinv", 1), ("ka15", 1)],
         "mappresence": [("vspm", 1), ("wpm", 1), ("wcpm", 1), ("wcpm_ctrl", 1)],
         "reliability": [("d30", -1), ("deathsat15", -1)]},
}
CORE = {"top": ["laning", "teamfight"], "jng": ["early", "teamfight"], "mid": ["laning", "damage"], "bot": ["lane_own", "damage"], "sup": ["playmaking", "reliability"]}
pre = p.date < "2026-09-01"
for role, feats in FEAT.items():
    m = p.position == role
    for f, mets in feats.items():
        zs = []
        for met, sg in mets:
            mu, sd = p.loc[m & pre, met].mean(), p.loc[m & pre, met].std()
            zs.append(sg * (p.loc[m, met] - mu) / sd)
        p.loc[m, "f_" + f] = pd.concat(zs, axis=1).mean(axis=1, skipna=True)
    p.loc[m, "core"] = p.loc[m, ["f_" + c for c in CORE[role]]].mean(axis=1)
fcols = sorted({"f_" + f for feats in FEAT.values() for f in feats})
p[["gameid", "date", "league", "side", "position", "playerid", "playername", "teamname", "champion", "result"] + fcols + ["core"]].to_csv(OUT_ROWS, index=False)
print("per-game feature coverage (non-empty %, own role):")
for role, feats in FEAT.items():
    m = p.position == role
    print(" ", role, {f: round(100 * p.loc[m, "f_" + f].notna().mean()) for f in feats})

# pre-game estimates, in date order
p = p.sort_values(["date", "gameid"])
st = {}  # playerid -> dict(t, W per feat, S per feat, Wc, Sc, S2c)
t0 = np.datetime64("2026-01-01")
def decay(s, t):
    if s["t"] is None: return
    f = 0.5 ** ((t - s["t"]) / np.timedelta64(1, "D") / HL)
    for k in ("W", "S"): s[k] = {a: v * f for a, v in s[k].items()}
    s["Wc"] *= f; s["Sc"] *= f; s["S2c"] *= f
def est(s, f): return s["S"].get(f, 0.0) / (s["W"].get(f, 0.0) + N0)
def steady(s):
    if s["Wc"] < 1: return 0.0
    mu = s["Sc"] / s["Wc"]; var = max(s["S2c"] / s["Wc"] - mu * mu, 0)
    pop = 1.0  # role-average spread is about 1 in z units; shrink the player's spread toward it
    sd = (s["Wc"] * np.sqrt(var) + N0 * pop) / (s["Wc"] + N0)
    return -(sd - pop)  # higher = steadier than average
rows = []
for gid, g in p.groupby("gameid", sort=False):
    t = np.datetime64(g.date.iloc[0][:10])
    for r in g.itertuples():
        s = st.setdefault(r.playerid, {"t": None, "W": {}, "S": {}, "Wc": 0.0, "Sc": 0.0, "S2c": 0.0, "n": 0})
        decay(s, t); s["t"] = t
        feats = FEAT[r.position]
        rec = {"gameid": gid, "side": r.side, "position": r.position, "playerid": r.playerid, "n_before": s["n"]}
        for f in feats: rec["e_" + f] = est(s, f)
        if r.position == "top": rec["e_cons_steady"] = steady(s)
        rows.append(rec)
    for r in g.itertuples():  # update after all pre-game estimates of this game are taken
        s = st[r.playerid]; s["n"] += 1
        for f in FEAT[r.position]:
            v = getattr(r, "f_" + f)
            if pd.notna(v): s["S"][f] = s["S"].get(f, 0.0) + v; s["W"][f] = s["W"].get(f, 0.0) + 1
        if pd.notna(r.core): s["Sc"] += r.core; s["S2c"] += r.core ** 2; s["Wc"] += 1
gf = pd.DataFrame(rows)
gf.to_csv(OUT_GF, index=False)
# estimates now (1 Nov), for cards
now = np.datetime64("2026-11-01"); out = []
last = p.groupby("playerid").agg(name=("playername", "last"), team=("teamname", "last"), role=("position", "last"), games=("gameid", "count"), league=("league", "last"))
for pid, s in st.items():
    decay(s, now); s["t"] = now
    role = last.loc[pid, "role"]; rec = {"playerid": pid, **last.loc[pid].to_dict()}
    for f in FEAT[role]: rec["e_" + f] = est(s, f)
    if role == "top": rec["e_cons_steady"] = steady(s)
    out.append(rec)
pd.DataFrame(out).to_csv(OUT_NOW, index=False)
print(f"player-games {len(gf)}, players {len(st)}")
