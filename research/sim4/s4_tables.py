"""Sim session 4 (13 Nov 2026 AEST): builds js/sim-tables.js, every table the app's new sim reads, from a refit folder. Never hand-edited.
What goes in (all fitted or counted from real games; Luke 13 Nov: the history tables come from real games only, a run never updates them):
  P        the sim's event tables: params3.json, fighttypes.json (with the early-window keys), the lane-level fit (version 2) and the
           early-kill fit (research/sim4/s4_earlykills.py)
  cal      each sim version's calibration (gain etc.) from that folder's Worlds replays: default = fight types + pushes + lane-level,
           alt = baseline + lane-level (Luke, 13 Nov)
  v1       who-wins before the draft: team and league terms and the blue-side term (fit on every game before the cutoff, 90-day
           half-life, / 1.125), the player-skill weights and the league shift per role (research/local/sim1/v1_all/league_fresh.json),
           each Worlds player's current skill estimates (pnow.csv)
  lanes    per player: lane skill; per champion and role: lane value in gold at 15 (120-day half-life, k = 20), kills-minus-deaths value
           (k = 20), strength (result minus v1's expected, k = 100), draft styles (siege, objectives, skirmish, pace; 60-day half-life)
  history  comfort (a Worlds player's games on each champion, all leagues), bot + support champion synergy (k = 30), games each bot
           duo has played together; as of the cutoff
Check: --check <gameid> rebuilds one played game's inputs with history as of that game's day and compares them with the fit
folder's saved per-game inputs (lane-level m0 / e0 and draft styles), which must match.
usage (repo root): python -I research/sim4/s4_tables.py <OE csv> <v1_games.csv> <sim1 build dir> <fit dir> <calibration dir> <league_fresh.json>
                   <app params dir> <out js> [--cutoff 2026-11-10] [--check <gameid>] [--pog research/model/pog/pog_app.json]
  app params dir: fighttypes.json (with the early-window keys), earlykills.json, participants.json, firstdragon.json, all fitted on the same
  games (research/local/sim4/app_params); calibration dir: default/ and alt/ test3_results.json from the same tables with every chosen option on.
  --pog: Player of the Game version C and the rating table (research/sim4/s4_pog.py)."""
import os, sys, json, math, runpy, contextlib, io
from collections import defaultdict
import numpy as np, pandas as pd
a = sys.argv[1:]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
CSV, V1, B1, FIT, REP, LFJ, APD, OUTJS = a[:8]; CUTD = opt("--cutoff", "2026-11-10"); CHECK = opt("--check", None); POGJ = opt("--pog", None)
ROLES = ["top", "jng", "mid", "bot", "sup"]; MAJOR = {"LCK", "LPL", "LEC", "LCS", "LCP", "CBLOL", "FST", "MSI", "EWC", "WLDs"}
SKILL = {"top": "e_laning", "jng": "e_early", "mid": "e_laning", "bot": "e_lane_own", "sup": "e_playmaking"}
MAIN = {"top": ["laning", "teamfight", "cons_side", "cons_dur", "cons_steady"], "jng": ["early", "objectives", "teamfight"],
        "mid": ["laning", "mapimpact", "damage"], "bot": ["lane_own", "lane_duo", "damage", "lategame"], "sup": ["playmaking", "mappresence", "reliability"]}
HL_LANES, HL_COMP, K = 120.0, 60.0, 20
cols = ["gameid", "league", "date", "side", "position", "playerid", "teamid", "champion", "result", "golddiffat10", "golddiffat15", "killsat15", "deathsat15"]
raw = pd.read_csv(CSV, low_memory=False, usecols=cols)
raw = raw[~((raw.league == "WLDs") & (raw.date < "2026-10-01")) & (raw.date < CUTD)].copy(); raw["day"] = raw.date.str[:10]
v1 = pd.read_csv(V1).set_index("gameid")
PL = raw[raw.position.isin(ROLES)].copy(); PL["p"] = PL.gameid.map(v1.p_v1); PL.loc[PL.side == "Red", "p"] = 1 - PL.loc[PL.side == "Red", "p"]
pick = lambda js: json.load(open(js))

# ---------- champion lane values (as s3_lanes.py, s3_lanelevel.py; training = every game before the cutoff) ----------
L = PL[PL.league.isin(MAJOR)]
bl = L[L.side == "Blue"].set_index(["gameid", "position"]); rd = L[L.side == "Red"].set_index(["gameid", "position"])
LL_ = bl[["day", "champion", "golddiffat10", "golddiffat15", "killsat15", "deathsat15"]].join(rd[["champion", "killsat15", "deathsat15"]], rsuffix="_red").reset_index()
LL_["z"] = LL_.gameid.map(v1.z_v1); LL_ = LL_.dropna(subset=["golddiffat10", "golddiffat15", "z"])
LL_["w"] = 0.5 ** ((pd.Timestamp(CUTD) - pd.to_datetime(LL_.day)).dt.days.clip(lower=0) / HL_LANES)
x = pd.concat([LL_[["position", "champion", "golddiffat15", "w"]].rename(columns={"champion": "c", "golddiffat15": "v"}),
               LL_[["position", "champion_red", "golddiffat15", "w"]].rename(columns={"champion_red": "c", "golddiffat15": "v"}).assign(v=lambda t: -t.v)])
g = x.assign(wv=x.w * x.v).groupby(["position", "c"])[["wv", "w"]].sum(); CGOLD = (g.wv / (g.w + K)).to_dict()
lf = pd.read_csv(os.path.join(FIT, "lanes3_features.csv")); LFG = set(lf.gameid)
kd = LL_[LL_.gameid.isin(LFG)].copy(); kd["v"] = (kd.killsat15 - kd.deathsat15) - (kd.killsat15_red - kd.deathsat15_red); kd = kd.dropna(subset=["v"])
x = pd.concat([kd[["position", "champion", "v"]].rename(columns={"champion": "c"}), kd[["position", "champion_red", "v"]].rename(columns={"champion_red": "c"}).assign(v=lambda t: -t.v)])
g = x.groupby(["position", "c"]).v.agg(["sum", "count"]); CKD = (g["sum"] / (g["count"] + K)).to_dict()
STY = pd.read_csv(os.path.join(FIT, "comp3_styles_pre_sep.csv")).set_index(["champion", "position"])[["siege", "objectives", "skirmish", "pace"]]

# ---------- history up to a day (as s3_lanelevel.py: built day by day from earlier days only) ----------
def history(until):
    comf = defaultdict(int); tog = defaultdict(int); st_s = defaultdict(float); st_n = defaultdict(int); sy_s = defaultdict(float); sy_n = defaultdict(int)
    for day, dd in PL[PL.day < until].groupby("day", sort=True):
        for (g_, s_), xx in dd.groupby(["gameid", "side"]):
            xx = xx.set_index("position")
            if not (set(ROLES) <= set(xx.index) and xx.index.is_unique): continue
            for r in ROLES:
                pid, ch = xx.at[r, "playerid"], xx.at[r, "champion"]
                if pid == pid: comf[(pid, ch)] += 1
                if xx.at[r, "p"] == xx.at[r, "p"]: st_s[(ch, r)] += xx.at[r, "result"] - xx.at[r, "p"]; st_n[(ch, r)] += 1
            pa, pb = xx.at["bot", "playerid"], xx.at["sup", "playerid"]
            if pa == pa and pb == pb: tog[frozenset((pa, pb))] += 1
            if xx.at["bot", "p"] == xx.at["bot", "p"]:
                k_ = (xx.at["bot", "champion"], xx.at["sup", "champion"]); sy_s[k_] += xx.at["bot", "result"] - xx.at["bot", "p"]; sy_n[k_] += 1
    return comf, tog, {k_: st_s[k_] / (st_n[k_] + 100) for k_ in st_s}, {k_: sy_s[k_] / (sy_n[k_] + 30) for k_ in sy_s}

LLF = pick(os.path.join(FIT, "ll2", "lanelevel_fit.json"))
def side_inputs(players, champs, skills, H):
    """one side: players[role] = playerid, champs[role], skills[role] = lane skill; H = history"""
    comf, tog, strength, syn = H; f = {}
    for r in ROLES:
        f[f"comfort_{r}"] = math.log1p(comf.get((players[r], champs[r]), 0)); f[f"strength_{r}"] = strength.get((champs[r], r), 0.0)
        f[f"cgold_{r}"] = CGOLD.get((r, champs[r]), 0.0); f[f"ckd_{r}"] = CKD.get((r, champs[r]), 0.0); f[f"skill_{r}"] = skills[r]
    f["together"] = math.log1p(tog.get(frozenset((players["bot"], players["sup"])), 0)); f["synergy"] = syn.get((champs["bot"], champs["sup"]), 0.0)
    st = {k_: sum(float(STY[k_].get((champs[r], r), 0.0)) for r in ROLES) for k_ in ["siege", "objectives", "skirmish", "pace"]}
    return f, st
def game_inputs(fb, fr, sb, sr):
    out = {}
    for r in ROLES:
        cs = LLF["inputs"][r]; gap = {c_: fb[c_] - fr[c_] for c_ in cs}
        out[f"m0_{r}"] = LLF["coef"][r]["const"] + sum(LLF["coef"][r][c_] * gap[c_] for c_ in cs)
        out[f"e0_{r}"] = LLF["coef_pregame"][r]["const"] + sum(LLF["coef_pregame"][r][c_] * gap[c_] for c_ in cs)
    out.update({"siege_d": sb["siege"] - sr["siege"], "obj_d": sb["objectives"] - sr["objectives"], "skirm_d": sb["skirmish"] - sr["skirmish"],
                "pace_s": sb["pace"] + sr["pace"], "siege_s": sb["siege"] + sr["siege"], "obj_s": sb["objectives"] + sr["objectives"]})
    return out

if CHECK:  # rebuild one played game as of its own day and compare with the fit folder's saved inputs
    rows = PL[PL.gameid == CHECK]; day = rows.day.iloc[0]; H = history(day)
    gf = pd.read_csv(os.path.join(B1, "gfeat.csv")); gf = gf[gf.gameid == CHECK]
    sk = {(r_.side, r_.position): r_[SKILL[r_.position]] for _, r_ in gf.iterrows()}
    sides = {}
    for s_ in ("Blue", "Red"):
        q = rows[rows.side == s_].set_index("position")
        sides[s_] = side_inputs({r: q.at[r, "playerid"] for r in ROLES}, {r: q.at[r, "champion"] for r in ROLES}, {r: sk.get((s_, r), np.nan) for r in ROLES}, H)
    # lane skill gaps are filled with 0 where missing, as s3_lanes.py does (gap, not each side)
    fb, fr = sides["Blue"][0], sides["Red"][0]
    for r in ROLES:
        if not (fb[f"skill_{r}"] == fb[f"skill_{r}"] and fr[f"skill_{r}"] == fr[f"skill_{r}"]): fb[f"skill_{r}"] = fr[f"skill_{r}"] = 0.0
    got = game_inputs(fb, fr, sides["Blue"][1], sides["Red"][1])
    saved = pd.read_csv(os.path.join(FIT, "ll2", "lanelevel_features.csv")).set_index("gameid").loc[CHECK].to_dict()
    comp = pd.read_csv(os.path.join(FIT, "comp3_games.csv")).set_index("gameid").loc[CHECK]
    saved.update({"siege_d": comp.siege_blue - comp.siege_red, "obj_d": comp.objectives_blue - comp.objectives_red, "skirm_d": comp.skirmish_blue - comp.skirmish_red,
                  "pace_s": comp.pace_blue + comp.pace_red, "siege_s": comp.siege_blue + comp.siege_red, "obj_s": comp.objectives_blue + comp.objectives_red})
    worst = max(abs(got[k_] - saved[k_]) for k_ in got)
    for k_ in got: print(f"{k_:9s} rebuilt {got[k_]:10.3f}   saved {saved[k_]:10.3f}")
    print("largest gap:", round(worst, 4), "(m0/e0 saved to 2 decimals, styles to 4)"); sys.exit(0)

# ---------- v1 (who-wins before the draft) ----------
with contextlib.redirect_stdout(io.StringIO()):
    sys_argv = sys.argv; sys.argv = ["exptest.py", CSV, os.path.join(B1, "games.csv"), os.path.join(B1, "gfeat.csv"), "research/model/sim1/player_experience_pre2026.csv"]
    ns = runpy.run_path(os.path.join("research", "sim1", "exptest.py")); sys.argv = sys_argv
G1, wfit, TI, LI, NT, home, TEMP = (ns[k_] for k_ in ["G", "wfit", "TI", "LI", "NT", "home", "TEMP"])
bt = wfit(np.where(G1.day < CUTD)[0], CUTD)
LF = pick(LFJ); W = LF["weights"]; CR = LF["league_shift_new"]; Lnew = LF["league_strength_10nov"]
idt = pd.read_csv("research/model/sim1/id_teams.csv"); idp = pd.read_csv("research/model/sim1/id_players.csv")
pn = pd.read_csv(os.path.join(B1, "pnow.csv")).set_index("playerid")
teams = {}
for t in idt.itertuples():
    h = home.get(t.teamid, ""); teams[t.app_id] = {"team": round(float(bt[TI[t.teamid]]), 5) if t.teamid in TI else 0.0, "home": h,
                                                  "league": round(float(bt[NT + LI[h]]), 5) if h in LI else 0.0}
players = {}
for p_ in idp.itertuples():
    r = p_.position; e = pn.loc[p_.playerid] if p_.playerid in pn.index else None
    sk = {f: (round(float(e["e_" + f]), 5) if e is not None and pd.notna(e["e_" + f]) else None) for f in MAIN[r]}
    lane = (round(float(e[SKILL[r]]), 5) if e is not None and pd.notna(e[SKILL[r]]) else None)
    players[f"{p_.app_id}|{r}"] = {"pid": p_.playerid, "name": p_.app_slot_name, "skills": sk, "lane_skill": lane}
H = history(CUTD); comf, tog, strength, syn = H
ids = {v["pid"]: k_ for k_, v in players.items()}
comfort = defaultdict(dict)
for (pid, ch), n in comf.items():
    if pid in ids: comfort[ids[pid]][ch] = n
together = {}
for t in idt.app_id:
    pb_, ps_ = players.get(f"{t}|bot"), players.get(f"{t}|sup")
    if pb_ and ps_: together[t] = tog.get(frozenset((pb_["pid"], ps_["pid"])), 0)
champs = defaultdict(dict)
for (r, c_), v in CGOLD.items(): champs[c_].setdefault(r, {})["cgold"] = round(v, 2)
for (r, c_), v in CKD.items(): champs[c_].setdefault(r, {})["ckd"] = round(v, 4)
for (c_, r), v in strength.items(): champs[c_].setdefault(r, {})["str"] = round(v, 5)
for (c_, r), row in STY.iterrows():
    for k_ in ["siege", "objectives", "skirmish", "pace"]:
        if row[k_]: champs[c_].setdefault(r, {})[k_[:4]] = round(float(row[k_]), 5)
P = pick(os.path.join(FIT, "params3.json")); P["fight_typed"] = pick(os.path.join(APD, "fighttypes.json")); P["lane_level"] = LLF
P["early_kills"] = {k_: v for k_, v in pick(os.path.join(APD, "earlykills.json")).items() if k_ in ("pair", "assist", "cutoff")}
P["fight_players"] = {k_: v for k_, v in pick(os.path.join(APD, "participants.json")).items() if k_ in ("players", "killer", "victim", "assist", "cutoff")}
_fd = pick(os.path.join(APD, "firstdragon.json")); P["taker_first_dragon"] = {"side": _fd["taker"], "timing": _fd["taker_timing"]}
for k_ in ("fight_size_table", "fights"): assert k_ in P  # the base tables the sim reads
cal = {"default": pick(os.path.join(REP, "default", "test3_results.json"))["cal"], "alt": pick(os.path.join(REP, "alt", "test3_results.json"))["cal"]}
T = {"built": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "cutoff": CUTD, "fit_dir": FIT.replace("\\", "/"), "P": P, "cal": cal,
     "v1": {"temp": TEMP, "blue": round(float(bt[-1]), 5), "w": W, "league_shift": CR, "league_strength": Lnew, "teams": teams},
     "players": players, "champs": champs, "comfort": comfort, "synergy": {f"{b_}|{s_}": round(v, 5) for (b_, s_), v in syn.items()}, "together": together,
     "skill_key": SKILL, "main_skills": MAIN}
if POGJ: _pg = pick(POGJ); T["pog"] = {k_: _pg[k_] for k_ in ("cutoff", "mean", "sd", "w", "pct")}
js = ("/* Tables for the new game sim (js/sim-engine.js). BUILT BY research/sim4/s4_tables.py, never edit by hand.\n   Every value is fitted or counted "
      f"from real games before {CUTD} (the Oracle's Elixir file and the gol.gg timelines); a tournament run never changes them. */\n"
      "window.SIM_TABLES = " + json.dumps(T, separators=(",", ":"), default=float) + ";\n")
open(OUTJS, "w", encoding="utf-8").write(js)
print("written", OUTJS, round(len(js) / 1024, 1), "KB | teams", len(teams), "players", len(players), "champions", len(champs),
      "comfort pairs", sum(len(v) for v in comfort.values()), "synergy", len(syn), "duos", len(together))
