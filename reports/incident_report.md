# Incident Report

## Severity
P1 - Critical (Direct Impact on Executive Revenue Reporting & AI Customer Support Accuracy)

## Summary
On 2026-08-29, the data reliability team detected multiple silent data corruption issues across the e-commerce analytics and AI pipeline. Although upstream batch jobs reported execution status `SUCCESS`, executive revenue metrics on the CEO Dashboard were distorted and the Customer Support AI Agent served outdated refund policies. Data Observability layers (Data Contracts, dbt Unit Tests, Statistical Anomaly Detection, Lineage Tracking, and SLO Multi-window Burn-rate policies) identified the root causes, determined the blast radius, isolated corrupt records, and verified system recovery.

## Detection
- Signal:
  1. Data Contract failure: Primary key uniqueness violation on `order_id` in `orders.csv` (critical check failed).
  2. Statistical Anomaly: Ingested order row count dropped by 75% (`volume_drop` anomaly, MAD score > 5.5).
  3. Freshness / Knowledge Base contract violation: `kb_documents.jsonl` publish timestamps lagged by >3 hours.
  4. dbt Transformation unit tests caught customer dimension duplicate active rows inflating daily revenue.
- First observed time: 2026-08-29T10:00:00Z

## Root Cause
1. **Ingestion Layer Primary Key Duplication:** Upstream order service retry loop generated duplicate `order_id` records in `orders.csv`.
2. **Silent Ingestion Truncation:** Network timeout during batch transfer resulted in only 150/600 rows ingested without triggering a fatal error in the ETL runner.
3. **Knowledge Base Synchronization Stalling:** Background document publisher failed to refresh active KB documents (`kb_documents.jsonl`), causing RAG retrieval to query stale policies.
4. **SCD Type 2 Dimension Join Inflation:** Duplicate active customer records (`is_active = true`) in `stg_customers` produced a Cartesian explosion in `fct_daily_revenue`, artificially inflating revenue figures.

## Evidence
1. `src/contract_validator.py` detected duplicate keys: `duplicate_rows=6` on `order_id` (Severity: critical).
2. `observability/anomaly.py` MAD detector flagged volume drop: 150 rows vs. historical baseline 600 rows (Modified Z-score = 5.53 > threshold 3.5).
3. Contract freshness checker flagged `delay_minutes=180.0 > max_delay_minutes=60.0` on `published_at` in `kb_documents.jsonl`.
4. dbt unit test `test_scd_customer_duplicate_active_rows_does_not_inflate_revenue` caught revenue inflation before customer deduplication was applied in `fct_daily_revenue.sql`.
5. `observability/slo.py` multi-window burn rate calculation produced burn rate > 14.0x, triggering an immediate on-call page.

## Blast Radius
```text
orders.csv / customers.csv / kb_documents.jsonl (Raw Ingestion)
  │
  ├──► stg_orders & stg_customers (Staging Models)
  │      │
  │      └──► fct_daily_revenue (Core Mart)
  │             │
  │             └──► CEO Revenue Dashboard (Executive KPI Reporting)
  │
  └──► active KB documents
         │
         └──► RAG Vector Store & Support Agent (Customer Support Bot)
```

## Mitigation
1. **Pipeline Blocking & Quarantine:** Enhanced `contract_validator.py` with `quarantine_invalid_rows()` to block critical violations while isolating invalid records.
2. **dbt Mart Hardening:** Updated `fct_daily_revenue.sql` with `distinct customer_id` filter for `is_active = true` customers, eliminating duplicate join expansion.
3. **Adaptive Seasonality Anomaly Detection:** Deployed context-aware MAD and same-weekday statistical detectors in `observability/anomaly.py` to prevent false positive alerts on weekends.
4. **Freshness Contract Gate:** Enforced freshness threshold (max 60 minutes) on `kb_documents.jsonl` before vector indexing.

## Recovery
- Cleaned and re-ingested healthy baseline dataset via `make reset`.
- Executed `dbt build` to recompile staging models and rebuild `fct_daily_revenue`.
- Refreshed active knowledge base documents in the RAG retrieval pipeline.

## Verification
- [x] Contract healthy
- [x] dbt tests healthy
- [x] anomaly returned to expected range
- [x] SLO healthy / budget understood
- [x] downstream output verified

## Prevention / Action Items
| Action | Owner | Deadline | Why |
|---|---|---|---|
| Implement pre-ingestion Data Contract Gate in CI/CD pipeline | Data Platform Team | 2026-09-05 | Prevent schema, type, and freshness drift from entering warehouse |
| Add dbt native unit tests for all mart models | Analytics Engineering | 2026-09-10 | Ensure SQL transformation logic is resilient to SCD dimension duplication |
| Deploy Multi-window Burn-rate alerting in PagerDuty | SRE / Observability Team | 2026-09-12 | Distinguish transient short-lived spikes from sustained budget depletion |
| Automated quarantine mechanism for invalid incoming records | Data Engineering | 2026-09-15 | Enable zero-downtime processing while isolating problematic records |
