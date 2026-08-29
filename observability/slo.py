"""Service Level Objective (SLO), Error Budget, and Burn-Rate Alerting Engine.

Features:
- SLI/SLO compliance and error budget calculation.
- Google SRE Multi-Window Multi-Burn-Rate alerting policy:
  - Detects sustained fast burns that threaten error budgets (triggers on-call page).
  - Absorbs transient short-lived spikes without paging on-call engineers.
"""
from __future__ import annotations

from typing import Any


def calculate_slo(target: float, bad_events: int, total_events: int) -> dict[str, Any]:
    """Calculate SLO compliance, actual vs allowed bad rate, burn rate, and remaining budget."""
    if not 0 < target < 1:
        raise ValueError("target must be between 0 and 1 (exclusive)")
    if bad_events < 0 or total_events < 0 or bad_events > total_events:
        raise ValueError("invalid event counts")

    allowed_bad_rate = 1.0 - target
    if total_events == 0:
        return {
            "target": target,
            "actual_bad_rate": 0.0,
            "allowed_bad_rate": allowed_bad_rate,
            "burn_rate": 0.0,
            "remaining_error_budget_fraction": 1.0,
            "breached": False,
        }

    actual_bad_rate = bad_events / total_events
    burn_rate = actual_bad_rate / allowed_bad_rate if allowed_bad_rate > 0 else 0.0
    consumed_fraction = min(1.0, actual_bad_rate / allowed_bad_rate) if allowed_bad_rate > 0 else 1.0

    return {
        "target": target,
        "actual_bad_rate": actual_bad_rate,
        "allowed_bad_rate": allowed_bad_rate,
        "burn_rate": burn_rate,
        "remaining_error_budget_fraction": max(0.0, 1.0 - consumed_fraction),
        "breached": bool(actual_bad_rate > allowed_bad_rate),
    }


def evaluate_multiwindow_burn(
    *,
    short_window_burn: float,
    long_window_burn: float,
    policy: str = "standard",
) -> dict[str, Any]:
    """Evaluate multi-window multi-burn-rate policy according to Google SRE guidelines.
    
    Alert triggers (page=True) only when BOTH short and long windows indicate elevated burn rate,
    preventing noisy alerts on brief transient spikes.
    """
    short_b = float(short_window_burn)
    long_b = float(long_window_burn)

    # Fast Burn: Critical (e.g. 14.4x burn rate over 1h & 6h)
    if short_b >= 14.0 and long_b >= 14.0:
        return {
            "page": True,
            "severity": "critical",
            "reason": "critical_sustained_fast_burn_14x",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
            "action": "page_oncall_immediate",
        }

    # Medium Burn: High (e.g. 6.0x burn rate over short & long window)
    if short_b >= 6.0 and long_b >= 6.0:
        return {
            "page": True,
            "severity": "high",
            "reason": "sustained_fast_burn_6x",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
            "action": "page_oncall",
        }

    # Sustained Elevated Burn (e.g. short >= 3.0 and long >= 2.0)
    if short_b >= 3.0 and long_b >= 2.0:
        return {
            "page": True,
            "severity": "medium",
            "reason": "sustained_elevated_burn",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
            "action": "page_oncall_ticket",
        }

    # Transient Spike: Short window is high, but long window remains healthy -> DO NOT PAGE
    if short_b >= 3.0 and long_b < 2.0:
        return {
            "page": False,
            "severity": "warning",
            "reason": "transient_spike_short_window_only_no_page",
            "short_window_burn": short_b,
            "long_window_burn": long_b,
            "action": "log_warning_no_page",
        }

    # Normal operation
    return {
        "page": False,
        "severity": "info",
        "reason": "within_normal_burn_budget",
        "short_window_burn": short_b,
        "long_window_burn": long_b,
        "action": "none",
    }
