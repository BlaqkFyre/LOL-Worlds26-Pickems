"""Tables for research/laning/step1-report.md, built from the saved results (14 Nov 2026; lib/report.py fills them).
usage (repo root): python -I research/lib/report.py research/laning/step1-report.md research/laning/report_tables.py"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib import config
from lib.runlog import latest

def J(name): return json.load(open(config.MODEL_DIR / "laning" / f"{name}.json", encoding="utf-8"))
def src(name, run_name=None):
    try: r = latest(run_name or name); rec = f"run record research/runs/{r['record']}, script {r['script']['path']} at commit {r['script']['git_commit']}" + (" with uncommitted edits" if r['script']['uncommitted_edits'] else "")
    except LookupError: rec = "no run record"
    return f"\n\n<sub>Source: research/model/laning/{name}.json ({rec}).</sub>"
def k(v): return f"{v / 1000:.0f}k"
def pct(v): return f"{100 * v:.1f}%"

def lane_edges():
    R = J("lane_edges"); W15, S15, W10 = R["y15"]["Worlds day by day"], R["y15"]["2026 from 1 Sep (non-Worlds)"], R["y10"]["Worlds day by day"]
    rows = ["| Version (each adds one input) | Worlds error at 15 | Worlds right | 2026 error at 15 | 2026 right | Worlds error at 10 |", "|---|---|---|---|---|---|"]
    names = [n for n in W15 if n != "current sim inputs"] + ["current sim inputs"]
    label = {"current sim inputs": "Current sim's lane inputs (skill gap, champion gold, team strength)"}
    for n in names:
        rows.append(f"| {label.get(n, n)} | {k(W15[n]['mse'])} | {pct(W15[n]['winner_right'])} | {k(S15[n]['mse'])} | {pct(S15[n]['winner_right'])} | {k(W10[n]['mse'])} |")
    return "\n".join(rows) + src("lane_edges")

def fight_winner():
    R = J("fight_winner"); W, S = R["Worlds day by day"], R["2026 from 1 Sep (non-Worlds)"]
    rows = [f"| Version | Worlds day by day ({W['n']} fights) | 2026 from 1 Sep ({S['n']}) |", "|---|---|---|"]
    for n in W:
        if n != "n": rows.append(f"| {n} | {W[n]:.4f} | {S[n]:.4f} |")
    return "\n".join(rows) + src("fight_winner")

def actions(section, title):
    R = J("lane_actions")[section]; W, S = R["Worlds day by day"], R["2026 from 1 Sep (non-Worlds)"]
    rows = [f"| Version | Worlds ({W['n']}) | 2026 ({S['n']}) |", "|---|---|---|"]
    for n in W:
        if n != "n": rows.append(f"| {n} | {W[n]:.4f} | {S[n]:.4f} |")
    return "\n".join(rows) + src("lane_actions")

def gank_state():
    R = J("gank_state"); rows = ["| Question | Constants only (Worlds / 2026) | With game state (Worlds / 2026) |", "|---|---|---|"]
    for key, label in [("A. gank lane (jungler's early kills)", "Which lane the jungler's early kills are in"),
                       ("C. mid roams: lane of the mid's early kills", "Which lane the mid's early kills are in"),
                       ("C. support roams: lane of the support's early kills", "Which lane the support's early kills are in")]:
        W, S = R[key]["Worlds day by day"], R[key]["2026 from 1 Sep (non-Worlds)"]
        rows.append(f"| {label} ({R[key]['kills']:,} kills) | {W['lane constants']:.4f} / {S['lane constants']:.4f} | {W['game state']:.4f} / {S['game state']:.4f} |")
    B = R["B. gank pace (jungler-involved kills per side-minute, Poisson deviance)"]; W, S = B["Worlds day by day"], B["2026 from 1 Sep (non-Worlds)"]
    rows.append(f"| Jungler early kills per minute ({B['side-minutes']:,} side-minutes) | {W['minute only']:.4f} / {S['minute only']:.4f} | {W['+ game state']:.4f} / {S['+ game state']:.4f} |")
    return "\n".join(rows) + src("gank_state")

TABLES = {"lane_edges": lane_edges, "fight_winner": fight_winner, "gank_state": gank_state,
          "plates": lambda: actions("A. plates (Poisson deviance)", "plates"),
          "first_dragon": lambda: actions("B. first dragon taker (log loss)", "first dragon"),
          "grubs": lambda: actions("C. grub taker (log loss)", "grubs")}
