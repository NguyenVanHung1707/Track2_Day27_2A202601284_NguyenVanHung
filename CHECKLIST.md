# CHECKLIST — DATA RELIABILITY GAME DAY (LAB 27)

> **Mục tiêu chính:** Detect → Triage → Find Root Cause → Determine Blast Radius → Mitigate → Verify Recovery  
> **Tổng điểm:** 100 điểm cơ bản + tối đa 15 điểm Bonus  
> **Interface bắt buộc:** Đảm bảo tất cả 9 functions trong [`student_api.py`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/student_api.py) đúng định dạng để pass 20 Hidden Tests.

---

## 📌 PHẦN 1: TỔNG QUAN VÀ TIẾN ĐỘ THỰC HIỆN

- [x] **Phase 0:** Healthy Baseline & System Setup (0–10')
- [x] **Phase 1:** Data Contract & Validation (10–30')
- [x] **Phase 2:** dbt Transformation Protection (30–50')
- [x] **Phase 3:** Anomaly Detection & Statistics (50–70')
- [x] **Phase 4:** Lineage & Blast Radius (70–85')
- [x] **Phase 5:** SLI / SLO & Error Budget (85–100')
- [x] **Phase 6:** Mystery Incident Investigation (100–115')
- [x] **Phase 7:** Incident Report & AI Agent Decision Log (115–120')
- [x] **Phase 8:** Comprehensive Testing & Hidden Tests Readiness

---

## 🚀 PHẦN 2: CHI TIẾT TỪNG GIAI ĐOẠN (PHASES)

### Phase 0: Healthy Baseline & Setup (0–10')
- [x] Khởi tạo môi trường ảo Python (3.10–3.13) và cài đặt dependencies:
  ```bash
  python -m venv .venv
  .venv\Scripts\activate      # Trên Windows
  pip install -r requirements.txt
  ```
- [x] Chạy reset dữ liệu và thiết lập baseline:
  ```bash
  make reset
  make baseline
  ```
- [x] Chạy kiểm thử ban đầu:
  ```bash
  pytest tests_public -q
  ```
- [x] Khảo sát hệ thống và trả lời 3 câu hỏi cốt lõi:
  - [x] Dataset nào là critical? (`orders`, `customers`, `kb_documents`)
  - [x] Downstream consumers gồm những ai? (`fct_daily_revenue`, `CEO dashboard`, `RAG/Support Agent`)
  - [x] Metric nào cảnh báo sớm khi data không đáng tin cậy?

---

### Phase 1: Data Contract & Deterministic Validation (10–30') — [10 Điểm]
- **File cần chỉnh sửa/kiểm tra:**
  - [`src/contract_validator.py`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/src/contract_validator.py)
  - [`contracts/orders_contract.yaml`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/contracts/orders_contract.yaml)
  - [`contracts/kb_contract.yaml`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/contracts/kb_contract.yaml)
  - [`gx/validate_orders.py`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/gx/validate_orders.py)
- **Nhiệm vụ bắt buộc:**
  - [x] Bổ sung Type validation (kiểm tra kiểu dữ liệu của các cột theo contract: integer, number, datetime, boolean, string).
  - [x] Bổ sung Freshness validation (kiểm tra độ trễ/độ tươi mới của dữ liệu so với thời gian hiện tại).
  - [x] Phân loại `severity`: `critical`, `warning`, `info`.
  - [x] Xác định `action`: `block`, `quarantine`, `warn`.
  - [x] Kiểm tra đầy đủ: `required/missing columns`, `null`, `unique`, `accepted values`, `range`, `min_length`.
  - [x] Thử nghiệm với fault scenario `duplicate_pk`:
    ```bash
    make reset
    python scripts/inject_fault.py duplicate_pk
    make baseline
    ```
    *Kỳ vọng:* Contract validator phải bắt được lỗi deterministic này (Đã pass!).
- **Nhiệm vụ nâng cao (Bonus):**
  - [x] Xây dựng Great Expectations Expectation Suite + ValidationDefinition + Checkpoint + Actions (**+3 điểm**).
  - [x] Triển khai cơ chế Automatic Quarantine khi gặp bad records (`quarantine_invalid_rows`) (**+3 điểm**).

---

### Phase 2: dbt Transformation Protection (30–50') — [10 Điểm]
- **File cần chỉnh sửa/kiểm tra:**
  - [`dbt_project/models/marts/fct_daily_revenue.sql`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/dbt_project/models/marts/fct_daily_revenue.sql)
  - [`dbt_project/models/marts/schema.yml`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/dbt_project/models/marts/schema.yml)
  - [`dbt_project/models/staging/schema.yml`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/dbt_project/models/staging/schema.yml)
  - [`dbt_project/tests/assert_nonnegative_revenue.sql`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/dbt_project/tests/assert_nonnegative_revenue.sql)
  - [`dbt_project/models/marts/unit_tests.yml`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/dbt_project/models/marts/unit_tests.yml)
- **Nhiệm vụ bắt buộc:**
  - [x] Thêm ít nhất 2 generic data tests hợp lý vào `schema.yml` (not_null, unique, accepted_values).
  - [x] Thêm 1 singular business test (`assert_nonnegative_revenue.sql`).
  - [x] Chạy và verify dbt:
    ```bash
    make reset
    .venv\Scripts\dbt.exe build --project-dir dbt_project --profiles-dir dbt_project
    ```
  - [x] Nắm vững lý do: *Vì sao `not_null/unique` là data tests chứ không phải dbt unit tests?* (Data tests kiểm tra dữ liệu thực tế tại runtime; dbt unit tests kiểm tra tính đúng đắn của logic SQL biến đổi dựa trên mock inputs).
- **Nhiệm vụ nâng cao (Bonus):**
  - [x] Xử lý trường hợp Customer dimension có nhiều active version (SCD Type 2 issue) bằng `distinct customer_id`.
  - [x] Viết dbt native unit test nhỏ nhất để expose hiện tượng revenue inflation khi join với customer bị duplicate active rows trong `unit_tests.yml` (**+3 điểm**).

---

### Phase 3: Anomaly Detection (50–70') — [15 Điểm]
- **File cần chỉnh sửa/kiểm tra:**
  - [`observability/anomaly.py`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/observability/anomaly.py)
  - [`observability/distribution.py`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/observability/distribution.py)
- **Nhiệm vụ bắt buộc:**
  - [x] Hoàn thiện `detect_anomaly` để bắt được lỗi `volume_drop`:
    ```bash
    make reset
    python scripts/inject_fault.py volume_drop
    make baseline
    ```
  - [x] Cải tiến `detect_distribution_shift` trong `observability/distribution.py` (sử dụng 2-sample Kolmogorov-Smirnov test & Population Stability Index PSI).
  - [x] Hiểu rõ và giải thích được khi nào Z-score bị sai lệch (bị ảnh hưởng bởi outliers, phân phối lệch skewness, tính chu kỳ/mùa vụ, dữ liệu kích thước nhỏ).
- **Nhiệm vụ nâng cao (Bonus):**
  - [x] Nâng cấp chế độ `method="auto"` để tự động thích ứng với seasonality và outliers:
    - [x] Same-weekday baseline (so sánh với cùng thứ trong tuần qua `same_segment_history`) (**+3 điểm**).
    - [x] Median / MAD (Median Absolute Deviation) chống ngoại lai và xử lý zero-MAD (**+3 điểm**).
    - [x] EWMA (Exponentially Weighted Moving Average) cho dữ liệu có xu hướng thời gian.
  - [x] Tận dụng tham số `context` (`metric_name`, `day_of_week`, `same_segment_history`, `known_event`).

---

### Phase 4: Lineage & Blast Radius (70–85') — [15 Điểm]
- **File cần chỉnh sửa/kiểm tra:**
  - [`observability/lineage.py`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/observability/lineage.py)
  - [`data/baseline/lineage_graph.json`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/data/baseline/lineage_graph.json)
- **Nhiệm vụ bắt buộc:**
  - [x] Trả lời bằng code: Khi `stg_orders` bị lỗi thì những assets downstream nào bị ảnh hưởng? (`fct_daily_revenue`, `ceo_revenue_dashboard`).
  - [x] Hoàn thiện hàm `get_downstream_assets(graph, start)` sử dụng thuật toán BFS/DFS duyệt toàn bộ downstream dependencies.
- **Nhiệm vụ nâng cao (Bonus):**
  - [x] Hoàn thiện hàm `get_column_downstream(graph, start)` tính toán Column-level transitive lineage (**+7 điểm**).
  - [x] Tự động parse `dbt_project/target/manifest.json` sau `dbt build` để tự sinh đồ thị lineage.

---

### Phase 5: SLI / SLO & Error Budget (85–100') — [10 Điểm]
- **File cần chỉnh sửa/kiểm tra:**
  - [`observability/slo.py`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/observability/slo.py)
- **Nhiệm vụ bắt buộc:**
  - [x] Hoàn thiện hàm `calculate_slo(target, bad_events, total_events)`:
    - [x] `allowed_bad_rate = 1.0 - target`
    - [x] `actual_bad_rate = bad_events / total_events`
    - [x] `burn_rate = actual_bad_rate / allowed_bad_rate`
    - [x] `remaining_error_budget_fraction`
    - [x] `breached: bool`
  - [x] Kiểm thử với case chuẩn: SLO = 99.5%, 2 bad checks / 100 checks (actual bad rate = 2%, allowed = 0.5%, burn rate = 4.0, breached = True).
- **Nhiệm vụ nâng cao (Bonus):**
  - [x] Triển khai chính sách `evaluate_multiwindow_burn(short_window_burn, long_window_burn)` theo Google SRE standard (**+7 điểm**):
    - [x] Phân biệt transient spike ngắn hạn (không page on-call, chỉ cảnh báo nhẹ).
    - [x] Phát hiện sustained fast burn dài hạn (page on-call khẩn cấp).

---

### Phase 6: RAG / Knowledge Base Observability (Bonus) — [+7 Điểm]
- **File cần chỉnh sửa/kiểm tra:**
  - [`observability/rag_metrics.py`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/observability/rag_metrics.py)
  - [`contracts/kb_contract.yaml`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/contracts/kb_contract.yaml)
- **Nhiệm vụ:**
  - [x] Thử nghiệm lỗi stale knowledge base:
    ```bash
    make reset
    python scripts/inject_fault.py stale_kb
    make baseline
    ```
  - [x] Hoàn thiện `detect_text_length_shift(current_texts, baseline_batch_means)`.
  - [x] Hoàn thiện `detect_embedding_norm_shift(current_norms, baseline_norms)` (**+7 điểm**).

---

### Phase 7: Mystery Incident Investigation & RCA (100–115') — [15 Điểm]
- **Quy tắc:** Giảng viên cung cấp dataset hoặc fault folder bí mật. **TUYỆT ĐỐI KHÔNG XEM SCRIPT TẠO FAULT.**
- **Thu thập bằng chứng (Evidence) thông qua:**
  1. Contract validation output
  2. dbt test failure output
  3. Anomaly detection metrics
  4. Lineage graph & blast radius
  5. SLO status & burn rate
  6. Khám phá raw data có chủ đích
- **Trả lời đầy đủ 7 câu hỏi:**
  - [x] **1. What happened?** (Sự cố sụt giảm dữ liệu, trùng khóa và tài liệu KB bị trễ).
  - [x] **2. When did it start?** (2026-08-29T10:00:00Z).
  - [x] **3. Root cause?** (Retry loop sinh trùng order_id, stream drop 75% rows, stale KB sync và duplicate active SCD rows).
  - [x] **4. Blast radius?** (Ảnh hưởng `stg_orders`, `fct_daily_revenue`, `CEO Revenue Dashboard` và `RAG Support Agent`).
  - [x] **5. Mitigation?** (Chặn pipeline, cô lập quarantine rows, deduplicate active customer trong dbt, enforce freshness).
  - [x] **6. Recovery verification?** (Reset clean baseline, rebuild dbt, chạy full test suite và kiểm tra SLO burn rate).
  - [x] **7. Prevention?** (CI/CD Contract Gate, dbt unit tests, multiwindow alerting, automated quarantine).

---

### Phase 8: Báo cáo & Tài liệu hóa (115–120') — [10 Điểm]

#### 1. Hoàn thành [`reports/incident_report.md`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/reports/incident_report.md) [5 Điểm]
- [x] Điền Severity (P1 - Critical).
- [x] Tóm tắt Summary sự cố chi tiết, rõ ràng.
- [x] Mô tả Detection signal & First observed time.
- [x] Trình bày Root Cause và liệt kê đầy đủ 5 bằng chứng kỹ thuật (Evidence 1 - 5).
- [x] Vẽ sơ đồ Blast Radius dạng ASCII: `root -> downstream`.
- [x] Ghi rõ kế hoạch Mitigation & Recovery.
- [x] Tích chọn đầy đủ checklist Verification:
  - [x] Contract healthy
  - [x] dbt tests healthy
  - [x] Anomaly returned to expected range
  - [x] SLO healthy / budget understood
  - [x] Downstream output verified
- [x] Lập bảng Prevention / Action Items đầy đủ các cột (Action, Owner, Deadline, Why).

#### 2. Hoàn thành [`reports/agent_log.md`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/reports/agent_log.md)
- [x] Ghi lại 6 quyết định kỹ thuật quan trọng khi tương tác với AI Agent:
  - [x] Decision 1: Strict Type Validation vs. Silent Coercion.
  - [x] Decision 2: SCD Type 2 Customer Join & Revenue Inflation Protection in dbt.
  - [x] Decision 3: Robust Anomaly Detection using MAD & Seasonality Awareness.
  - [x] Decision 4: Google SRE Multi-Window Multi-Burn-Rate Alerting Policy.
  - [x] Decision 5: Transitive Column-Level Lineage Graph Traversal.
  - [x] Decision 6: Statistical Distribution Drift with KS-Test & PSI.

#### 3. Chuẩn bị bảo vệ giải pháp (Defend Solution) [5 Điểm]
- [x] Sẵn sàng giải thích luồng hoạt động của toàn bộ pipeline từ input raw data đến dashboard/RAG.
- [x] Sẵn sàng giải thích trade-offs giữa false positives và false negatives trong anomaly detection & SLO alerting.

---

## 🛠️ PHẦN 3: STABLE STUDENT API CHECKLIST

Đảm bảo file [`student_api.py`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/student_api.py) cung cấp đúng 9 hàm với output shape chuẩn theo [`docs/STUDENT_API.md`](file:///E:/hung/VinAI/Track2/Day27/Track2_Day27_2A202601284_NguyenVanHung/docs/STUDENT_API.md):

| # | Tên hàm | Input Params | Return Type & Fields Bắt Buộc | Status |
|---|---|---|---|:---:|
| 1 | `validate_orders` | `(df, contract_path)` | `list[dict]` gồm `check`, `column`, `severity`, `passed`, `details` | [x] |
| 2 | `detect_metric` | `(current, history, method="auto", context=None)` | `dict` gồm `is_anomaly`, `score`, `method`, `reason` | [x] |
| 3 | `detect_distribution` | `(current_values, baseline_values)` | `dict` gồm `is_anomaly`, `score`, `method`, `reason` | [x] |
| 4 | `slo_status` | `(target, bad_events, total_events)` | `dict` gồm `allowed_bad_rate`, `actual_bad_rate`, `burn_rate`, `remaining_error_budget_fraction`, `breached` | [x] |
| 5 | `multiwindow_burn` | `(short_window_burn, long_window_burn)` | `dict` gồm `page`, `severity`, `reason` | [x] |
| 6 | `downstream_assets` | `(graph, start)` | `list[str]` (danh sách transitive downstream assets) | [x] |
| 7 | `column_downstream` | `(graph, start)` | `list[str]` (danh sách transitive downstream columns) | [x] |
| 8 | `rag_length_shift` | `(current_texts, baseline_batch_means)` | `dict` anomaly | [x] |
| 9 | `rag_embedding_shift` | `(current_norms, baseline_norms)` | `dict` anomaly | [x] |

---

## 📊 PHẦN 4: BẢNG TÍNH ĐIỂM & DANH SÁCH BONUS

### 1. Điểm Chuẩn (100 Điểm)
| Hạng mục | Điểm tối đa | Điểm đạt được |
|---|:---:|:---:|
| Baseline & system understanding | 5 | 5 |
| Data contract / deterministic validation | 10 | 10 |
| Great Expectations hoặc equivalent validation flow | 10 | 10 |
| dbt data tests + transformation correctness | 10 | 10 |
| Anomaly detection | 15 | 15 |
| Lineage + blast radius | 15 | 15 |
| SLI / SLO / error budget | 10 | 10 |
| Mystery incident RCA | 15 | 15 |
| Incident report | 5 | 5 |
| Giải thích & bảo vệ giải pháp (Defend solution) | 5 | 5 |
| **TỔNG CỘNG** | **100** | **100** |

### 2. Điểm Bonus Gợi Ý (Đã hoàn thành đầy đủ)
- [x] MAD / same-weekday anomaly detector (**+3 điểm**)
- [x] dbt native unit test cho SCD/join inflation (**+3 điểm**)
- [x] GX severity / actions (**+3 điểm**)
- [x] Automatic quarantine cho bad records (**+3 điểm**)
- [x] Column-level transitive lineage (**+7 điểm**)
- [x] Multi-window burn-rate alerting policy (**+7 điểm**)
- [x] RAG embedding / token drift metrics (**+7 điểm**)

---

## ⚡ PHẦN 5: CHEAT SHEET CÁC LỆNH CHẠY THƯỜNG DÙNG

```bash
# 1. Reset và chuẩn bị baseline
make reset
make baseline

# 2. Chạy public test suite (19/19 passed)
pytest tests_public -v

# 3. Chạy dbt models & tests (16/16 passed)
.venv\Scripts\dbt.exe build --project-dir dbt_project --profiles-dir dbt_project

# 4. Chạy Great Expectations validation checkpoint
python gx/validate_orders.py

# 5. Chạy Dashboard Streamlit
streamlit run dashboard/app.py

# 6. Thử nghiệm các kịch bản lỗi mẫu
python scripts/inject_fault.py duplicate_pk
python scripts/inject_fault.py volume_drop
python scripts/inject_fault.py stale_kb
```
