"""Small fitting and scoring helpers shared by the scripts (14 Nov 2026). The ridge terms only keep the solves stable."""
import numpy as np

def logistic(X, y, ridge=1e-3, iters=30):
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p)
        b += np.linalg.solve(X.T @ (X * W[:, None]) + ridge * np.eye(len(b)), X.T @ (y - p) - ridge * b)
    return b

def poisson(X, y, ridge=1e-3, iters=40):
    b = np.zeros(X.shape[1]); b[0] = np.log(max(1e-6, float(np.mean(y))))
    for _ in range(iters):
        mu = np.exp(np.clip(X @ b, -20, 20)); b += np.linalg.solve((X * mu[:, None]).T @ X + ridge * np.eye(len(b)), X.T @ (y - mu) - ridge * b)
    return b

def sigmoid(z): return 1 / (1 + np.exp(-z))
def log_loss(y, p): p = np.clip(p, 1e-6, 1 - 1e-6); return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
def poisson_dev(y, mu): mu = np.clip(mu, 1e-9, None); return float(np.mean(2 * (np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0) - (y - mu))))
