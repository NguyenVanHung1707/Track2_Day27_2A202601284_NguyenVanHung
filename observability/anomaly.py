"""Advanced statistical anomaly detection engine for Data Reliability.

Features:
- Standard Z-score detector with zero-std safeguards.
- Robust Median Absolute Deviation (MAD) detector with zero-MAD handling.
- Exponentially Weighted Moving Average (EWMA) detector for temporal trends.
- Context-aware auto router:
  - Considers day_of_week / seasonality via same_segment_history.
  - Considers known_events (flash sale, maintenance, holidays).
  - Selects robust statistical method (MAD vs Z-score) based on sample characteristics.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def zscore_detector(
    current: float, history: Iterable[float], threshold: float = 3.0
) -> dict[str, Any]:
    values = np.asarray(list(history), dtype=float)
    if values.size < 3:
        return {
            "is_anomaly": False,
            "score": 0.0,
            "method": "zscore",
            "reason": "insufficient_history",
        }
    mean = float(np.mean(values))
    std = float(np.std(values))
    if std == 0:
        score = float("inf") if float(current) != mean else 0.0
    else:
        score = abs(float(current) - mean) / std
    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "zscore",
        "reason": f"mean={mean:.3f}, std={std:.3f}, threshold={threshold}",
    }


def mad_detector(
    current: float, history: Iterable[float], threshold: float = 3.5
) -> dict[str, Any]:
    """Robust Median Absolute Deviation (MAD) detector with zero-MAD edge case handling."""
    values = np.asarray(list(history), dtype=float)
    if values.size < 3:
        return {
            "is_anomaly": False,
            "score": 0.0,
            "method": "mad",
            "reason": "insufficient_history",
        }
    median = float(np.median(values))
    abs_deviations = np.abs(values - median)
    mad = float(np.median(abs_deviations))

    # Zero-MAD edge case handling (when >50% values are identical)
    if mad == 0:
        mean_ad = float(np.mean(abs_deviations))
        if mean_ad > 0:
            mad = mean_ad
        else:
            # All historical values are identical
            if float(current) == median:
                return {
                    "is_anomaly": False,
                    "score": 0.0,
                    "method": "mad",
                    "reason": f"median={median:.3f}, mad=0.0 (identical baseline), match",
                }
            else:
                return {
                    "is_anomaly": True,
                    "score": float("inf"),
                    "method": "mad",
                    "reason": f"median={median:.3f}, mad=0.0 (identical baseline), mismatch",
                }

    modified_z = 0.6745 * abs(float(current) - median) / mad
    return {
        "is_anomaly": bool(modified_z > threshold),
        "score": float(modified_z),
        "method": "mad",
        "reason": f"median={median:.3f}, mad={mad:.3f}, threshold={threshold}",
    }


def ewma_detector(
    current: float, history: Iterable[float], alpha: float = 0.3, threshold: float = 3.0
) -> dict[str, Any]:
    """Exponentially Weighted Moving Average detector for trending/time-series data."""
    values = np.asarray(list(history), dtype=float)
    if values.size < 3:
        return {
            "is_anomaly": False,
            "score": 0.0,
            "method": "ewma",
            "reason": "insufficient_history",
        }
    # Calculate EWMA
    weights = (1 - alpha) ** np.arange(len(values))[::-1]
    weights /= weights.sum()
    ewma_mean = float(np.sum(weights * values))
    ewma_std = float(np.sqrt(np.sum(weights * (values - ewma_mean) ** 2)))

    if ewma_std == 0:
        score = float("inf") if float(current) != ewma_mean else 0.0
    else:
        score = abs(float(current) - ewma_mean) / ewma_std

    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "ewma",
        "reason": f"ewma_mean={ewma_mean:.3f}, ewma_std={ewma_std:.3f}, threshold={threshold}",
    }


def detect_anomaly(
    current: float,
    history: Iterable[float],
    *,
    method: str = "auto",
    threshold: float = 3.0,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stable anomaly detection API with context awareness & seasonal intelligence."""
    context = context or {}

    if method == "zscore":
        return zscore_detector(current, history, threshold=threshold)

    if method == "mad":
        return mad_detector(current, history, threshold=threshold if threshold != 3.0 else 3.5)

    if method == "ewma":
        return ewma_detector(current, history, threshold=threshold)

    if method == "auto":
        # 1. Seasonality / Segment-based history selection
        same_segment_history = context.get("same_segment_history")
        day_of_week = context.get("day_of_week")

        if same_segment_history is not None:
            segment_list = list(same_segment_history)
            if len(segment_list) >= 3:
                history_to_use = segment_list
                routing_note = f"segment_dow={day_of_week}" if day_of_week is not None else "same_segment"
            else:
                history_to_use = list(history)
                routing_note = "fallback_general_history"
        else:
            history_to_use = list(history)
            routing_note = "general_history"

        # 2. Known event threshold adjustment
        known_event = context.get("known_event")
        effective_threshold = threshold
        if known_event in {"promo", "flash_sale", "marketing_campaign"}:
            # Relax threshold slightly for known surge events
            effective_threshold = threshold * 1.5
            routing_note += f"; known_event={known_event}"
        elif known_event in {"scheduled_downtime", "maintenance"}:
            effective_threshold = threshold * 1.5
            routing_note += f"; known_event={known_event}"

        # 3. Model selection based on sample size and distribution robustness
        if len(history_to_use) >= 5:
            res = mad_detector(current, history_to_use, threshold=3.5 if threshold == 3.0 else effective_threshold)
            res["method"] = "auto:mad"
            res["reason"] = f"{res['reason']}; routing={routing_note}"
            return res
        else:
            res = zscore_detector(current, history_to_use, threshold=effective_threshold)
            res["method"] = "auto:zscore"
            res["reason"] = f"{res['reason']}; routing={routing_note}"
            return res

    raise ValueError(f"Unsupported method: {method}")
