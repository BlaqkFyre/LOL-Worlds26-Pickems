"""Tables for research/memory/game-memory-report.md, built from the saved results (17 Nov 2026; lib/report.py fills them).
usage (repo root): python -I research/lib/report.py research/memory/game-memory-report.md research/memory/report_tables.py"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pandas as pd
from lib import config
from lib.runlog import latest

M = config.MODEL_DIR / "memory"
def J(name): return json.load(open(M / f"{name}.json", encoding="utf-8"))
def src(name, run_name):
    try:
        r = latest(run_name); rec = f"run record research/runs/{r['record']}, script {r['script']['path']} at commit {r['script']['git_commit']}" + (" with uncommitted edits" if r['script']['uncommitted_edits'] else "")
    except LookupError: rec = "no run record"
    return f"\n\n<sub>Source: research/model/memory/{name} ({rec}).</sub>"
pct = lambda v: "–" if v is None else f"{100 * v:.0f}%"
pct1 = lambda v: "–" if v is None else f"{100 * v:.1f}%"
f2 = lambda v: "–" if v is None else f"{v:.2f}"
mm = lambda s: f"{int(s // 60)}:{int(s % 60):02d}"

def clock():
    R = J("m0_clock"); rows = ["| Rule | Length v file (median) | Games 30 s+ off | Most over | Kills within 3 s of gol.gg | After 25:00 |", "|---|---|---|---|---|---|"]
    for k, v in R.items():
        rows.append(f"| {k} | {v['length v file: median s']:+.0f} s | {v['games more than 30 s off']} | {v['largest s over']:+.0f} s | {pct1(v['kills within 3 s of gol.gg'])} | {pct1(v['kills after 25:00 within 3 s'])} |")
    return "\n".join(rows) + src("m0_clock.json", "memory_clock")

def gaps():
    R = J("m1_fights"); h, d = R["gap between consecutive deaths (s): count per bin"], R["gap between consecutive deaths: count per second of bin width"]
    rows = ["| Seconds between deaths | " + " | ".join(h) + " |", "|---" * (len(h) + 1) + "|",
            "| Count | " + " | ".join(str(v) for v in h.values()) + " |", "| Per second of gap | " + " | ".join(f"{v:.1f}" for v in d.values()) + " |"]
    return "\n".join(rows) + src("m1_fights.json", "memory_fights")

def by_gap():
    R = J("m1_fights")["by gap"]; keys = list(next(iter(R.values())))
    rows = ["| Gap (s) | " + " | ".join(keys) + " |", "|---" * (len(keys) + 1) + "|"]
    for g, v in R.items(): rows.append(f"| {g} | " + " | ".join(f"{v[k]:g}" for k in keys) + " |")
    return "\n".join(rows) + src("m1_fights.json", "memory_fights")

def game4():
    F = pd.read_csv(M / "fights_G20.csv"); g = F[F.gameid == "LOLTMNT02_488489"]
    rows = ["| Fight | BLG deaths | GEN deaths | Gold swing (BLG) | Winner by gold | by kills | Players in (BLG v GEN) | BLG lead before |", "|---|---|---|---|---|---|---|---|"]
    side = {"blue": "BLG", "red": "GEN", "trade": "trade", "even": "even"}
    for r in g.itertuples():
        rows.append(f"| {mm(r.t_first)}–{mm(r.t_last)} | {r.deaths_blue} | {r.deaths_red} | {r.swing:+,.0f} | {side[r.win_gold]} | {side[r.win_kills]} | {r.in_blue} v {r.in_red} | {r.lead_before:+,.0f} |")
    return "\n".join(rows) + src("fights_G20.csv", "memory_fights")

def app_trace():
    A = J("app_sim_check")["trace"]
    return (f"App sim v50, seed 2650763346037409: {'BLG' if A['winner'] == 'blue' else 'GEN'} won in {A['length']}, kills {A['kills'][0]}–{A['kills'][1]}, towers "
            f"{A['towers'][0]}–{A['towers'][1]}.\n\n| Fights (kills 20 s apart) | Objectives |\n|---|---|\n| " + "<br>".join(A["fights"]) + " | " + "<br>".join(A["objectives"]) + " |"
            "\n\n<sub>Source: research/model/memory/app_sim_check.json (browser run of research/memory/app_sim_check.js; no run record).</sub>")

RESP_COLS = [("fights", "Fights", str), ("window median s", "Window (median s)", lambda v: f"{v:.0f}"), ("winner takes anything", "Winner takes anything", pct),
             ("tower winner per fight", "Towers W", f2), ("tower loser per fight", "Towers L", f2), ("inhib winner per fight", "Inhibs W", f2),
             ("dragon winner per fight", "Dragons W", f2), ("dragon loser per fight", "Dragons L", f2), ("baron winner per fight", "Barons W", f2),
             ("Nexus in window", "Nexus", pct), ("median s to winner's first objective", "First objective (median s)", lambda v: "–" if v is None else f"{v:.0f}"),
             ("loser contested", "Loser contests", pct), ("loser won a fight in window", "Loser wins a fight", pct)]
def resp_table(R, groups, cols=RESP_COLS):
    cols = [c for c in cols if c[0] in groups[0][1]]
    rows = ["| Group | " + " | ".join(c[1] for c in cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for label, b in groups: rows.append(f"| {label} | " + " | ".join(c[2](b.get(c[0])) for c in cols) + " |")
    return "\n".join(rows)

def responses():
    R = J("m2_responses")
    G = [("All fights", R["all"])] + [(k, v) for k, v in R["by phase"].items()] + [(f"Losers lost {k}", v) for k, v in R["by loser deaths"].items() if k != "0"] \
        + [(f"After 25:00, losers lost {k}", v) for k, v in R["after 25:00 by loser deaths"].items() if k != "0"]
    b = R["baseline per minute outside the windows (both sides)"]
    return (resp_table(R, G) + f"\n\nOutside every window (both sides together, per minute): towers {b['tower']:.3f}, inhibitors {b['inhib']:.3f}, Barons {b['baron']:.3f}, dragons {b['dragon']:.3f}. "
            f"In the windows the winner alone takes towers at {R['all']['tower winner per minute of window']:.2f} a minute and Barons at {R['all']['baron winner per minute of window']:.2f}."
            + src("m2_responses.json", "memory_responses"))

def snowball():
    R = J("m3_state"); f = R["snowball: fit (blue wins next fight)"]
    t = (f"Fit on {f['fights']} fights: per 1,000 gold lead {f['per 1,000 gold lead']:+.3f} (90% range {f['per 1,000 gold, 90% range'][0]:+.3f} to {f['per 1,000 gold, 90% range'][1]:+.3f}); "
         f"won the last fight {f['won the last fight']:+.3f} ({f['won the last fight, 90% range'][0]:+.3f} to {f['won the last fight, 90% range'][1]:+.3f}); at even gold the last fight's "
         f"winner wins the next {pct(f['won last, at even gold: win chance'])}, the loser {pct(f['lost last, at even gold'])}.\n\n")
    rows = ["| Last fight's winner, gold lead going into the next | Fights | Wins the next |", "|---|---|---|"]
    for k, v in R["snowball: last fight's winner wins the next, by its gold lead"].items(): rows.append(f"| {k} | {v['fights']} | {pct(v['wins next'])} |")
    for k, v in R["snowball: last fight's winner wins the next, by phase"].items(): rows.append(f"| {k} (any lead) | {v['fights']} | {pct(v['wins next'])} |")
    g = R["seconds from one fight to the next: median, 25%, 75%"]
    return t + "\n".join(rows) + f"\n\nSeconds from one fight to the next: median {g[0]}, middle half {g[1]}–{g[2]}." + src("m3_state.json", "memory_state")

def dead():
    R = J("m3_state")["share of game time dead, by role and phase"]; ph = list(next(iter(R.values())))
    rows = ["| Role | " + " | ".join(ph) + " |", "|---" * (len(ph) + 1) + "|"]
    for r, v in R.items(): rows.append(f"| {r} | " + " | ".join(pct1(v[p]) for p in ph) + " |")
    return "\n".join(rows) + src("m3_state.json", "memory_state")

def closeness():
    R = J("m3_state"); f = R["closeness: fit (blue wins the fight)"]
    rows = ["| Health gap going in (full health bars) | Fights | Side with more health wins | Median gold swing |", "|---|---|---|---|"]
    for k, v in R["closeness: by health gap going in (full bars)"].items(): rows.append(f"| {k} | {v['fights']} | {pct(v['side with more health wins'])} | {v['median |swing|']:,} |")
    rows2 = ["| More players alive going in | Fights | That side wins |", "|---|---|---|"]
    for k, v in R["numbers going in (alive): side with more alive wins"].items(): rows2.append(f"| +{k}{'+' if k == '3' else ''} | {v['fights']} | {pct(v['wins'])} |")
    return ("\n".join(rows) + "\n\n" + "\n".join(rows2) + f"\n\nFit (blue wins): per extra full health bar {f['per extra full health bar']:+.3f}, per 1,000 gold {f['per 1,000 gold lead']:+.3f}, "
            f"per extra player counted in the fight {f['per extra player in the fight']:+.3f} (biased: players are counted by losing health, which losing sides do more)." + src("m3_state.json", "memory_state"))

TL_COLS = RESP_COLS[:10] + [("loser contested", "Loser contests", pct), ("winner wins the next fight", "Wins the next fight", pct), ("fight winner wins the game", "Wins the game", pct)]
def timelines():
    R = J("m4_timelines"); G = []
    for name in ("Worlds (same games as the feed)", "other 2026 timelines"):
        G.append((f"{name}: all ({R[name]['games']} games)", R[name]["all"]))
        G += [(f"{name}: {k}", v) for k, v in R[name]["by phase"].items()]
        G += [(f"{name}: after 25:00, losers lost {k}", v) for k, v in R[name]["after 25:00 by loser deaths"].items()]
    return resp_table(None, G, TL_COLS) + src("m4_timelines.json", "memory_timelines")

def sim_compare():
    try: R = J("m5_sim_compare")
    except FileNotFoundError: return "(not run yet)"
    a, b = R["real (gol.gg timelines)"], R["current sim"]; keys = list(a["per game"])
    rows = [f"| Per game | Real ({a['games']} Worlds games) | Current research sim ({b['games']:,} sims) |", "|---|---|---|"]
    for k in keys: rows.append(f"| {k} | {a['per game'][k]:g} | {b['per game'][k]:g} |")
    G = [("Real: all", a["all"]), ("Sim: all", b["all"])]
    for p in a["by phase"]: G += [(f"Real: {p}", a["by phase"][p]), (f"Sim: {p}", b["by phase"].get(p, {}))]
    for k in a["after 25:00 by loser deaths"]: G += [(f"Real: after 25:00, losers lost {k}", a["after 25:00 by loser deaths"][k]), (f"Sim: after 25:00, losers lost {k}", b["after 25:00 by loser deaths"].get(k, {}))]
    return "\n".join(rows) + "\n\n" + resp_table(None, G, TL_COLS) + src("m5_sim_compare.json", "memory_sim_compare")

def app_shape():
    A = J("app_sim_check")
    try: R = J("m5_sim_compare"); r, s = R["real (gol.gg timelines)"]["per game"], R["current sim"]["per game"]
    except FileNotFoundError: r = s = None
    def v(d, k): return "–" if d is None else d[k]
    rows = ["| Measure | Real Worlds (gol.gg) | Research sim (94 Worlds games) | App sim v50 (final game 4 draft, 1,000 seeds) |", "|---|---|---|---|",
            f"| Fights with 6+ deaths on one side | {pct1(v(r, 'fights (kills 20 s apart) with 6+ deaths on one side')) if r else '–'} | {pct1(v(s, 'fights (kills 20 s apart) with 6+ deaths on one side')) if s else '–'} | {pct1(A['fights_6plus_one_side'])} |",
            f"| Objectives in the same second as the one before, per game | {v(r, 'objectives in the same second as the one before, per game')} | {v(s, 'objectives in the same second as the one before, per game')} | {A['same_second_objective_pairs_per_game']:.2f} |",
            f"| Nexus: seconds after the last kill (median) | {v(r, 'Nexus: seconds after the last kill, median')} | {v(s, 'Nexus: seconds after the last kill, median')} | {A['nexus_s_after_last_kill_median']} |",
            f"| Nexus more than 60 s after the last kill | {pct(v(r, 'Nexus more than 60 s after the last kill')) if r else '–'} | {pct(v(s, 'Nexus more than 60 s after the last kill')) if s else '–'} | {pct(A['nexus_over_60s_after_last_kill'])} |"]
    return "\n".join(rows) + "\n\n<sub>Sources: research/model/memory/m5_sim_compare.json (run memory_sim_compare) and app_sim_check.json (browser run, no run record).</sub>"

TABLES = {"clock": clock, "gaps": gaps, "by_gap": by_gap, "game4": game4, "app_trace": app_trace, "responses": responses, "snowball": snowball,
          "dead": dead, "closeness": closeness, "timelines": timelines, "sim_compare": sim_compare, "app_shape": app_shape}

def leads():
    R = J("m6_fight_kinds"); P = ["before 14:00", "14:00-25:00", "after 25:00"]
    k = R["1 kind share by phase"]; v = R["2 deaths by role: share of pick victims v share of all deaths"]
    vis = R["3 vision (estimate, 90% range, fights)"]; ob = R["4 objectives with a fight ending in the 90 s before"]; b = R["4 baseline: random seconds after 5:00"]
    out5, ent = R["5 big fights: share each role is not in"], R["5 big fights: entry after the first player in, median s and share 10 s+"]; tw = R["7 towers with no death in the 60 s before"]
    rows = ["| Phase | Fights | Picks | Big fights (8+) | Pick victims: top / jng / mid / bot / sup (share of all deaths) | Towers with no death in the 60 s before |", "|---|---|---|---|---|---|"]
    for p in P:
        roles = " / ".join(f"{pct(v[p][r][0])} ({pct(v[p][r][1])})" for r in ("top", "jng", "mid", "bot", "sup"))
        rows.append(f"| {p} | {k[p]['fights']} | {pct(k[p]['pick'])} | {pct(k[p]['big (8+)'])} | {roles} (n {v[p]['pick victims']}) | {pct(tw[p][0])} of {tw[p][1]} |")
    g = R["1 kind share by gold gap going in"]; gl = R["1 after 25:00, kind share by gold gap"]
    rows2 = ["| Gold gap going in | Picks (all) | Big (all) | Picks after 25:00 | Big after 25:00 |", "|---|---|---|---|---|"]
    for b_ in g: rows2.append(f"| {b_} | {pct(g[b_]['pick'])} | {pct(g[b_]['big (8+)'])} | {pct(gl[b_]['pick'])} | {pct(gl[b_]['big (8+)'])} |")
    rows3 = ["| Objective | Big fight in the 90 s before | Pick | Any fight |", "|---|---|---|---|"]
    for o_, x in ob.items(): rows3.append(f"| {o_} | {pct(x['big (8+)'])} | {pct(x['pick'])} | {pct(x['any fight'])} |")
    rows3.append(f"| Random second after 5:00 (chance) | {pct(b['big (8+)'])} | {pct(b['pick'])} | {pct(b['any'])} |")
    rows4 = ["| Role | Not in a big fight | Entry after the first player (median s) | Entering 10 s+ after |", "|---|---|---|---|"]
    for r in ("top", "jng", "mid", "bot", "sup"): rows4.append(f"| {r} | {pct(out5[r])} | {ent[r][0]:.0f} | {pct(ent[r][1])} |")
    rows5 = ["| Fights won, per +10 points of the team's share of… | Estimate | 90% range | Fights |", "|---|---|---|---|"]
    for kk, x in vis.items(): rows5.append(f"| {kk} | {x[0]:+.3f} | {x[1]:+.3f} to {x[2]:+.3f} | {x[3]} |")
    NL = chr(10)
    return (NL * 2).join(NL.join(r) for r in (rows, rows2, rows3, rows4, rows5)) + src("m6_fight_kinds.json", "memory_fight_kinds")

TABLES["leads"] = leads
