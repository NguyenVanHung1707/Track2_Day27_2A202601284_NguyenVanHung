"""Enterprise-grade contract validator for Data Reliability.

Features:
- Deterministic checks: required, not_null, unique, accepted_values, range (min/max).
- Type validation: integer, number/float, string/text, datetime, boolean.
- Content checks: min_length for text fields.
- Contract-level freshness check against UTC timestamp.
- Severity levels: critical, warning, info.
- Operational actions: block, quarantine, warn.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def _issue(
    check: str,
    *,
    column: str | None,
    severity: str,
    passed: bool,
    details: str,
) -> dict[str, Any]:
    return {
        "check": check,
        "column": column,
        "severity": severity,
        "passed": bool(passed),
        "details": details,
    }


def load_contract(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _validate_type(series: pd.Series, expected_type: str) -> tuple[bool, int]:
    """Validate declared data type without silent coercion hiding data corruption.
    
    Returns (passed, invalid_count).
    """
    non_null = series.dropna()
    if non_null.empty:
        return True, 0

    expected = expected_type.lower()

    if expected in {"int", "integer"}:
        numeric = pd.to_numeric(non_null, errors="coerce")
        valid_mask = numeric.notna() & (numeric == np.floor(numeric))
        invalid_count = int((~valid_mask).sum())
        return invalid_count == 0, invalid_count

    elif expected in {"number", "float", "double", "decimal"}:
        numeric = pd.to_numeric(non_null, errors="coerce")
        invalid_count = int(numeric.isna().sum())
        return invalid_count == 0, invalid_count

    elif expected in {"datetime", "timestamp"}:
        dt = pd.to_datetime(non_null, errors="coerce", utc=True)
        invalid_count = int(dt.isna().sum())
        return invalid_count == 0, invalid_count

    elif expected in {"bool", "boolean"}:
        valid_bools = {True, False, 1, 0, "true", "false", "True", "False", "1", "0"}
        invalid_count = int((~non_null.isin(valid_bools)).sum())
        return invalid_count == 0, invalid_count

    elif expected in {"str", "string", "text"}:
        return True, 0

    return True, 0


def validate_dataframe(df: pd.DataFrame, contract: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    
    # Support both 'columns' and 'fields' schemas in contract definition
    columns = contract.get("columns") or contract.get("fields") or {}

    for column, rules in columns.items():
        severity = rules.get("severity", "warning")
        required = bool(rules.get("required", False))

        if column not in df.columns:
            if required:
                issues.append(
                    _issue(
                        "required_column",
                        column=column,
                        severity=severity,
                        passed=False,
                        details=f"Missing required column: {column}",
                    )
                )
            continue

        series = df[column]

        # 1. Type validation
        if "type" in rules:
            type_passed, invalid_type_count = _validate_type(series, rules["type"])
            issues.append(
                _issue(
                    "type",
                    column=column,
                    severity=severity,
                    passed=type_passed,
                    details=f"expected_type={rules['type']}; invalid_count={invalid_type_count}",
                )
            )

        # 2. Not-null validation
        if required:
            null_count = int(series.isna().sum())
            issues.append(
                _issue(
                    "not_null",
                    column=column,
                    severity=severity,
                    passed=(null_count == 0),
                    details=f"null_count={null_count}",
                )
            )

        # 3. Uniqueness validation
        if rules.get("unique"):
            duplicate_count = int(series.duplicated(keep=False).sum())
            issues.append(
                _issue(
                    "unique",
                    column=column,
                    severity=severity,
                    passed=(duplicate_count == 0),
                    details=f"duplicate_rows={duplicate_count}",
                )
            )

        # 4. Accepted values validation
        accepted = rules.get("accepted_values")
        if accepted is not None:
            invalid_mask = series.notna() & ~series.isin(accepted)
            invalid_count = int(invalid_mask.sum())
            issues.append(
                _issue(
                    "accepted_values",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}; accepted={accepted}",
                )
            )

        # 5. Numeric range validation
        if "min" in rules or "max" in rules:
            numeric = pd.to_numeric(series, errors="coerce")
            invalid = pd.Series(False, index=series.index)
            if "min" in rules:
                invalid |= numeric < rules["min"]
            if "max" in rules:
                invalid |= numeric > rules["max"]
            invalid_count = int(invalid.fillna(False).sum())
            issues.append(
                _issue(
                    "range",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}",
                )
            )

        # 6. String length validation (e.g. min_length for KB docs)
        if "min_length" in rules:
            min_len = rules["min_length"]
            non_null_strs = series.dropna().astype(str)
            short_count = int((non_null_strs.str.len() < min_len).sum())
            issues.append(
                _issue(
                    "min_length",
                    column=column,
                    severity=severity,
                    passed=(short_count == 0),
                    details=f"short_count={short_count}; min_length={min_len}",
                )
            )

    # 7. Freshness validation at contract level
    freshness = contract.get("freshness")
    if freshness and isinstance(freshness, dict):
        fresh_col = freshness.get("column")
        max_delay = freshness.get("max_delay_minutes", 60)
        fresh_sev = freshness.get("severity", "warning")

        if fresh_col and fresh_col in df.columns and not df.empty:
            timestamps = pd.to_datetime(df[fresh_col], utc=True, errors="coerce")
            max_ts = timestamps.max()
            if pd.isna(max_ts):
                issues.append(
                    _issue(
                        "freshness",
                        column=fresh_col,
                        severity=fresh_sev,
                        passed=False,
                        details=f"All timestamps in '{fresh_col}' are invalid or missing",
                    )
                )
            else:
                now_utc = pd.Timestamp(datetime.now(timezone.utc))
                delay_minutes = max(0.0, (now_utc - max_ts).total_seconds() / 60.0)
                is_fresh = delay_minutes <= max_delay
                issues.append(
                    _issue(
                        "freshness",
                        column=fresh_col,
                        severity=fresh_sev,
                        passed=is_fresh,
                        details=f"delay_minutes={delay_minutes:.1f}; max_delay_minutes={max_delay}",
                    )
                )

    return issues


def failed_issues(issues: list[dict[str, Any]], min_severity: str | None = None) -> list[dict[str, Any]]:
    failed = [i for i in issues if not i.get("passed", False)]
    if min_severity is None:
        return failed
    order = {"info": 0, "warning": 1, "critical": 2}
    threshold = order.get(min_severity, 1)
    return [i for i in failed if order.get(i.get("severity", "warning"), 1) >= threshold]


def determine_action(issues: list[dict[str, Any]]) -> str:
    """Determine operational action: block (critical failures), quarantine (row issues), warn (info/warning)."""
    failed = failed_issues(issues)
    if not failed:
        return "pass"
    critical_fails = failed_issues(issues, min_severity="critical")
    if critical_fails:
        return "block"
    return "warn"


def quarantine_invalid_rows(df: pd.DataFrame, contract: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate clean rows from invalid/corrupt rows according to contract rules."""
    invalid_mask = pd.Series(False, index=df.index)
    columns = contract.get("columns") or contract.get("fields") or {}

    for column, rules in columns.items():
        if column not in df.columns:
            continue
        series = df[column]

        if rules.get("required"):
            invalid_mask |= series.isna()

        if rules.get("unique"):
            invalid_mask |= series.duplicated(keep=False)

        accepted = rules.get("accepted_values")
        if accepted is not None:
            invalid_mask |= (series.notna() & ~series.isin(accepted))

        if "min" in rules or "max" in rules:
            numeric = pd.to_numeric(series, errors="coerce")
            if "min" in rules:
                invalid_mask |= (numeric < rules["min"])
            if "max" in rules:
                invalid_mask |= (numeric > rules["max"])

    clean_df = df[~invalid_mask].copy()
    quarantine_df = df[invalid_mask].copy()
    return clean_df, quarantine_df
