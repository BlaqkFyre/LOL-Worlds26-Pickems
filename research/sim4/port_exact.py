"""Exact port check (13 Nov 2026): the Python sim (research/sim3/s3_sim.py, unchanged) is run with a random generator that reproduces
js/sim-engine.js's generator draw for draw (sfc32 seeded by splitmix32, Box-Muller normals, Knuth Poisson, gamma-Poisson negative
binomial, cumulative-probability choice). With the same seed both sims should play the same game, so any game that differs points to a
porting bug. Writes per-game results for the games and versions in port_ref.json; port_check.html?exact=1 compares them.
usage (repo root): python -I research/sim4/port_exact.py port_ref.json <n_seeds> <out_json>"""
import os, sys, json, math, importlib.util
import numpy as np
RJ, NS, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
M32 = 0xFFFFFFFF
class JSRNG:
    def __init__(self, seed):
        seed = abs(seed); self.s = int(seed % 4294967296); self.hi = int(seed // 4294967296) & M32; self.spare = None
        def sm():
            self.s = (self.s + 0x9E3779B9) & M32; z = self.s ^ self.hi
            z = ((z ^ (z >> 16)) * 0x85EBCA6B) & M32; z = ((z ^ (z >> 13)) * 0xC2B2AE35) & M32; return (z ^ (z >> 16)) & M32
        self.a, self.b, self.c, self.d = sm(), sm(), sm(), sm()
        for _ in range(12): self.u32()
    def u32(self):
        a, b, c, d = self.a, self.b, self.c, self.d
        t = (a + b) & M32; a = b ^ (b >> 9); b = (c + (c << 3)) & M32; c = ((c << 21) | (c >> 11)) & M32; d = (d + 1) & M32
        t = (t + d) & M32; c = (c + t) & M32; self.a, self.b, self.c, self.d = a, b, c, d; return t
    def random(self):
        hi = self.u32(); lo = self.u32(); return (hi + lo / 4294967296) / 4294967296
    def _z(self):
        if self.spare is not None: z = self.spare; self.spare = None; return z
        u = 0.0
        while not u: u = self.random()
        v = self.random(); r = math.sqrt(-2 * math.log(u)); self.spare = r * math.sin(2 * math.pi * v); return r * math.cos(2 * math.pi * v)
    def normal(self, loc=0.0, scale=1.0): return loc + scale * self._z()
    def standard_normal(self, n): return np.array([self._z() for _ in range(n)])
    def uniform(self, lo, hi): return lo + (hi - lo) * self.random()
    def poisson(self, mu):
        if not (mu > 0): return 0
        if mu > 60: return max(0, round(self.normal(mu, math.sqrt(mu))))
        L = math.exp(-mu); k = 0; p = 1.0
        while True:
            k += 1; p *= self.random()
            if not (p > L): break
        return k - 1
    def gamma(self, shape):
        if shape < 1: u = self.random(); return self.gamma(1 + shape) * (u or 1e-300) ** (1 / shape)
        d = shape - 1 / 3; c = 1 / math.sqrt(9 * d)
        while True:
            while True:
                x = self._z(); v = 1 + c * x
                if v > 0: break
            v = v * v * v; u = self.random()
            if u < 1 - 0.0331 * x ** 4 or math.log(u) < 0.5 * x * x + d * (1 - v + math.log(v)): return d * v
    def negative_binomial(self, n, p): return self.poisson(self.gamma(n) * (1 - p) / p)
    def choice(self, a, p=None):
        vals = list(range(a)) if isinstance(a, (int, np.integer)) else list(a)
        if p is None: return vals[min(len(vals) - 1, int(math.floor(self.random() * len(vals))))]
        u = self.random(); acc = 0.0
        for v, q in zip(vals, p):
            acc += q
            if u < acc: return v
        return vals[-1]
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("s3_sim", os.path.join(HERE, "..", "sim3", "s3_sim.py")); sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)
sm.np = type("npx", (), {k: getattr(np, k) for k in dir(np) if not k.startswith("__")})  # the sim module's numpy, with its generator swapped
sm.np.random = type("rx", (), {"default_rng": staticmethod(lambda seed: JSRNG(seed))})
R = json.load(open(RJ)); res = {}
for v, cal in R["cal"].items():
    sim = sm.Sim(R["P"], cal); res[v] = {}
    for g, x in R["x"].items():
        res[v][g] = []
        for j in range(NS):
            o = sim.run(x, seed=1 + j)
            res[v][g].append([o["winner"], o["sec"], o["kills"], o["towers"], [len(o["dr"][0]), len(o["dr"][1])], o["ba"], None if math.isnan(o["g15"]) else round(o["g15"], 6)])
json.dump(res, open(OUT, "w")); print("done", {v: len(r) for v, r in res.items()})
