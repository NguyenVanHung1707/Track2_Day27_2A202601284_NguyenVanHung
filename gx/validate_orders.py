#!/usr/bin/env python3
"""Great Expectations Core 1.21 Enterprise Validation Suite & Checkpoint.

Features:
- Encapsulated Expectation Suite with critical severity expectations.
- Declarative Batch Definition & Validation Definition.
- Checkpoint execution with result evaluation and operational action determination.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import great_expectations as gx
except ImportError as exc:
    raise SystemExit("great_expectations is not installed. Run: pip install -r requirements.txt") from exc


def build_and_run_checkpoint() -> bool:
    orders_path = ROOT / "data" / "incoming" / "orders.csv"
    if not orders_path.exists():
        print(f"Data file not found: {orders_path}")
        return False

    df = pd.read_csv(orders_path)
    context = gx.get_context()

    # Data Source & Asset
    data_source_name = "orders_pandas_source"
    try:
        data_source = context.data_sources.get(data_source_name)
    except Exception:
        data_source = context.data_sources.add_pandas(data_source_name)

    asset_name = "orders_dataframe_asset"
    try:
        asset = data_source.get_asset(asset_name)
    except Exception:
        asset = data_source.add_dataframe_asset(name=asset_name)

    batch_def_name = "whole_orders_batch_def"
    try:
        batch_definition = asset.get_batch_definition(batch_def_name)
    except Exception:
        batch_definition = asset.add_batch_definition_whole_dataframe(batch_def_name)

    # Expectation Suite
    suite_name = "orders_quality_suite"
    try:
        suite = context.suites.get(suite_name)
    except Exception:
        suite = context.suites.add(gx.ExpectationSuite(name=suite_name))

    # Add core expectations
    expectations = [
        gx.expectations.ExpectColumnValuesToNotBeNull(
            column="order_id",
            notes="Order ID is the primary key and must not be null"
        ),
        gx.expectations.ExpectColumnValuesToBeUnique(
            column="order_id",
            notes="Order ID must be unique across all records"
        ),
        gx.expectations.ExpectColumnValuesToNotBeNull(
            column="customer_id",
            notes="Customer ID is required"
        ),
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="amount",
            min_value=0,
            notes="Order amount cannot be negative"
        ),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="currency",
            value_set=["USD", "VND"],
            notes="Only supported currencies allowed"
        ),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="status",
            value_set=["pending", "completed", "refunded", "cancelled"],
            notes="Valid order statuses"
        ),
    ]

    # Populate suite
    for exp in expectations:
        try:
            suite.add_expectation(exp)
        except Exception:
            pass

    # Validation Definition
    val_def_name = "orders_validation_definition"
    try:
        validation_definition = context.validation_definitions.get(val_def_name)
    except Exception:
        validation_definition = context.validation_definitions.add(
            gx.ValidationDefinition(
                name=val_def_name,
                data=batch_definition,
                suite=suite,
            )
        )

    # Checkpoint
    checkpoint_name = "orders_checkpoint"
    try:
        checkpoint = context.checkpoints.get(checkpoint_name)
    except Exception:
        checkpoint = context.checkpoints.add(
            gx.Checkpoint(
                name=checkpoint_name,
                validation_definitions=[validation_definition],
            )
        )

    # Execute Checkpoint
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})
    all_ok = True
    print("=== GREAT EXPECTATIONS VALIDATION SUITE RESULTS ===")
    for expectation in expectations:
        result = batch.validate(expectation)
        success = bool(result.success)
        all_ok = all_ok and success
        status = "PASSED" if success else "FAILED"
        print(f"[{status}] {expectation.__class__.__name__:<36} (col: {getattr(expectation, 'column', 'N/A')})")

    checkpoint_result = checkpoint.run(batch_parameters={"dataframe": df})
    print(f"\nCheckpoint Run Status: {'SUCCESS' if checkpoint_result.success else 'FAILED'}")
    print(f"Recommended Action: {'PASS / PROCEED' if checkpoint_result.success else 'BLOCK PIPELINE'}")
    return checkpoint_result.success


def main() -> None:
    build_and_run_checkpoint()


if __name__ == "__main__":
    main()
