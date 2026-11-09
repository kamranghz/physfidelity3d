"""Scene-cluster bootstrap estimators (Section 3.3 of the paper).

Scenes are resampled with replacement within each dataset, so every replicate keeps
12 YCB-V, 20 T-LESS and 10 Picasso scenes, and all methods share the same draw.
Confidence intervals are 2.5/97.5 percentiles over ``N_BOOT`` replicates.
"""

from collections.abc import Iterator

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .config import METHODS, N_BOOT


def scene_matrices(scenes: pd.DataFrame, column: str, dataset: str | None = None) -> list[np.ndarray]:
    """One (n_scenes, n_methods) array per dataset; datasets and scenes in sorted order."""
    if dataset is not None:
        scenes = scenes[scenes["dataset"] == dataset]
    return [
        g.pivot(index="scene_id", columns="method", values=column)[METHODS].to_numpy(float)
        for _, g in scenes.groupby("dataset")
    ]


def _resamples(seed: int, sizes: list[int]) -> Iterator[list[np.ndarray]]:
    rng = np.random.default_rng(seed)
    for _ in range(N_BOOT):
        yield [rng.integers(0, n, size=n) for n in sizes]


def _ci(samples: np.ndarray) -> tuple[float, float]:
    return float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))


def _mean_over_scenes(mats: list[np.ndarray], idx: list[np.ndarray]) -> np.ndarray:
    total = np.zeros(len(METHODS))
    for m, i in zip(mats, idx, strict=True):
        total += m[i].sum(axis=0)
    return total / sum(len(i) for i in idx)


def mean_ci(scenes: pd.DataFrame, column: str, seed: int, dataset: str | None = None) -> pd.DataFrame:
    """Per-method mean over scenes with a bootstrap CI."""
    mats = scene_matrices(scenes, column, dataset)
    boots = np.array([_mean_over_scenes(mats, i) for i in _resamples(seed, [len(m) for m in mats])])
    rows = []
    for j, method in enumerate(METHODS):
        lo, hi = _ci(boots[:, j])
        rows.append({"method": method, "mean": np.concatenate(mats)[:, j].mean(), "ci_low": lo, "ci_high": hi})
    return pd.DataFrame(rows)


def cap_hit_rate_ci(scenes: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Pair-weighted cap-hit rate (capped terms / all object pairs) with a bootstrap CI."""
    hits, pairs = scene_matrices(scenes, "cap_hits"), scene_matrices(scenes, "n_pairs")
    boots = []
    for idx in _resamples(seed, [len(m) for m in hits]):
        num = sum(h[i].sum(axis=0) for h, i in zip(hits, idx, strict=True))
        den = sum(p[i].sum(axis=0) for p, i in zip(pairs, idx, strict=True))
        boots.append(num / den)
    boots = np.array(boots)
    rate = np.concatenate(hits).sum(axis=0) / np.concatenate(pairs).sum(axis=0)
    return pd.DataFrame(
        [
            {"method": m, "mean": rate[j], "ci_low": _ci(boots[:, j])[0], "ci_high": _ci(boots[:, j])[1]}
            for j, m in enumerate(METHODS)
        ]
    )


def rank_probabilities(scenes: pd.DataFrame, column: str, seed: int) -> pd.DataFrame:
    """Probability that each method takes rank 1..5 (rank 1 = lowest mean)."""
    mats = scene_matrices(scenes, column)
    counts = np.zeros((len(METHODS), len(METHODS)))
    tie_break = np.arange(len(METHODS)) * 1e-12
    for idx in _resamples(seed, [len(m) for m in mats]):
        order = np.argsort(_mean_over_scenes(mats, idx) + tie_break, kind="mergesort")
        counts[order, np.arange(len(METHODS))] += 1
    probs = pd.DataFrame(counts / N_BOOT, columns=[f"rank{k}" for k in range(1, len(METHODS) + 1)])
    return probs.assign(method=METHODS)[["method", *probs.columns]]


def paired_difference_ci(scenes: pd.DataFrame, column: str, method: str, reference: str, seed: int) -> dict:
    """Mean scene-level difference ``method - reference`` with a bootstrap CI."""
    diffs = [m[:, METHODS.index(method)] - m[:, METHODS.index(reference)] for m in scene_matrices(scenes, column)]
    boots = [
        np.concatenate([d[i] for d, i in zip(diffs, idx, strict=True)]).mean()
        for idx in _resamples(seed, [len(d) for d in diffs])
    ]
    lo, hi = _ci(np.array(boots))
    return {"method": method, "reference": reference, "diff": np.concatenate(diffs).mean(), "ci_low": lo, "ci_high": hi}


def spearman_ci(scenes: pd.DataFrame, x: str, y: str, seed: int, dataset: str | None = None) -> dict:
    """Spearman rho over method-scene rows with a scene-cluster bootstrap CI."""
    xs, ys = scene_matrices(scenes, x, dataset), scene_matrices(scenes, y, dataset)
    boots = [
        spearmanr(
            np.concatenate([a[i].ravel() for a, i in zip(xs, idx, strict=True)]),
            np.concatenate([b[i].ravel() for b, i in zip(ys, idx, strict=True)]),
        ).statistic
        for idx in _resamples(seed, [len(m) for m in xs])
    ]
    lo, hi = _ci(np.array(boots))
    rho = spearmanr(np.concatenate(xs).ravel(), np.concatenate(ys).ravel()).statistic
    return {"rho": float(rho), "ci_low": lo, "ci_high": hi}
