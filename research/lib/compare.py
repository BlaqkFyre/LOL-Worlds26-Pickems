"""Compare two result JSON files value by value (14 Nov 2026): used to prove a rebuilt script gives the same numbers as before.
usage (repo root): python -I research/lib/compare.py <old.json> <new.json> [tolerance=1e-9]
Prints every key whose value differs (numbers beyond the relative tolerance, or any other change) and exits 1 if any do."""
import sys, json, math

def walk(a, b, path, out, tol):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a: out.append(f"{path}/{k}: only in new"); continue
            if k not in b: out.append(f"{path}/{k}: only in old"); continue
            walk(a[k], b[k], f"{path}/{k}", out, tol)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): out.append(f"{path}: length {len(a)} v {len(b)}"); return
        for i, (x, y) in enumerate(zip(a, b)): walk(x, y, f"{path}[{i}]", out, tol)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if a is None or b is None or (isinstance(a, float) and math.isnan(a)) != (isinstance(b, float) and math.isnan(b)): out.append(f"{path}: {a} v {b}")
        elif not (isinstance(a, float) and math.isnan(a)) and abs(a - b) > tol * max(1.0, abs(a), abs(b)): out.append(f"{path}: {a} v {b}")
    elif a != b: out.append(f"{path}: {a!r} v {b!r}")

if __name__ == "__main__":
    old, new = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3]); tol = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-9
    diffs = []; walk(old, new, "", diffs, tol)
    print(f"{len(diffs)} differences" + (":" if diffs else " (identical within tolerance)"))
    for d in diffs[:60]: print("  " + d)
    sys.exit(1 if diffs else 0)
