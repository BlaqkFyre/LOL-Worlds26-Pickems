"""Tables for research/memory/fight-window-report.md, built from research/model/memory/m21_fight_window.json (27 Nov 2026; lib/report.py fills them).
usage (repo root): python -I research/lib/report.py research/memory/fight-window-report.md research/memory/fight_window_report_tables.py"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib import config
from lib.runlog import latest

NAME = "m21_fight_window"
def J(): return json.load(open(config.MODEL_DIR / "memory" / f"{NAME}.json", encoding="utf-8"))
def src():
    try:
        r = latest("memory_fight_window"); rec = f"run record research/runs/{r['record']}, script {r['script']['path']} at commit {r['script']['git_commit']}" + (" with uncommitted edits" if r['script']['uncommitted_edits'] else "")
    except LookupError: rec = "no run record"
    return f"\n\n<sub>Source: research/model/memory/{NAME}.json ({rec}).</sub>"
f4 = lambda v: "–" if v is None else f"{v:.4f}"
pct = lambda v: "–" if v is None else f"{100 * v:.0f}%"

def port():
    P = J()["port check"]; rows = ["| Table in `js/sim-tables.js` | App copy refit on all rows | Largest difference |", "|---|---|---|"]
    d = P["base_push_fight (differences)"]; rows.append(f"| `base_push_fight` | {'identical' if P['identical']['base push'] else 'differs'} ({len(d)} coefficients) | {max(abs(v) for v in d.values()):g} |")
    for k, d in P["monsters (differences)"].items():
        rows.append(f"| `monsters.{k}` | {'identical' if all(abs(v) < 1e-9 for v in d.values()) else 'differs'} ({len(d)}) | {max(abs(v) for v in d.values()):g} |")
    return "\n".join(rows) + src()

def counts():
    R = J(); rows = ["| | Research copy | App copy |", "|---|---|---|"]
    a, b = R["research"]["counts"], R["app"]["counts"]
    rows.append(f"| won fights | {a['won fights']} | {b['won fights']} |")
    rows.append(f"| base races left out | {a['censored (base race)']} | {b['censored (base race)']} |")
    rows.append(f"| step rows: training / from 1 Sep / Worlds | {' / '.join(str(a['step rows by split'][s]) for s in ('train', 'test', 'worlds'))} | {b['step rows by split']['train']} (all training) |")
    for k in sorted(set(a["steps (train) by next"]) | set(b["steps (train) by next"]), key=lambda k: -a["steps (train) by next"].get(k, 0)):
        rows.append(f"| training steps ending in {k} | {a['steps (train) by next'].get(k, 0)} | {b['steps (train) by next'].get(k, 0)} |")
    return "\n".join(rows) + src()

def scores():
    S = J()["research"]["window"]["held-out scores"]; rows = ["| Games | Steps | Takes | Stage 1 log loss: fit / base share | Stage 2 log loss: fit / equal among those up |", "|---|---|---|---|---|"]
    for s, lab in (("train", "training (before 1 Sep)"), ("test", "from 1 Sep"), ("worlds", "Worlds")):
        v = S.get(s)
        if v: rows.append(f"| {lab} | {v['steps']} | {v['takes']} | {f4(v['stage 1 log loss (fit | base share)'][0])} / {f4(v['stage 1 log loss (fit | base share)'][1])} | {f4(v['stage 2 log loss (fit | equal among those up)'][0])} / {f4(v['stage 2 log loss (fit | equal among those up)'][1])} |")
    return "\n".join(rows) + src()

def coefs():
    R = J(); a = R["app"]["window"]; r = R["research"]["window"]
    rows = ["| Stage 1 input (take something v reset) | App copy | Research copy |", "|---|---|---|"]
    for k, v in a["stage 1 coef"].items(): rows.append(f"| {k} | {v:+.3f} | {r['stage 1 coef'][k]:+.3f} |")
    rows += ["", "| Stage 2 (which one), app copy | intercept | per player alive ahead | per 10 s until all back |", "|---|---|---|---|"]
    for k, v in a["stage 2 coef"].items(): rows.append(f"| {k} | {v['intercept']:+.3f} | {v['per_alive_diff']:+.3f} | {v['per_10s_until_all_back']:+.3f} |")
    return "\n".join(rows) + src()

def replay():
    R = J()["research"]["window"]["replay (no sim): fights, real share, fitted share"]
    keys = list(dict.fromkeys(k for s in R.values() for k in s if k != "any objective"))
    rows = ["| Won fights | Training: n, real, fitted | From 1 Sep: n, real, fitted | Worlds: n, real, fitted |", "|---|---|---|---|"]
    cell = lambda s, k: "–" if k not in R.get(s, {}) else f"{R[s][k][0]}, {pct(R[s][k][1])}, {pct(R[s][k][2])}"
    for k in keys: rows.append(f"| {k} | {cell('train', k)} | {cell('test', k)} | {cell('worlds', k)} |")
    return "\n".join(rows) + src()

def times():
    T = J()["app"]["window"]["take times s (21 quantiles; option x players alive, n >= 20)"]; N = J()["app"]["window"]["takes (train) by option x players alive"]
    rows = ["| Option | Winners 3+ up: n, median s | 1-2 up | Even or behind | Pooled median |", "|---|---|---|---|---|"]
    md = lambda q: "–" if not q else f"{q[10]:g}"
    for k in J()["options"]:
        c = lambda b: f"{N[k][b]}, {md(T.get(k, {}).get(b))}"
        rows.append(f"| {k} | {c('ahead 3+')} | {c('ahead 1-2')} | {c('even or behind')} | {md(T.get(k, {}).get('pooled'))} |")
    return "\n".join(rows) + src()

def minute():
    R = J(); rows = ["| Per-minute draw (app copy) | Rows left out (inside windows) | Rows | Held-out log loss outside windows, research copy (refit / all-row fit): from 1 Sep, Worlds |", "|---|---|---|---|"]
    a, r = R["app"], R["research"]
    h = r["base push, outside windows"]["held-out log loss outside windows (refit | fit on all rows)"]
    rows.append(f"| base push | {a['base team-minutes left out']} | {sum(a['base push, all rows (port check)']['n'].values())} | {f4(h['test'][0])} / {f4(h['test'][1])}, {f4(h['worlds'][0])} / {f4(h['worlds'][1])} |")
    rows.append(f"| monsters (all kinds) | {a['monster minutes left out']} | {a['monster minutes']} | per kind below |")
    rows += ["", "| Monster | Taken / minutes up (all rows) | Outside windows | Research held-out log loss from 1 Sep: refit on its rows (outside windows) / all-row fit on all rows (different rows: not a like-for-like score) |", "|---|---|---|---|"]
    for k, v in a["monsters, all rows (port check)"].items():
        e = a["monsters, outside windows"].get(k, {}); re_, rf = r["monsters, outside windows"].get(k, {}), r["monsters, all rows (port check)"].get(k, {})
        rows.append(f"| {k} | {v['taken']} / {v['minutes_up']} | {e.get('taken', '–')} / {e.get('minutes_up', '–')} | {f4(re_.get('log loss test'))} / {f4(rf.get('log loss test'))} |")
    return "\n".join(rows) + src()

def K():
    return json.load(open(config.MODEL_DIR / "memory" / "m22_app_check.json", encoding="utf-8"))["m22"]
ksrc = lambda: "\n\n<sub>Source: research/model/memory/m22_app_check.json (research/memory/m22_app_check.js run in a local app tab); real objectives a game from research/model/memory/m20_fight_windows.json (640 gol.gg timelines).</sub>"

def appcheck():
    A = K(); on, off, re_ = A["v55"], A["v55_off"], A["real_72"]
    q = lambda v: " / ".join(f"{x:g}" for x in v)
    rows = [f"| {A['drafts']} Worlds drafts x {A['seeds']} seeds | v55 (fight window on) | fight window off (= v54) | Real (the same 72 games) |", "|---|---|---|---|"]
    rows.append(f"| blue win | {pct(on['blue win'])} | {pct(off['blue win'])} | {pct(re_['blue win'])} |")
    rows.append(f"| length min (10 / 25 / 50 / 75 / 90%) | {q(on['length min (10/25/50/75/90%)'])} | {q(off['length min (10/25/50/75/90%)'])} | {q(re_['length min (10/25/50/75/90%)'])} |")
    for k in ("45+ min", "50+ min"): rows.append(f"| {k} | {pct(on[k])} | {pct(off[k])} | {pct(re_[k])} |")
    rows.append(f"| kills a game | {on['kills per game']:.1f} | {off['kills per game']:.1f} | {re_['kills per game']:.1f} |")
    R20 = json.load(open(config.MODEL_DIR / "memory" / "m20_fight_windows.json", encoding="utf-8")); n = R20["games"]; c = R20["objectives inside a won-fight window / all (by kind)"]
    real = {"dragon": c["dragon"][1], "elder": c["elder"][1], "baron": c["baron"][1], "herald": c["herald"][1], "inhib": c["inhib"][1], "nexus": c["nexus"][1],
            "tower": c["outer"][1] + c["T3"][1] + c["nxt"][1]}
    rows += ["", f"| Objectives a game (both sides) | v55 | off (= v54) | Real ({n} timelines, 2026) |", "|---|---|---|---|"]
    po, pf = on["objectives per game (both sides; grubs = takes, towers all tiers)"], off["objectives per game (both sides; grubs = takes, towers all tiers)"]
    for k in ("dragon", "elder", "baron", "herald", "tower", "inhib", "nexus"): rows.append(f"| {k}{' (all tiers)' if k == 'tower' else ''} | {po.get(k, 0):.2f} | {pf.get(k, 0):.2f} | {real[k] / n:.2f} |")
    rows += ["", "| Player of the Game by role | v55 | off (= v54) |", "|---|---|---|"]
    for r in ("top", "jng", "mid", "bot", "sup"): rows.append(f"| {r} | {pct(on['Player of the Game by role'][r])} | {pct(off['Player of the Game by role'][r])} |")
    rp = A.get("replay", {}); rows += ["", "| Replay check (72 drafts x 20 seeds, fingerprint of every game record) | v54 | v55 with fight_window off | Identical |", "|---|---|---|---|"]
    for k, v in rp.items(): rows.append(f"| {k} sim | `{v['v54']}` | `{v['v55 off']}` | {'yes' if v['identical'] else 'no'} |")
    return "\n".join(rows) + ksrc()

def simwindow():
    S = K()["v55"]["window shares (won fights, share taking it in the 60 s chain)"]; Rr = J()["research"]["window"]["replay (no sim): fights, real share, fitted share"]
    cell = lambda s, k: "–" if k not in Rr.get(s, {}) else f"{pct(Rr[s][k][1])} ({Rr[s][k][0]})"
    rows = ["| Won fights | v55 sim: share (fights) | Real, training | Real, from 1 Sep | Real, Worlds |", "|---|---|---|---|---|"]
    for k in sorted(S, key=lambda k: (k.split(",")[0], k)):
        rows.append(f"| {k} | {pct(S[k][1])} ({S[k][0]}) | {cell('train', k)} | {cell('test', k)} | {cell('worlds', k)} |")
    return "\n".join(rows) + ksrc() + "\n<sub>Real: m21_fight_window.json, research copy (the replay table's real column; same 60 s chain).</sub>"

def playtest():
    M = config.MODEL_DIR / "memory"; a = json.load(open(M / "m22_series_playtest.json", encoding="utf-8")); b = json.load(open(M / "m15_series_playtest.json", encoding="utf-8"))
    re_ = b["real for comparison (640 gol.gg timelines)"]; q = lambda v: " / ".join(f"{x:g}" for x in v) if v else "–"
    rows = [f"| 100 Bo5 Fearless series, AI drafts both sides | v55 ({a['games']} games) | v54 ({b['games']} games) | Real (640 timelines) |", "|---|---|---|---|"]
    rows.append(f"| errors | {len(a['errors'])} | {len(b['errors'])} | |")
    rows.append(f"| replay from seed matches the game record | {a['replay matches record']} | {b['replay from seed matches the game record']} | |")
    rows.append(f"| exports with every game's play-by-play / NaN or undefined | {a['export: series with a play-by-play block for every game']} / {a['export: NaN/undefined in text']} | {b['export: series with a play-by-play block for every game']} / {b['export: NaN/undefined in text']} | |")
    rows.append(f"| length min (10 / 25 / 50 / 75 / 90%) | {q(a['length min (10/25/50/75/90%)'])} | {q(b['length min (10/25/50/75/90%)'])} | {q(re_['length min (10/25/50/75/90%)'])} |")
    rows.append(f"| 45+ min | {a['45+ min %']:g}% | {b['45+ min %']:g}% | {100 * re_['45+']:g}% |")
    rows.append(f"| kills a game (10 / 25 / 50 / 75 / 90%) | {q(a['kills per game (10/25/50/75/90%)'])} | {q(b['kills per game (10/25/50/75/90%)'])} | median {re_['kills median']} |")
    rows.append(f"| Nexus from the last kill s (10 / 25 / 50 / 75 / 90%) | {q(a['Nexus from the last kill s (10/25/50/75/90%)'])} | {q(b['Nexus from the last kill s (10/25/50/75/90%)'])} | median {re_['Nexus from the last kill median s']} |")
    rows.append(f"| Nexus 60 s+ after the last kill | {a['Nexus 60 s+ after the last kill %']:g}% | {b['Nexus 60 s+ after the last kill %']:g}% | |")
    rows.append(f"| first blood before 0:30 / 1:00 / 3:00 | {q(a['first blood before 0:30 / 1:00 / 3:00 %'])}% | {q(b['first blood before 0:30 / 1:00 / 3:00 %'])}% | {q(re_['first blood before 0:30 / 1:00 / 3:00 %'])}% |")
    rows.append(f"| support 4+ kills in one fight | {a['support 4+ kills in one fight (count)']} | {b['support 4+ kills in one fight (count)']} | |")
    rows.append(f"| blue win | {a['blue win %']:g}% | {b['blue win %']:g}% | |")
    return "\n".join(rows) + "\n\n<sub>Source: research/model/memory/m22_series_playtest.json (v55) and m15_series_playtest.json (v54), both from research/memory/m15_series_playtest.js in a new local tab, same team pairs.</sub>"

TABLES = {"playtest": playtest, "port": port, "counts": counts, "scores": scores, "coefs": coefs, "replay": replay, "times": times, "minute": minute, "appcheck": appcheck, "simwindow": simwindow}
