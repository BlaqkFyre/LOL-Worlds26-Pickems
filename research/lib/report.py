"""Report tables generated from saved results, never typed by hand (14 Nov 2026).
In a Markdown report, a generated table sits between two markers:
    <!-- table: lane_edges_15 -->
    ...(replaced on every build)...
    <!-- /table -->
A tables module (e.g. research/laning/report_tables.py) defines TABLES = {name: function() -> markdown}, each reading result files
through lib (config paths). Text outside the markers is hand-written and never touched. Under each table the build adds a source line
naming the result file and its run record, so every number can be traced.
usage (repo root): python -I research/lib/report.py <report.md> <tables module path>"""
import sys, re, importlib.util
from pathlib import Path

def build(md_path, tables):
    p = Path(md_path); s = p.read_text(encoding="utf-8"); n = 0
    def rep(m):
        nonlocal n
        name = m.group(1).strip()
        if name not in tables: raise KeyError(f"no table named {name} in the tables module")
        n += 1; return f"<!-- table: {name} -->\n{tables[name]().strip()}\n<!-- /table -->"
    out = re.sub(r"<!-- table: (.*?) -->.*?<!-- /table -->", rep, s, flags=re.S)
    tmp = p.with_name(p.name + ".tmp"); tmp.write_text(out, encoding="utf-8"); tmp.replace(p)
    return n

if __name__ == "__main__":
    spec = importlib.util.spec_from_file_location("tables", sys.argv[2]); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    print(f"{build(sys.argv[1], mod.TABLES)} tables rebuilt in {sys.argv[1]}")
