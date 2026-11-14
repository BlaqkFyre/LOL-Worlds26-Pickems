"""Laning slice, step 3: fit every table the laning module reads (14 Nov 2026 AEST; Luke: build three; design research/laning/step3-design.md).
One params block per cut-off: each Worlds day (fitted only on games before that day) and "all" (every game, for the app later). Plus each
Worlds game's per-game inputs. Nothing typed in: every number below is fitted here or is an official game rule (League wiki, see
s5_rule_gold.py).
  fight     early fight winner: logistic on fights before the cut-off: side, players and champions of the roles in the fight (pre-game
            expected gold edge at 10, per 1k), team strength (v1), those roles' gold edge now (per 1k)                       (s5_fight_winner.py)
  plates    plates per side-lane-minute 3:00-13:59: Poisson: minute, lane, lane edge, enemy / own laners just killed, plates off, own grubs
  dragon    first dragon taker: side, strength, bot / mid / jungle edges, kills in the 60 s before, Worlds term (Luke: keep kills-before)
  grubs     each grub's taker: side, strength, top / mid / jungle edges, kills in the 60 s before, team grubs priority (Luke: full model)
  farm      the CS contest per role (feed): blue-minus-red CS per minute when both laners are alive = a + b x (pre-game expected CS edge at
            10 / 10) + spread, each minute's swing carrying over to the next by the measured lag-1 correlation (waves alternate); CS a minute for a lane-mate whose opponent is dead; gold per CS. From the feed's Worlds games on other
            days (leave-day-out: these are rates of the game, the players' and champions' part comes from the lane model fitted only on
            earlier games); "all" uses every feed game
  quest     ADC quest completion times (feed, other days)
  rules     official values: bounty base 300 (+10 a level from 7), first blood +100, accrual 1 per 3 kill/assist gold and 1 per 20 farm
            gold above a 100 buffer, depreciation 1 per 3.5 paid out, minimum 50, cap base + 700, assist pool half the bounty at most
            half the base; plate 120 split; first turret +300; turret 50 to each; ADC quest 300 then +2 a minion, +40 a takedown;
            grub 30 to the jungler
Per-game inputs (Worlds): pre-game expected gold and CS edge at 10 per role (lane model, games before that day), team grubs priority
difference (fitted before that day).
usage (repo root): python -I research/laning/s5_fit_laning.py   (writes research/local/laning/params/*.json, research/local/laning/inputs.json,
       research/model/laning/laning_params_all.json)"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data, fit, laning_data, feed
from lib.runlog import Run
from lib.lane_model import pregame_preds
PDIR = config.R / "local" / "laning" / "params"; PDIR.mkdir(parents=True, exist_ok=True)
RULES = {"bounty_base": 300, "bounty_per_level_from_7": 10, "first_blood": 100, "accrue_ka": 3.0, "accrue_farm": 20.0, "buffer": 100, "depreciate": 3.5,
         "min_bounty": 50, "cap_above_base": 700, "assist_share": 0.5, "plate": 120, "first_turret": 300, "turret_each": 50, "quest_lump": 300,
         "quest_per_minion": 2, "quest_per_takedown": 40, "grub": 30,
         "source": "League of Legends Wiki, opened 14 Nov 2026: Champion gold bounties, Turret, Role Quests, Voidgrub camp, Gold"}
with Run("fit_laning", inputs=[config.OE_CSV, config.LANE_FEATURES, config.TL_MATCH, config.TL_EVENTS, config.TL_GOLD, config.MODEL_DIR / "laning" / "farm.json"]) as run:
    o = data.oe(["gameid", "league", "date", "position", "teamname", "side"]); data.check(o)
    G10 = pregame_preds("y10"); PE = G10.set_index(["gameid", "position"]).pred.to_dict(); Z = G10.drop_duplicates("gameid").set_index("gameid").z_v1.fillna(0).to_dict()
    cset = json.load(open(config.MODEL_DIR / "laning" / "farm.json"))["C settings chosen on training games"]
    C10 = pregame_preds("c10", {"k": cset, "half_life_days": {"p": None, "c": None}}); PC = C10.set_index(["gameid", "position"]).pred.to_dict()
    T = laning_data.build(PE, Z, games=set(G10.gameid)); print({k: len(v) for k, v in T.items()}, flush=True)
    M = feed.player_minutes(); Q = feed.quest_times(); print("feed minutes", len(M), "quests", len(Q), flush=True)
    team = o[o.position == "team"].assign(sd=lambda d: d.side.str.lower()).set_index(["gameid", "sd"]).teamname.to_dict()
    W = o[o.league == "WLDs"].drop_duplicates("gameid"); wday = W.set_index("gameid").date.str[:10].to_dict(); days = sorted(set(wday.values()))
    def team_eff(tr, k=10.0):
        X = np.c_[np.ones(len(tr)), tr.z]; b = fit.logistic(X, tr.y.values); p = fit.sigmoid(X @ b); res = tr.y.values - p; w = p * (1 - p)
        num = pd.concat([pd.Series(res, index=tr.tb.values), pd.Series(-res, index=tr.tr.values)]).groupby(level=0).sum()
        den = pd.concat([pd.Series(w, index=tr.tb.values), pd.Series(w, index=tr.tr.values)]).groupby(level=0).sum()
        return (num / (den + k)).to_dict()
    def farm(Mx):
        piv = Mx.pivot_table(index=["gameid", "m", "role"], columns="side", values=["dcs", "dead"]).dropna()
        Cc = piv[(piv[("dead", "blue")] == 0) & (piv[("dead", "red")] == 0)].copy(); Cc["y"] = Cc[("dcs", "blue")] - Cc[("dcs", "red")]
        Cc = Cc[["y"]].reset_index(); Cc.columns = ["gameid", "m", "role", "y"]; Cc["pre"] = [PC.get((g, r), np.nan) / 10 for g, r in zip(Cc.gameid, Cc.role)]; Cc = Cc.dropna()
        out = {}
        for r, g in Cc.groupby("role"):
            b = np.linalg.lstsq(np.c_[np.ones(len(g)), g.pre], g.y.values, rcond=None)[0]; resid = g.y.values - np.c_[np.ones(len(g)), g.pre] @ b
            alive = Mx[(Mx.role == r) & (Mx.dead == 0)]
            gg = g.assign(e=resid).sort_values(["gameid", "m"]); gg["prev"] = gg.groupby("gameid").e.shift(); gg["mp"] = gg.groupby("gameid").m.shift()
            cc = gg[gg.mp == gg.m - 1]; rho = float(cc.e.corr(cc.prev)) if len(cc) > 30 else 0.0  # waves alternate: a big CS minute tends to follow a small one
            out[r] = {"a": float(b[0]), "b": float(b[1]), "sd": float(resid.std()), "rho": rho, "cs_rate": {str(m): float(v) for m, v in alive.groupby("m").dcs.mean().items()}}
        X = pd.get_dummies(Mx.role + "_" + Mx.m.astype(str), dtype=float); cols = ["dcs", "dk", "da", "plates", "dead", "towers", "first_tower"]
        bb = np.linalg.lstsq(np.c_[X.values, Mx[cols].values], Mx.dgold.values, rcond=None)[0]
        return out, float(bb[-len(cols)])
    XA = lambda d: np.column_stack([np.ones(len(d))] + [(d.m.values == m).astype(float) for m in range(4, 14)] + [(d.lane.values == "mid").astype(float), (d.lane.values == "bot").astype(float)]
                                   + [d[k].values.astype(float) for k in ("edge", "en_dead", "own_dead", "taken", "grubs")])
    PNAMES = ["const"] + [f"m{m}" for m in range(4, 14)] + ["lane_mid", "lane_bot", "edge", "en_dead", "own_dead", "taken", "grubs"]
    inputs, summary = {}, {}
    for cut in days + ["all"]:
        before = (lambda d: d.day < cut) if cut != "all" else (lambda d: d.day == d.day)
        F_, P_, DR, GR = (T[k][before(T[k])] for k in ("fights", "plates", "dragon", "grubs"))
        if cut != "all": assert F_.day.max() < cut and DR.day.max() < cut
        te = team_eff(GR)
        GRx = GR.assign(team=GR.tb.map(te).fillna(0) - GR.tr.map(te).fillna(0))
        Mx = M[M.day != cut] if cut != "all" else M; Qx = Q[Q.day != cut] if cut != "all" else Q
        fm, gpc = farm(Mx)
        L = {"fight": dict(zip(["const", "pre", "team", "state"], fit.logistic(np.c_[np.ones(len(F_)), F_[["pre", "team", "state"]].values], F_.y.values).tolist())),
             "plates": dict(zip(PNAMES, fit.poisson(XA(P_), P_.y.values).tolist())),
             "dragon": dict(zip(["const", "z", "bot", "mid", "jng", "net60", "w"], fit.logistic(np.c_[np.ones(len(DR)), DR[["z", "bot", "mid", "jng", "net60", "w"]].values], DR.y.values).tolist())),
             "grubs": dict(zip(["const", "z", "top", "mid", "jng", "net60", "team"], fit.logistic(np.c_[np.ones(len(GRx)), GRx[["z", "top", "mid", "jng", "net60", "team"]].values], GRx.y.values).tolist())),
             "farm": fm, "gold_per_cs": gpc, "quest_times": sorted(Qx.t.round().astype(int).tolist()), "rules": RULES, "cutoff": cut,
             "n": {"fights": len(F_), "plate rows": len(P_), "dragons": len(DR), "grubs": len(GR), "feed minutes": len(Mx), "quests": len(Qx)}}
        if cut == "all": L["team_grubs_priority"] = {k: round(float(v), 4) for k, v in te.items()}
        name = "laning_all.json" if cut == "all" else f"laning_{cut}.json"
        (PDIR / name).write_text(json.dumps(L, indent=1))
        if cut != "all":
            for g in [g for g, d in wday.items() if d == cut]:
                inputs[g] = {"day": cut, "pre_gold": [float(PE.get((g, r), 0.0)) for r in config.ROLES], "pre_cs": [float(PC.get((g, r), 0.0)) for r in config.ROLES],
                             "tgrub": float(te.get(team.get((g, "blue")), 0.0) - te.get(team.get((g, "red")), 0.0)), "w": 1.0}
        summary[cut] = {"fight": {k: round(v, 3) for k, v in L["fight"].items()}, "n": L["n"]}
        print(cut, summary[cut], flush=True)
    (config.R / "local" / "laning" / "inputs.json").write_text(json.dumps(inputs, indent=1))
    run.result("Worlds games with inputs", len(inputs))
    run.save_json(config.MODEL_DIR / "laning" / "laning_params_all.json", json.loads((PDIR / "laning_all.json").read_text()))
