"""Tables for research/memory/base-push-report.md, built from research/model/memory/m17_base_push_state.json (27 Nov 2026; lib/report.py fills them).
usage (repo root): python -I research/lib/report.py research/memory/base-push-report.md research/memory/base_push_report_tables.py"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib import config
from lib.runlog import latest

NAME = "m17_base_push_state"
def J(): return json.load(open(config.MODEL_DIR / "memory" / f"{NAME}.json", encoding="utf-8"))
def src():
    try:
        r = latest("memory_base_push_state"); rec = f"run record research/runs/{r['record']}, script {r['script']['path']} at commit {r['script']['git_commit']}" + (" with uncommitted edits" if r['script']['uncommitted_edits'] else "")
    except LookupError: rec = "no run record"
    return f"\n\n<sub>Source: research/model/memory/{NAME}.json ({rec}).</sub>"
f4 = lambda v: "–" if v is None else f"{v:.4f}"
pct = lambda v: "–" if v is None else f"{100 * v:.0f}%"
q = lambda a: "–" if not a else " / ".join(f"{x:g}" for x in a)

def port():
    P = J()["port check"]; d = P["app copy refit v js/sim-tables.js base_push_fight (differences)"]
    return (f"| Check | Result |\n|---|---|\n| App copy's refit of today's inputs v `base_push_fight` in `js/sim-tables.js` | "
            f"{'identical' if P['identical'] else 'differs'} ({len(d)} coefficients, largest difference {max(abs(v) for v in d.values()):g}) |") + src()

def scores():
    R = J(); rows = ["| Version | Research: training | Research: from 1 Sep | Research: Worlds | App copy: games to 10 Nov (in-sample) |", "|---|---|---|---|---|"]
    for k, v in R["research"]["versions"].items():
        a = R["app"]["versions"][k]
        rows.append(f"| {k} | {f4(v['train']['logloss'])} | {f4(v['test']['logloss'])} | {f4(v['worlds']['logloss'])} | {f4(a['train']['logloss'])} |")
    n = R["research"]["versions"]["today's inputs"]
    rows.append(f"| team-minutes | {n['train']['n']} | {n['test']['n']} | {n['worlds']['n']} | {R['app']['versions']['today' + chr(39) + 's inputs']['train']['n']} |")
    return "\n".join(rows) + src()

def choice():
    R = J(); rows = ["| Version | Research copy | App copy |", "|---|---|---|"]
    a, b = R["research"]["choice"], R["app"]["choice"]
    for k in a["later-half log loss"]: rows.append(f"| {k} | {f4(a['later-half log loss'][k])} | {f4(b['later-half log loss'][k])} |")
    rows.append(f"| **chosen** | {a['left form']}{', interaction kept' if a['interaction kept'] else ''} | {b['left form']}{', interaction kept' if b['interaction kept'] else ''} |")
    rows.append(f"| fit / check minutes (split {a['split_date']}) | {a['n_fit']} / {a['n_check']} | {b['n_fit']} / {b['n_check']} |")
    return "\n".join(rows) + src()

def coefs():
    R = J(); ra, ap = R["research"]["versions"], R["app"]["versions"]
    keys = list(ap["all (chosen)"]["coef"]); rk = ra["all (chosen)"]["coef"]
    rows = ["| Input | Today (app) | New fit, app copy | New fit, research copy |", "|---|---|---|---|"]
    t = ap["today's inputs"]["coef"]
    for k in dict.fromkeys(list(t) + keys + list(rk)):
        g = lambda d: "–" if k not in d else f"{d[k]:+.3f}"
        rows.append(f"| {k} | {g(t)} | {g(ap['all (chosen)']['coef'])} | {g(rk)} |")
    return "\n".join(rows) + src()

def descriptive():
    D = J()["app"]["descriptive"]; rows = []
    for title, d in D.items():
        rows += [f"**{title.replace(' (train)', '')}** (games to 10 Nov)", "", "| Value | " + " | ".join(d) + " |", "|---" * (len(d) + 1) + "|",
                 "| Share of minutes a push starts | " + " | ".join(pct(v[0]) for v in d.values()) + " |",
                 "| Team-minutes | " + " | ".join(str(v[1]) for v in d.values()) + " |", ""]
    return "\n".join(rows).rstrip() + src()

def sizes():
    R = J(); rows = ["| Structures left at the push's start | Pushes (to 1 Sep / to 10 Nov) | Size shares (to 10 Nov) | Push ends in the Nexus (to 10 Nov) |", "|---|---|---|---|"]
    a, b = R["tables, training games (before 1 Sep)"]["push sizes by structures left (share, n, ends in the Nexus)"], R["tables, app games (before 10 Nov)"]["push sizes by structures left (share, n, ends in the Nexus)"]
    for L in ("0", "1", "2", "3"):
        rows.append(f"| {L} | {a[L]['n']} / {b[L]['n']} | " + ", ".join(f"{s}: {pct(p)}" for s, p in zip(b[L]['sizes'], b[L]['p'])) + f" | {pct(b[L]['ends_in_nexus'])} |")
    return "\n".join(rows) + src()

def gaps():
    R = J(); b = R["tables, app games (before 10 Nov)"]["base gaps s (10/25/50/75/90%), n"]; a = R["tables, training games (before 1 Sep)"]["base gaps s (10/25/50/75/90%), n"]
    rows = ["| Previous > this structure | Gap s, 10/25/50/75/90% (to 10 Nov) | Gaps (to 1 Sep / to 10 Nov) |", "|---|---|---|"]
    for k, v in b.items(): rows.append(f"| {k} | {q(v[0])} | {a.get(k, [None, 0])[1]} / {v[1]} |")
    p = R["tables, app games (before 10 Nov)"]["base gaps pooled"]; rows.append(f"| all base gaps pooled | {q(p[0])} | {R['tables, training games (before 1 Sep)']['base gaps pooled'][1]} / {p[1]} |")
    return "\n".join(rows) + src()

def nexus():
    R = J(); b = R["tables, app games (before 10 Nov)"]; a = R["tables, training games (before 1 Sep)"]
    k = "Nexus from the last kill by structures left at the fight's start s (10/25/50/75/90%), n"
    rows = ["| Structures left at the fight's start | Won fights (to 10 Nov) | Nexus in the push | Nexus from the last kill s, 10/25/50/75/90% (to 10 Nov) |", "|---|---|---|---|"]
    for L in ("0", "1", "2", "3"):
        w = b["won fights by structures left (lane open)"][L]; n = b[k][L][1]
        rows.append(f"| {L} | {w} | {n} ({pct(n / w if w else None)}) | {q(b[k][L][0])} |")
    return "\n".join(rows) + src()

TABLES = {"port": port, "scores": scores, "choice": choice, "coefs": coefs, "descriptive": descriptive, "sizes": sizes, "gaps": gaps, "nexus": nexus}
