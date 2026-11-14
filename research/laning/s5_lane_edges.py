"""Laning slice, step 1a (14 Nov 2026 AEST; research/laning-plan.md; Luke OK'd step 1). Read-only.
What decides a lane's edge at 10 and 15 minutes: the players, their champions, the matchup and comfort.
Rows: every 2026 major-league game (Worlds qualifier rows before 1 Oct left out) x role, from the blue player's side:
  y = gold edge at 15 (also reported at 10) of blue's player over red's player in that role (Oracle's Elixir golddiffat15 / at10).
Model, per role (all effects shrunk toward 0, fitted by weighted ridge, recent games weighted by a half-life):
  y = role intercept (blue side)
      + player[blue] - player[red]                       player lane skill (lasting: all of 2026)
      + champion[blue, role] - champion[red, role]        champion lane strength (meta: half-life on dates, so 16.20 / Worlds count most)
      + matchup[blue champ v red champ, role]             champion v champion
      + comfort x (log(1 + blue's earlier games on the champion) - same for red)
      + player x champion[blue] - player x champion[red]  how a player does on that champion beyond his usual
Every shrink (k) and half-life is chosen on training games only (fit before 1 Aug, judge 1-31 Aug), never on test games.
Tests (Luke, 14 Nov: Worlds first, day by day):
  Worlds: for each Worlds day (UTC), fit on every game before that day (weights from that day), predict that day's games.
  2026 second check: fit before 1 Sep, predict non-Worlds major games from 1 Sep.
  Versions add one block at a time; "current sim" = the app's lane inputs (skill gap, champion gold at 15, team strength) fitted linearly
  on the same training games (note: its skill table was built on the full file, so it has a small head start on test games).
  Score: mean squared error of the gold edge at 15 (and 10), and the share of lanes whose winner the model calls right.
  Stability (player lane skill): player effects fitted on odd v even games of 2026 before 1 Sep, correlation for players with 20+ games each.
Data, splits and the model come from research/lib (14 Nov 2026); every run leaves a record in research/runs/.
usage (repo root): python -I research/laning/s5_lane_edges.py [--minor]   (writes research/model/laning/lane_edges.json, or lane_edges_minor.json)
  --minor adds minor-league games on patch 16.20 to the champion and matchup blocks only (their players get their own effects),
          for the minor-league test (Luke, 14 Nov: test them first)."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np, pandas as pd
from lib import config, data
from lib.runlog import Run
from lib.lane_model import lane_rows, Model, Current
MINOR = "--minor" in sys.argv; ROLES = config.ROLES
OUT = config.MODEL_DIR / "laning" / ("lane_edges_minor.json" if MINOR else "lane_edges.json")
with Run("lane_edges" + ("_minor" if MINOR else ""), params={"minor_16_20": MINOR}, inputs=[config.OE_CSV, config.LANE_FEATURES]) as run:
    data.check(data.oe(["gameid", "league", "date"]))
    J, cnt, names = lane_rows(MINOR)
    print("rows", len(J), "games", J.gameid.nunique(), "Worlds games", J[J.league == "WLDs"].gameid.nunique(), flush=True)

    def score(D, p):
        e = D.y.values - p; mj = D.major.values
        return {"mse": float(np.mean(e[mj] ** 2)), "winner_right": float(np.mean(np.sign(p[mj]) == np.sign(D.y.values[mj]))), "n": int(mj.sum())}
    VERS = [("role + side only", []), ("+ player lane skill", ["player"]), ("+ champion", ["player", "champ"]),
            ("+ matchup", ["player", "champ", "pair"]), ("+ comfort (games on champ)", ["player", "champ", "pair", "comfort"]),
            ("+ player x champion", ["player", "champ", "pair", "comfort", "pc"]),
            ("+ team strength (v1, as the current sim)", ["player", "champ", "pair", "comfort", "pc", "team"])]
    R = {"rows": int(len(J)), "minor_16_20": MINOR}
    for target in ("y15", "y10"):
        J["y"] = J[target]; D = J.dropna(subset=["y"])
        # choose k and half-lives on training games only: fit before 1 Aug, judge 1-31 Aug (majors)
        tr, va = D[D.day < config.TUNE_FROM], D[(D.day >= config.TUNE_FROM) & (D.day < config.SPLIT) & D.major]
        t_va = int(pd.Timestamp(config.TUNE_FROM).value // 86_400_000_000_000)
        K = {"player": 40, "champ": 40, "pair": 80, "pc": 40}; HL = {"p": None, "c": None}
        full = VERS[-2][1]
        for _ in range(2):
            for nm, grid in [("player", [5, 10, 20, 40, 80, 160, 320]), ("champ", [5, 10, 20, 40, 80, 160, 320]), ("pair", [10, 20, 40, 80, 160, 320, 640, 1280]),
                             ("pc", [5, 10, 20, 40, 80, 160, 320, 640]), ("hl_p", [None, 60, 120, 240]), ("hl_c", [None, 30, 60, 120])]:
                best = None
                for v in grid:
                    k2, h2 = dict(K), dict(HL)
                    if nm.startswith("hl"): h2[nm[-1]] = v
                    else: k2[nm] = v
                    e = score(va, Model(full, k2, h2).fit(tr, t_va).predict(va))["mse"]
                    if best is None or e < best[0]: best = (e, v)
                if nm.startswith("hl"): HL[nm[-1]] = best[1]
                else: K[nm] = best[1]
        R[target] = {"chosen on training games (fit < 1 Aug, judge Aug)": {"k": K, "half_life_days": HL}}
        # Worlds, day by day
        wdays = sorted(D[D.league == "WLDs"].day.unique()); W = {}
        for nm, bl in [("current sim inputs", None)] + VERS:
            preds = []
            for dday in wdays:
                trn, tst = D[D.day < dday], D[(D.day == dday) & (D.league == "WLDs")]
                t_ref = int(pd.Timestamp(dday).value // 86_400_000_000_000)
                m = Current().fit(trn[trn.major], t_ref) if bl is None else Model(bl, K, HL).fit(trn, t_ref)
                preds.append(pd.Series(m.predict(tst), index=tst.index))
            p = pd.concat(preds); T = D.loc[p.index]; W[nm] = score(T, p.values)
            W[nm]["by role mse"] = {ro: round(float(np.mean((T.y.values[(T.position == ro).values] - p.values[(T.position == ro).values]) ** 2))) for ro in ROLES}
        R[target]["Worlds day by day"] = W
        # 2026 second check
        trn, tst = D[D.day < config.SPLIT], D[(D.day >= config.SPLIT) & D.major & (D.league != "WLDs")]
        t_ref = int(pd.Timestamp(config.SPLIT).value // 86_400_000_000_000); S = {}
        for nm, bl in [("current sim inputs", None)] + VERS:
            m = Current().fit(trn[trn.major], t_ref) if bl is None else Model(bl, K, HL).fit(trn, t_ref); S[nm] = score(tst, m.predict(tst))
        R[target]["2026 from 1 Sep (non-Worlds)"] = S
        print(target, json.dumps({"k": K, "hl": HL}), flush=True)
        for nm in W: print(f"  {nm:32s} Worlds mse {W[nm]['mse']:>9.0f} right {W[nm]['winner_right']:.3f} | 2026 mse {S[nm]['mse']:>9.0f} right {S[nm]['winner_right']:.3f}", flush=True)
    # stability of player lane skill (y15): odd v even games before 1 Sep
    J["y"] = J.y15; D = J.dropna(subset=["y"]); D = D[(D.day < config.SPLIT) & D.major]
    gi = {g: i for i, g in enumerate(sorted(D.gameid.unique()))}; half = D.gameid.map(gi) % 2
    K = R["y15"]["chosen on training games (fit < 1 Aug, judge Aug)"]["k"]
    t_ref = int(pd.Timestamp(config.SPLIT).value // 86_400_000_000_000)
    h0 = Model(["player", "champ", "pair"], K, {"p": None, "c": None}).fit(D[half == 0], t_ref); h1 = Model(["player", "champ", "pair"], K, {"p": None, "c": None}).fit(D[half == 1], t_ref)
    st = {}
    for role in ROLES:
        n0 = pd.concat([D[(half == 0) & (D.position == role)].pb, D[(half == 0) & (D.position == role)].pr]).value_counts()
        n1 = pd.concat([D[(half == 1) & (D.position == role)].pb, D[(half == 1) & (D.position == role)].pr]).value_counts()
        ok = [p for p in n0.index if n0[p] >= 20 and n1.get(p, 0) >= 20]
        a = np.array([h0.par[role]["eff"]["player"][p] for p in ok]); c = np.array([h1.par[role]["eff"]["player"][p] for p in ok])
        st[role] = {"players": len(ok), "corr odd v even": round(float(np.corrcoef(a, c)[0, 1]), 3) if len(ok) > 2 else None}
    R["player lane skill stability (gold at 15, odd v even games before 1 Sep)"] = st; print("stability", st, flush=True)
    # the full fit to the last day, for reading: largest player and champion effects at 15
    J["y"] = J.y15; D = J.dropna(subset=["y"]); K = R["y15"]["chosen on training games (fit < 1 Aug, judge Aug)"]
    m = Model(VERS[-1][1], K["k"], K["half_life_days"]).fit(D, int(D.ts.max()) + 1)
    R["largest effects, gold at 15 (fit on every game)"] = {role: {
        "players top": [f"{names.get(p, p)} {v:+.0f}" for p, v in sorted(m.par[role]["eff"].get("player", {}).items(), key=lambda kv: -kv[1])[:8]],
        "champions top": [f"{c} {v:+.0f}" for c, v in sorted(m.par[role]["eff"].get("champ", {}).items(), key=lambda kv: -kv[1])[:8]],
        "comfort per log-game": round(m.par[role]["cf"], 1), "per unit of team strength": round(m.par[role]["ct"], 1)} for role in ROLES}
    for t in ("y15", "y10"):
        for nm, v in R[t]["Worlds day by day"].items(): run.result(f"{t} Worlds mse | {nm}", round(v["mse"]))
        for nm, v in R[t]["2026 from 1 Sep (non-Worlds)"].items(): run.result(f"{t} 2026 mse | {nm}", round(v["mse"]))
    run.save_json(OUT, R)
