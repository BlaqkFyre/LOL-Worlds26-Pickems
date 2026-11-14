# research/lib: the shared research library (14 Nov 2026)

Built after Luke asked for a research system that is secure, accurate, maintainable and scalable. The slips it prevents:
- **A stale file read:** an older timeline match file (626 games) was read instead of the current one (640). Every path now lives in
  `config.py`; known stale copies are listed in `config.STALE`, and reading one through the library stops the run.
- **Results saved nowhere:** two scripts ran another script's code with `exec`, which reset their output path. Scripts now import shared code;
  outputs are written only through a run record, to a temporary file renamed when the run finishes.
- **Report numbers copied by hand:** report tables are now generated from the result files (`report.py`).
- **The same slow step repeated:** the step 1 pre-game lane predictions are computed once and cached (`lane_model.pregame_preds`); the
  78 MB Oracle's Elixir CSV is read once into a fast cached copy (`data.oe`).
- **Leaks between training and test games:** the splits (`splits.py`) check that no training row is on or after the test start.

| File | What it does |
|---|---|
| `config.py` | Every data path, split date, league list and expected size (`EXPECT`). Change a date or path here, nowhere else |
| `data.py` | Loaders with checks: `oe()` (cached by the CSV's SHA-256), `check()` (Worlds 94 games, 2,869 major games), `timelines()` (640 matched, every Worlds game), `roles()`, `worlds_days()` |
| `splits.py` | `worlds_by_day`, `fixed_2026`, `tuning`, each with a leak check |
| `fit.py` | Logistic and Poisson fits, log loss, Poisson deviance |
| `lane_model.py` | The step 1 lane-edge model (`lane_rows`, `Model`, `Current`) and `pregame_preds` (cached) |
| `runlog.py` | `Run`: a record per script run in `research/runs/` (script SHA-256 and git state, inputs' sizes, dates and SHA-256, parameters, key results, outputs, time, status) plus `research/runs/index.csv`; `latest(name)` |
| `compare.py` | Compares two result files value by value (proves a rebuilt script gives the same numbers) |
| `doccheck.py` | Checks every tracked Markdown doc: file paths and commit hashes in backticks exist (zipped local folders and temporary files allowed). Run it before committing doc changes: `python -I research/lib/doccheck.py` |
| `report.py` | Fills `<!-- table: name -->` blocks in a Markdown report from a tables module (e.g. `research/laning/report_tables.py`) |

**Writing a new script**
```python
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib import config, data, splits, fit
from lib.runlog import Run
with Run("my_test", params={...}, inputs=[config.OE_CSV, config.TL_MATCH]) as run:
    o = data.oe(["gameid", "league", "date", ...]); data.check(o)
    ...
    for day, train, test in splits.worlds_by_day(df): ...
    run.result("Worlds log loss", x)
    run.save_json(config.MODEL_DIR / "laning" / "my_test.json", R)
```
Run from the repo root: `python -I research/<folder>/<script>.py`. When the Oracle's Elixir file is replaced on purpose, update
`config.EXPECT` (the checks stop the scripts until then, so a new file is never used without noticing).

**Scripts on the library:** `research/laning/s5_*.py` (moved 14 Nov; rebuilt results compared value by value with the earlier ones).
Older scripts (`sim1`–`sim4`, `pog`, `build`) still read their own paths; move each one when it is next changed.
