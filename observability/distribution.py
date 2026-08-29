"""Statistical Distribution Shift and Drift Detection Engine.

Methods:
- Two-Sample Kolmogorov-Smirnov (KS) Statistic (maximum empirical CDF distance).
- Population Stability Index (PSI) via quantile binning.
- Robust Ratio / Mean Ratio for small samples.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def _calculate_ks_statistic(data1: np.ndarray, data2: np.ndarray) -> float:
    """Calculate 2-sample Kolmogorov-Smirnov maximum empirical CDF distance D."""
    n1 = len(data1)
    n2 = len(data2)
    data_all = np.concatenate([data1, data2])
    data_all.sort()

    cdf1 = np.searchsorted(np.sort(data1), data_all, side="right") / n1
    cdf2 = np.searchsorted(np.sort(data2), data_all, side="right") / n2

    d_stat = float(np.max(np.abs(cdf1 - cdf2)))
    return d_stat


def _calculate_psi(current: np.ndarray, baseline: np.ndarray, num_bins: int = 5) -> float:
    """Calculate Population Stability Index (PSI) using baseline quantile binning."""
    percentiles = np.linspace(0, 100, num_bins + 1)
    bins = np.percentile(baseline, percentiles)
    bins[0] = -np.inf
    bins[-1] = np.inf

    base_counts, _ = np.histogram(baseline, bins=bins)
    curr_counts, _ = np.histogram(current, bins=bins)

    # Avoid zero division with Laplace smoothing
    base_pct = (base_counts + 1e-4) / (len(baseline) + 1e-4 * num_bins)
    curr_pct = (curr_counts + 1e-4) / (len(current) + 1e-4 * num_bins)

    psi_value = float(np.sum((curr_pct - base_pct) * np.log(curr_pct / base_pct)))
    return max(0.0, psi_value)


def detect_distribution_shift(
    current_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    ratio_threshold: float = 3.0,
    ks_threshold: float = 0.35,
    psi_threshold: float = 0.25,
) -> dict[str, Any]:
    """Detect statistical distribution shift using multi-signal evaluation (KS, PSI, and Mean Ratio)."""
    cur = np.asarray(list(current_values), dtype=float)
    base = np.asarray(list(baseline_values), dtype=float)

    if cur.size == 0 or base.size == 0:
        return {
            "is_anomaly": False,
            "score": 0.0,
            "method": "empty_input",
            "reason": "empty_input",
        }

    cur_mean = float(np.mean(cur))
    base_mean = float(np.mean(base))

    # Mean Ratio Score
    if base_mean == 0:
        mean_ratio_score = float("inf") if cur_mean != 0 else 1.0
    else:
        mean_ratio_score = (
            max(abs(cur_mean / base_mean), abs(base_mean / cur_mean))
            if cur_mean != 0
            else float("inf")
        )

    # For sufficiently large samples, use KS statistic & PSI
    if cur.size >= 8 and base.size >= 8:
        ks_stat = _calculate_ks_statistic(cur, base)
        psi_score = _calculate_psi(cur, base)
        is_shift = (ks_stat > ks_threshold) or (psi_score > psi_threshold) or (mean_ratio_score >= ratio_threshold)
        return {
            "is_anomaly": bool(is_shift),
            "score": float(max(ks_stat, psi_score, mean_ratio_score if mean_ratio_score != float("inf") else 10.0)),
            "method": "ks_psi_composite",
            "reason": (
                f"ks_stat={ks_stat:.3f} (thresh={ks_threshold}), "
                f"psi={psi_score:.3f} (thresh={psi_threshold}), "
                f"mean_ratio={mean_ratio_score:.2f}"
            ),
        }

    # Fallback to mean ratio for small sample sizes
    is_anomaly = bool(mean_ratio_score >= ratio_threshold)
    return {
        "is_anomaly": is_anomaly,
        "score": float(mean_ratio_score),
        "method": "mean_ratio",
        "reason": f"baseline_mean={base_mean:.3f}, current_mean={cur_mean:.3f}, ratio={mean_ratio_score:.2f}",
    }
