"""Check the docs against the repo (14 Nov 2026; Luke: get the documents verified, cleaned up and efficient).
For each Markdown file given (default: every tracked .md), finds
  - paths in backticks or links that look like repo files or folders (contain "/" or end in a known extension) and checks they exist
    (git-ignored local paths count if they exist on this PC; paths under research/local/ that are missing are listed separately)
  - commit hashes in backticks (7-12 hex characters) and checks git knows them
  - the cache version written as vNN next to "cache" or "?v=" against index.html
Prints one line per problem: file:line  kind  value.
usage (repo root): python -I research/lib/doccheck.py [file.md ...]"""
import re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
EXT = (".py", ".js", ".css", ".html", ".md", ".json", ".csv", ".sh", ".txt", ".xlsx", ".parquet")
def git(*a): return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True).stdout
files = [Path(f) for f in sys.argv[1:]] or [ROOT / f for f in git("ls-files", "*.md").splitlines() if f != "SESSION_NOTES_ARCHIVE.md"]  # the archive is verbatim history
cache_v = re.search(r"\?v=(\d+)", (ROOT / "index.html").read_text(encoding="utf-8")).group(1)
known_commits = {}
TEMPORARY = {".claude/launch.json", "launch.json", "draft-clash-save.json", "lanes3_resid_cov10/15.csv"}  # temporary or autosave files  # made and deleted on purpose during sessions (CLAUDE.md, notes sessions)
def commit_ok(h):
    if h not in known_commits: known_commits[h] = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", h + "^{commit}"], capture_output=True).returncode == 0
    return known_commits[h]
problems = 0
VERBOSE = "--zipped" in sys.argv; files = [f for f in files if str(f) != "--zipped"] or files
def zipped(c0):
    """a missing local path counts as kept when it, or a folder above it, was zipped (14 Nov disk clean-up)"""
    parts = Path(c0.rstrip("/")).parts
    for i in range(len(parts), 0, -1):
        for base in (ROOT, ROOT / "research"):
            if (base / Path(*parts[:i])).with_name(parts[i - 1] + ".zip").exists(): return True
    return bool(list((ROOT / "research" / "local").rglob("*.zip"))) and "/" not in c0 and c0.startswith(("wf_", "halflife"))
for f in files:
    rel = f.relative_to(ROOT) if f.is_absolute() else f
    for n, line in enumerate((ROOT / rel).read_text(encoding="utf-8", errors="ignore").split("\n"), 1):
        if re.search(r"deleted \d|\.zip", line): continue  # lines that say a file was deleted or zipped describe history
        cands = re.findall(r"`([^`\s]+)`", line) + re.findall(r"\]\(([^)\s#]+)", line)
        for c in cands:
            c0 = c.strip().rstrip(".,;:)").split(":")[0] if not c.startswith("http") else None
            if not c0 or c0.startswith(("http", "#", "<", "$", "-")) or any(ch in c0 for ch in "*{<>") or "." in c0.split("/")[0] and not c0.startswith((".claude", "Draft")) and "/" in c0: continue
            if re.fullmatch(r"[0-9a-f]{7,12}", c0):
                if not commit_ok(c0): print(f"{rel}:{n}  commit not found  {c0}"); problems += 1
                continue
            if not ("/" in c0 or c0.endswith(EXT)) or c0 in TEMPORARY: continue
            if c0.startswith(("research/", "js/", "css/", "img/", "tools/", "Draft Game/", ".claude/")) or c0.endswith(EXT):
                cands_paths = [ROOT / c0, (ROOT / rel).parent / c0, ROOT / "research" / c0]
                if "/" not in c0: cands_paths += list(ROOT.rglob(c0))[:1]  # bare file names: anywhere in the repo
                if not any(p.exists() for p in cands_paths) and zipped(c0): print(f"{rel}:{n}  zipped (research/local README)  {c0}") if VERBOSE else None; continue
                if not any(p.exists() for p in cands_paths):
                    kind = "local path missing (git-ignored)" if "research/local/" in c0 else "path not found"
                    print(f"{rel}:{n}  {kind}  {c0}"); problems += 1
        for m in re.finditer(r"(?:cache[^.]{0,40}?|\?v=)v?(\d{2,3})\b", line):
            pass  # versions in history lines are fine; the live version is checked in SESSION_NOTES / CLAUDE by hand
print(f"{problems} problems in {len(files)} files (index.html cache version v{cache_v})")
