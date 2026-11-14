"""Run records: every script run saves what it read, what it was, what it found and what it wrote (14 Nov 2026).
    from lib.runlog import Run
    with Run("lane_edges", params={...}, inputs=[config.OE_CSV, ...]) as run:
        ...
        run.result("Worlds mse", 581491)          # key numbers, for the index and for report tables
        run.save_json(config.MODEL_DIR / "laning" / "lane_edges.json", R)   # written to a temp file, renamed when complete
The record (research/runs/<UTC time>_<name>.json) holds: the script's path, SHA-256 and git state (commit, and whether the script had
uncommitted edits), each input's size, modified time and SHA-256, the parameters, the results, every output with its SHA-256, the run's
start, end and status ("ok" or the error). research/runs/index.csv gets one line per run. A failed run still leaves a record (status
"failed") and never replaces an existing output."""
import hashlib, json, os, subprocess, sys, time, traceback, datetime as dt, csv
from pathlib import Path
from . import config

_HCACHE = config.CACHE_DIR / "hashes.json"

def sha256(path):
    """SHA-256 of a file, remembered by (path, size, modified time) so a large unchanged file is hashed once."""
    p = Path(path); st = p.stat(); key = f"{p.resolve()}|{st.st_size}|{int(st.st_mtime)}"
    try: memo = json.loads(_HCACHE.read_text())
    except Exception: memo = {}
    if key in memo: return memo[key]
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    memo[key] = h.hexdigest(); _HCACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _HCACHE.with_suffix(".tmp"); tmp.write_text(json.dumps(memo)); os.replace(tmp, _HCACHE)
    return memo[key]

def fingerprint(path):
    p = Path(path)
    if p in config.STALE: raise RuntimeError(f"stale input {p}: {config.STALE[p]}")
    if not p.exists(): raise FileNotFoundError(p)
    st = p.stat()
    return {"path": p.relative_to(config.ROOT).as_posix() if p.is_relative_to(config.ROOT) else str(p), "bytes": st.st_size,
            "modified": dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"), "sha256": sha256(p)}

def _git(*a):
    try: return subprocess.run(["git", "-C", str(config.ROOT), *a], capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception: return ""

def atomic_write(path, text):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True); tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(text, encoding="utf-8"); os.replace(tmp, p)

class Run:
    def __init__(self, name, params=None, inputs=()):
        self.name, self.params, self.inputs = name, dict(params or {}), [Path(x) for x in inputs]
        self.results, self.outputs, self._pending = {}, [], []
    def __enter__(self):
        self.t0 = time.time(); script = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else None
        rel = script.relative_to(config.ROOT).as_posix() if script and script.is_relative_to(config.ROOT) else str(script)
        self.rec = {"name": self.name, "started_utc": dt.datetime.utcnow().isoformat(timespec="seconds"),
                    "script": {"path": rel, "sha256": sha256(script) if script and script.exists() else None,
                               "git_commit": _git("rev-parse", "--short", "HEAD"),
                               "uncommitted_edits": bool(_git("status", "--porcelain", "--", rel)) if script else None},
                    "params": self.params, "inputs": [fingerprint(p) for p in self.inputs]}
        print(f"[run {self.name}] inputs checked: " + ", ".join(i["path"] for i in self.rec["inputs"]), flush=True)
        return self
    def result(self, key, value): self.results[key] = value
    def save_json(self, path, obj):
        """queue an output; written (temp file, then renamed) only if the run finishes without an error"""
        self._pending.append((Path(path), json.dumps(obj, indent=1, default=float)))
    def __exit__(self, et, ev, tb):
        ok = et is None
        if ok:
            for p, text in self._pending:
                atomic_write(p, text); self.outputs.append({"path": p.relative_to(config.ROOT).as_posix(), "sha256": sha256(p)})
        stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"); rp = config.RUNS_DIR / f"{stamp}_{self.name}.json"
        self.rec.update({"record": rp.name, "status": "ok" if ok else "failed", "error": None if ok else "".join(traceback.format_exception_only(et, ev)).strip(),
                         "seconds": round(time.time() - self.t0, 1), "results": self.results, "outputs": self.outputs,
                         "not_written_because_failed": [] if ok else [str(p) for p, _ in self._pending]})
        atomic_write(rp, json.dumps(self.rec, indent=1, default=float))
        idx = config.RUNS_DIR / "index.csv"; new = not idx.exists()
        with open(idx, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new: w.writerow(["run", "name", "status", "seconds", "script", "git_commit", "uncommitted_edits", "outputs"])
            w.writerow([rp.name, self.name, self.rec["status"], self.rec["seconds"], self.rec["script"]["path"], self.rec["script"]["git_commit"],
                        self.rec["script"]["uncommitted_edits"], " ".join(o["path"] for o in self.outputs)])
        print(f"[run {self.name}] {self.rec['status']} in {self.rec['seconds']} s; record {rp.relative_to(config.ROOT)}", flush=True)
        return False

def latest(name):
    """the newest successful run record of a name"""
    recs = sorted(config.RUNS_DIR.glob(f"*_{name}.json"))
    for p in reversed(recs):
        r = json.loads(p.read_text(encoding="utf-8"))
        if r["status"] == "ok": r.setdefault("record", p.name); return r
    raise LookupError(f"no successful run named {name}")
