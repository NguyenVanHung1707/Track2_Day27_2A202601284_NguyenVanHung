"""Observability metrics for RAG Knowledge Base and Support AI Agents.

Features:
- Approximate token length tracking and length collapse/expansion anomaly detection.
- Embedding vector norm and representation space drift detection.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np

from observability.anomaly import zscore_detector


def approximate_token_lengths(texts: Iterable[str]) -> list[int]:
    """Token length approximation without requiring external heavy tokenizer models."""
    return [len(str(t).split()) for t in texts]


def detect_text_length_shift(
    current_texts: Iterable[str],
    baseline_batch_means: Iterable[float],
    *,
    threshold: float = 3.0,
) -> dict[str, Any]:
    """Detect significant document/response text length shifts (e.g. content truncation or explosion)."""
    lengths = approximate_token_lengths(current_texts)
    current_mean = float(np.mean(lengths)) if lengths else 0.0
    result = zscore_detector(current_mean, baseline_batch_means, threshold=threshold)
    result["metric"] = "mean_text_length"
    result["current_mean"] = current_mean
    return result


def detect_embedding_norm_shift(
    current_norms: Iterable[float],
    baseline_norms: Iterable[float],
    *,
    threshold: float = 3.0,
) -> dict[str, Any]:
    """Detect representation drift or abnormal vector norms in incoming embeddings."""
    cur = np.asarray(list(current_norms), dtype=float)
    base = np.asarray(list(baseline_norms), dtype=float)

    if cur.size == 0 or base.size == 0:
        return {
            "is_anomaly": False,
            "score": 0.0,
            "method": "embedding_norm_shift",
            "reason": "empty_input",
        }

    current_mean = float(np.mean(cur))
    base_mean = float(np.mean(base))
    result = zscore_detector(current_mean, base, threshold=threshold)
    result["metric"] = "embedding_norm"
    result["current_mean"] = current_mean
    result["baseline_mean"] = base_mean
    result["method"] = "embedding_norm_zscore"
    return result
