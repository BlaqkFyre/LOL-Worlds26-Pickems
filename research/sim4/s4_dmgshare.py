"""Damage share by player and champion (14 Nov 2026 AEST; Luke: not every ADC should top damage share, some variation would be there).
research/sim4/dmgshare_check.py: real Worlds top 16 by damage share = 13 ADCs + 3 mids (ShowMaker, Shanks, Knight); the sim's spread of player
averages within a role is too narrow (mid 0.015 v real 0.024, jungle 0.015 v 0.023) because its damage share = role average + a kill-participation
effect + noise (P["box"]), nothing for who plays or what champion.
Model (major-league games before the cutoff, Oracle's Elixir file), per player-game:
  damage share = role mean + role slope x (kill participation - role mean KP) + player effect + champion-in-role effect + noise
Effects are shrunk sums of residuals: player = sum(resid) / (games + k_p), champion = sum(resid) / (games + k_c), fitted in turn (3 rounds).
k_p and k_c are chosen on held-out games (fit before 1 Sep, score games from 1 Sep, squared error), from a grid; nothing typed in.
Then refit on every game to the cutoff with those k for the app. Reports: held-out error v the sim's current formula, and the leftover
noise sd per role (the sim's noise must shrink, or the spread would grow twice).
usage (repo root): python -I research/sim4/s4_dmgshare.py <OE csv> <out json> [--cutoff 2026-11-10] [--k <k_player> <k_champion>]"""
import sys, json, itertools
import numpy as np, pandas as pd
CSV, OUT = sys.argv[1:3]; CUT = sys.argv[sys.argv.index("--cutoff") + 1] if "--cutoff" in sys.argv else "2026-11-10"
ROLES = ["top", "jng", "mid", "bot", "sup"]; MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
o = pd.read_csv(CSV, low_memory=False, usecols=["gameid", "league", "date", "position", "playerid", "playername", "champion", "kills", "assists", "teamkills", "damageshare"])
o = o[o.league.isin(MAJOR) & o.position.isin(ROLES) & (o.date < CUT) & ~((o.league == "WLDs") & (o.date < "2026-10-01"))].dropna(subset=["damageshare", "playerid"]).copy()
o["kp"] = ((o.kills + o.assists) / o.teamkills.clip(lower=1)).clip(upper=1)
def base_fit(d):
    out = {}
    for r in ROLES:
        q = d[d.position == r]; kpm = q.kp.mean(); b = np.polyfit(q.kp - kpm, q.damageshare, 1)
        out[r] = {"mean": float(b[1]), "per_kp": float(b[0]), "kp_mean": float(kpm)}
    return out
def base_pred(d, B): return np.array([B[r]["mean"] + B[r]["per_kp"] * (k - B[r]["kp_mean"]) for r, k in zip(d.position, d.kp)])
def fit_effects(d, B, kp_, kc_, rounds=3):
    res0 = d.damageshare.values - base_pred(d, B); pe = pd.Series(0.0, index=d.playerid.unique()); ce = {}
    key_c = d.champion + "|" + d.position
    for _ in range(rounds):
        r1 = res0 - key_c.map(ce).fillna(0).values
        g = pd.DataFrame({"p": d.playerid.values, "r": r1}).groupby("p").r.agg(["sum", "count"]); pe = g["sum"] / (g["count"] + kp_)
        r2 = res0 - d.playerid.map(pe).fillna(0).values
        g = pd.DataFrame({"c": key_c.values, "r": r2}).groupby("c").r.agg(["sum", "count"]); ce = (g["sum"] / (g["count"] + kc_)).to_dict()
    return pe.to_dict(), ce
def predict(d, B, pe, ce): return base_pred(d, B) + d.playerid.map(pe).fillna(0).values + (d.champion + "|" + d.position).map(ce).fillna(0).values
tr, te = o[o.date < "2026-09-01"], o[o.date >= "2026-09-01"]
Btr = base_fit(tr); mse = lambda p, d: float(np.mean((d.damageshare.values - p) ** 2))
R = {"cutoff": CUT, "rows": {"train": len(tr), "test": len(te)}, "held_out_mse": {"role + kill participation only (the sim now)": round(mse(base_pred(te, Btr), te), 6)}}
grid = [1, 2, 5, 10, 20, 40, 80, 160, 320, 640, 1280]; best = None
KFIX = (int(sys.argv[sys.argv.index("--k") + 1]), int(sys.argv[sys.argv.index("--k") + 2])) if "--k" in sys.argv else None  # held-out checks: k already chosen
for kp_, kc_ in ([] if KFIX else itertools.product(grid, grid)):
    pe, ce = fit_effects(tr, Btr, kp_, kc_); e = mse(predict(te, Btr, pe, ce), te)
    R["held_out_mse"][f"k_player {kp_}, k_champion {kc_}"] = round(e, 6)
    if best is None or e < best[0]: best = (e, kp_, kc_)
if KFIX: best = (float("nan"), *KFIX)
for nm, kp_, kc_ in ([] if KFIX else [("player only", best[1], 1e9), ("champion only", 1e9, best[2])]):
    pe, ce = fit_effects(tr, Btr, kp_, kc_); R["held_out_mse"][nm + f" (k {kp_ if kp_ < 1e8 else kc_})"] = round(mse(predict(te, Btr, pe, ce), te), 6)
R["chosen"] = {"k_player": best[1], "k_champion": best[2], "held_out_mse": round(best[0], 6)}
# app fit: every game to the cutoff
B = base_fit(o); pe, ce = fit_effects(o, B, best[1], best[2]); res = o.damageshare.values - predict(o, B, pe, ce)
R["base"] = B; R["resid_sd_by_role"] = {r: round(float(res[(o.position == r).values].std()), 4) for r in ROLES}
R["resid_sd_without_effects"] = {r: round(float((o.damageshare.values - base_pred(o, B))[(o.position == r).values].std()), 4) for r in ROLES}
names = o.groupby("playerid").playername.agg(lambda s: s.value_counts().index[0]).to_dict()
R["player"] = {p: round(float(v), 4) for p, v in pe.items() if abs(v) >= 0.0005}; R["player_names"] = {p: names.get(p) for p in R["player"]}
R["champion"] = {c: round(float(v), 4) for c, v in ce.items() if abs(v) >= 0.0005}
top = sorted(pe.items(), key=lambda kv: -kv[1])[:10]; R["largest player effects"] = [f"{names.get(p)} {v:+.3f}" for p, v in top]
topc = sorted(ce.items(), key=lambda kv: -kv[1])[:10]; R["largest champion effects"] = [f"{c} {v:+.3f}" for c, v in topc]
json.dump(R, open(OUT, "w"), indent=1)
print(json.dumps({k: R[k] for k in ("rows", "chosen", "resid_sd_by_role", "resid_sd_without_effects", "largest player effects", "largest champion effects")}, indent=1))
print({k: v for k, v in R["held_out_mse"].items() if "k_player" not in k})
