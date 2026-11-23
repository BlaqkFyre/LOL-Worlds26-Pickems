"""Game memory, next steps, step 1a (24 Nov 2026 AEST; Luke OK'd): kill and assist credit by fight size, measured on real games.
Why: the v51 play-test (research/memory/next-steps-plan.md) had a support take four "solo" kills in one teamfight, and Player of the
Game went to junglers 3 of 4. Before fitting anything, this measures what real fights do.
Fights: kills less than 20 s apart (common.FIGHT_GAP). Fight size = kills in the fight: 1, 2, 3-4, 5-6, 7+. Phase by the fight's first
kill: 0-14, 15-24, 25+ min. Side A = the side with the fight's first kill, side B = the other side.
Sources:
- gol.gg timelines (each kill's killer, victim and assisting champions; roles from the Oracle's Elixir file), split into training games
  (before config.SPLIT, 1 Sep), other games from 1 Sep, and Worlds (test games: a check, never fitted on).
  The timelines' 40 executions (deaths with no killer champion) are left out.
- the lolesports Worlds feed (98 games; kills, deaths and assists per player by second, the in-game stats panel): per fight, each
  player's kills and assists from the change in their counts over the fight; per kill, assisters from each player's assist change in
  the kill's frame, split by count when a side lands 2+ kills in one frame (kills that can't be split stay in the killer tables only).
Output: research/model/memory/m7_kill_credit.json.
usage (repo root): python -I research/memory/m7_kill_credit.py"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import numpy as np, pandas as pd
from lib import config, data, feed
from lib.runlog import Run
from common import FIGHT_GAP, r3

OUT = config.MODEL_DIR / "memory"
ROLES = config.ROLES
SIZE = lambda n: "1" if n == 1 else "2" if n == 2 else "3-4" if n <= 4 else "5-6" if n <= 6 else "7+"
SIZES = ["1", "2", "3-4", "5-6", "7+"]
PHASE = lambda t: "0-14" if t < 900 else "15-24" if t < 1500 else "25+"
PHASES = ["0-14", "15-24", "25+"]

def group(kills):
    """kills sorted by time -> list of fights (each a list of kills)"""
    out, cur = [], []
    for k in kills:
        if cur and k["t"] - cur[-1]["t"] > FIGHT_GAP: out.append(cur); cur = []
        cur.append(k)
    if cur: out.append(cur)
    return out

def fight_rows(fights, src, split):
    """per kill and per player-in-fight rows from fights whose kills carry killer/victim roles and assister roles"""
    K, PF, F = [], [], []
    for gi, f in fights:
        n = len(f); sz, ph = SIZE(n), PHASE(f[0]["t"]); A = f[0]["side"]
        seen = {"blue": set(), "red": set()}; kc = {}; ac = {}
        for k in f:
            o = "red" if k["side"] == "blue" else "blue"
            seen[k["side"]].update([k["k"], *k["a"]]); seen[o].add(k["v"])
            kc[(k["side"], k["k"])] = kc.get((k["side"], k["k"]), 0) + 1
            for a in k["a"]: ac[(k["side"], a)] = ac.get((k["side"], a), 0) + 1
            K.append({"src": src, "split": split, "size": sz, "phase": ph, "killer": k["k"], "victim": k["v"], "n_ast": len(k["a"]),
                      "solo": int(len(k["a"]) == 0), "sideB": int(k["side"] != A), "ast_ok": 1, **{"ast_" + r: int(r in k["a"]) for r in ROLES}})
        kb = {s: sum(k["side"] == s for k in f) for s in ("blue", "red")}
        for s in ("blue", "red"):
            for r in seen[s]:
                PF.append({"src": src, "split": split, "size": sz, "phase": ph, "role": r, "sideB": int(s != A), "side_kills": kb[s],
                           "kills": kc.get((s, r), 0), "assists": ac.get((s, r), 0)})
        B = "red" if A == "blue" else "blue"
        F.append({"src": src, "split": split, "game": gi, "size": sz, "phase": ph, "kills_A": kb[A], "kills_B": kb[B],
                  "seen_A": len(seen[A]), "seen_B": len(seen[B]), "max_one_player": max(kc.values())})
    return K, PF, F

def timeline_fights(tm, ev, rl):
    E = ev[ev.type == "kill"].sort_values(["gameid", "t"]); split = {}
    for _, m in tm.iterrows(): split[m.gameid] = "worlds" if m.league == "WLDs" else "train" if m.day < config.SPLIT else "after 1 Sep"
    out = {s: [] for s in ("train", "after 1 Sep", "worlds")}; skipped = 0; execs = 0
    for g, d in E.groupby("gameid"):
        ks, ok = [], True
        for e in d.itertuples():
            # executions (24 Nov): 40 kill rows have no killer champion, no actor and no assists (deaths to a tower, minion or monster;
            # the parser fills side "red" for them), so there is no kill to credit; they are left out of the kills and fights
            if pd.isna(e.champ) and pd.isna(e.actor) and not (isinstance(e.assists, str) and e.assists): execs += 1; continue
            k, v = rl.get((g, data.key(e.champ))), rl.get((g, data.key(e.victim_champ)))
            a = [rl.get((g, data.key(c))) for c in str(e.assists).split("|")] if isinstance(e.assists, str) and e.assists else []
            if k is None or v is None or any(x is None for x in a) or k[1] != e.side: ok = False; break
            ks.append({"t": float(e.t), "side": e.side, "k": k[0], "v": v[0], "a": sorted({x[0] for x in a} - {k[0]})})
        if not ok: skipped += 1; continue
        out[split[g]] += [(g, f) for f in group(ks)]
    return out, skipped, execs

def feed_fights(games):
    """per fight from the feed: kills and assists per player from count changes; kills with a single kill in their frame keep killer
    and assisters (others: the fight's totals still count, the per-kill rows skip them)"""
    Kr, PFr, Fr, single, multi, resolved = [], [], [], 0, 0, 0
    for g in games:
        t, P, roles, sides = g["t"], g["P"], g["roles"], g["sides"]; kills = []
        for i in range(1, len(t)):
            dk = P[i, :, 2] - P[i - 1, :, 2]
            if dk.sum() <= 0: continue
            da = P[i, :, 4] - P[i - 1, :, 4]; dd = P[i, :, 3] - P[i - 1, :, 3]
            # assists from the players' K/D/A changes in this frame (Luke, 24 Nov: read the stats panel). Per killing side with m kills:
            # m = 1: every teammate whose assists went up assisted it. m > 1: a teammate whose assists rose by m assisted every one, by 0 none;
            # a killer whose assists rose by m - 1 assisted all the others, by 0 none; anything else can't be split (kill kept for the
            # killer tables, left out of the assist tables). The victim is known only when the other side has one death in the frame.
            for s in ("blue", "red"):
                kp = [p for p in range(10) if sides[p] == s and dk[p] > 0]
                if not kp: continue
                o = "red" if s == "blue" else "blue"; m = int(sum(dk[p] for p in kp))
                vic = [q for q in range(10) if sides[q] == o and dd[q] > 0]
                team = [q for q in range(10) if sides[q] == s]
                for p in kp:
                    for _ in range(int(dk[p])):
                        if m == 1: a, ok = [roles[q] for q in team if q != p and da[q] > 0], True
                        else:
                            a, ok = [], True
                            for q in team:
                                if q == p: continue
                                full = m - dk[q] if dk[q] > 0 else m  # kills this teammate could have assisted
                                if da[q] == full: a.append(roles[q])
                                elif da[q] != 0: ok = False
                        single += m == 1; multi += m > 1
                        kills.append({"t": float(t[i]), "i": i, "side": s, "k": roles[p], "v": roles[vic[0]] if len(vic) == 1 and m == 1 else None,
                                      "a": a, "one": ok, "multi": m > 1})
        for f in group(kills):
            n = len(f); sz, ph = SIZE(n), PHASE(f[0]["t"]); A = f[0]["side"]; B = "red" if A == "blue" else "blue"
            kc = {}
            for k in f:
                kc[(k["side"], k["k"])] = kc.get((k["side"], k["k"]), 0) + 1
                resolved += k["multi"] and k["one"]
                Kr.append({"src": "feed", "split": "worlds", "size": sz, "phase": ph, "killer": k["k"], "victim": k["v"], "n_ast": len(k["a"]),
                           "solo": int(len(k["a"]) == 0), "sideB": int(k["side"] != A), "ast_ok": int(k["one"]), **{"ast_" + r: int(r in k["a"]) for r in ROLES}})
            # each player's assists in the fight straight from the stats panel's count over the fight's frames (needs no splitting)
            i0, i1 = f[0]["i"], f[-1]["i"]; dA = P[i1, :, 4] - P[i0 - 1, :, 4]
            ac = {(sides[q], roles[q]): int(dA[q]) for q in range(10) if dA[q] > 0}
            kb = {s: sum(k["side"] == s for k in f) for s in ("blue", "red")}
            for s in ("blue", "red"):
                for r in ROLES:
                    if (s, r) in kc or (s, r) in ac:
                        PFr.append({"src": "feed", "split": "worlds", "size": sz, "phase": ph, "role": r, "sideB": int(s != A), "side_kills": kb[s],
                                    "kills": kc.get((s, r), 0), "assists": ac.get((s, r), 0)})
            Fr.append({"src": "feed", "split": "worlds", "game": g["gameid"], "size": sz, "phase": ph, "kills_A": kb[A], "kills_B": kb[B],
                       "max_one_player": max(kc.values())})
    return Kr, PFr, Fr, single, multi, resolved

def tables(K, PF, F):
    """the step 1a tables from one source/split"""
    KK = K; K = KK[KK.ast_ok == 1]  # killer tables use every kill; assist and solo tables only kills whose assisters are known
    T = {"kills": int(len(KK)), "kills with assisters known": int(len(K)), "fights": int(len(F))}
    def killer_share(x): return {r: r3((x.killer == r).mean()) for r in ROLES} | {"kills": int(len(x))}
    def ast(x): return {"assists per kill": r3(x.n_ast.mean()), "solo share": r3(x.solo.mean()), "kills": int(len(x))}
    T["killer role share by size"] = {s: killer_share(KK[KK["size"] == s]) for s in SIZES if (KK["size"] == s).any()}
    T["killer role share by phase x size"] = {f"{p} | {s}": killer_share(y) for (p, s), y in KK.groupby(["phase", "size"]) if len(y)}
    T["assists by size"] = {s: ast(K[K["size"] == s]) for s in SIZES if (K["size"] == s).any()}
    T["solo share by killer role x size"] = {r: {s: r3(K[(K.killer == r) & (K["size"] == s)].solo.mean()) for s in SIZES if ((K.killer == r) & (K["size"] == s)).any()} for r in ROLES}
    T["assist chance per kill by role x size (teammate of the killer)"] = {r: {s: r3(K[(K.killer != r) & (K["size"] == s)]["ast_" + r].mean()) for s in SIZES if ((K.killer != r) & (K["size"] == s)).any()} for r in ROLES}
    # one player's kills in one fight: players credited with a kill or assist (the feed can't see victims-only as "in", so both match)
    pf = PF[(PF.kills + PF.assists) > 0]
    T["player-fights with 2+ / 3+ / 4+ kills, by role x size (share of players credited in the fight)"] = {
        r: {s: [r3((y.kills >= 2).mean()), r3((y.kills >= 3).mean()), r3((y.kills >= 4).mean()), int(len(y))]
            for s in SIZES if len(y := pf[(pf.role == r) & (pf["size"] == s)])} for r in ROLES}
    sup = pf[pf.role == "sup"]
    T["support: fights with 3+ kills (count, of support player-fights)"] = [int((sup.kills >= 3).sum()), int(len(sup))]
    T["support: fights with 4+ kills (count)"] = int((sup.kills >= 4).sum())
    T["max kills by one player in a fight, by size (mean)"] = {s: r3(F[F["size"] == s].max_one_player.mean()) for s in SIZES if (F["size"] == s).any()}
    # side B (lost the fight's first kill)
    fb = F[F.kills_B > 0]
    T["fights where side B gets a kill (share, by size)"] = {s: r3((F[F["size"] == s].kills_B > 0).mean()) for s in SIZES if (F["size"] == s).any()}
    if "seen_B" in F:
        T["players seen per side by size (mean A, mean B)"] = {s: [r3(y.seen_A.mean()), r3(y.seen_B.mean())] for s in SIZES if len(y := F[F["size"] == s])}
        T["side B players seen when B gets kills, by size (mean)"] = {s: r3(y.seen_B.mean()) for s in SIZES if len(y := fb[fb["size"] == s])}
    for nm, b in (("B", 1), ("A", 0)):
        T[f"side {nm}'s kills: killer role share and solo share"] = killer_share(KK[KK.sideB == b]) | {"solo share": r3(K[K.sideB == b].solo.mean())}
    # kill participation of players credited in a fight
    pk = pf[pf.side_kills > 0]
    T["kill participation in the fight, players credited on a side with kills, by role x size"] = {
        r: {s: r3(((y.kills + y.assists) / y.side_kills).mean()) for s in SIZES if len(y := pk[(pk.role == r) & (pk["size"] == s)])} for r in ROLES}
    return T

with Run("memory_kill_credit", params={"fight_gap": FIGHT_GAP, "sizes": SIZES, "phases": PHASES, "split": config.SPLIT},
         inputs=[config.TL_MATCH, config.TL_EVENTS, config.OE_CSV]) as run:
    o = data.oe(["gameid", "league", "date", "side", "position", "champion"]); data.check(o); rl = data.roles(o)
    tm, ev, _ = data.timelines()
    TF, skipped, execs = timeline_fights(tm, ev, rl)
    R = {"timeline games skipped (a kill's champion not matched to a role)": skipped,
         "timeline executions left out (no killer champion)": execs}
    for split, fs in TF.items():
        K, PF, F = (pd.DataFrame(x) for x in fight_rows(fs, "timelines", split))
        R[f"timelines: {split}"] = {"games": int(F.game.nunique())} | tables(K, PF, F)
    Kr, PFr, Fr, single, multi, resolved = feed_fights(feed.full())
    K, PF, F = pd.DataFrame(Kr), pd.DataFrame(PFr), pd.DataFrame(Fr)
    R["feed: worlds"] = {"games": int(F.game.nunique()), "kills alone on their side in their frame": int(single),
                         "kills sharing a frame with another kill by the same side": int(multi),
                         "of those, assisters split from the K/D/A changes": int(resolved)} | tables(K, PF, F)
    for k_ in R:
        if isinstance(R[k_], dict): run.result(f"{k_}: kills", R[k_].get("kills"))
    run.save_json(OUT / "m7_kill_credit.json", R)
    print(json.dumps(R, indent=1))
