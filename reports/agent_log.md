# AI Agent Decision Log

Ghi lại các quyết định kỹ thuật và kiến trúc quan trọng trong quá trình thực hiện Lab 27.

---

## Decision 1: Strict Type Validation vs. Silent Coercion in Contract Validator
- **Hypothesis:** Dùng `pd.to_numeric(..., errors='coerce')` đơn thuần có thể âm thầm biến dữ liệu chuỗi lỗi/hỏng (string corruption) thành `NaN`, làm trôi dạt kiểu dữ liệu mà không bị phát hiện.
- **Prompt / request to agent:** Implement strict type validation per column for integer, number, datetime, and boolean without masking corrupt strings. Add contract-level freshness check.
- **Agent proposal:** Xây dựng hàm `_validate_type` kiểm tra kiểu dữ liệu nguyên vẹn (strict check), phát hiện giá trị thập phân trong cột `integer`, kiểm tra timestamp hợp lệ và tính toán freshness so với UTC time.
- **Evidence/test:** Test `test_type_drift_is_detected` và `test_stale_data_freshness_is_detected` trong `tests_public/test_contracts.py` bắt được chính xác lỗi trôi kiểu dữ liệu và dữ liệu cũ.
- **Accept / reject / revise:** **Accept**.
- **Why:** Bảo vệ pipeline khỏi hiện tượng Silent Type Drift và Stale Data Ingestion trước khi dữ liệu đi vào data warehouse.

---

## Decision 2: SCD Type 2 Customer Join & Revenue Inflation Protection in dbt
- **Hypothesis:** Nếu bảng chiều `customers` có nhiều hơn 1 bản ghi `is_active = true` cho cùng một khách hàng (do lỗi SCD Type 2), phép `left join` trong `fct_daily_revenue` sẽ nhân bản dòng đơn hàng và làm doanh thu bị thổi phồng giả tạo (revenue inflation) mà không sinh lỗi SQL.
- **Prompt / request to agent:** Write the smallest dbt unit test that exposes revenue inflation when a customer dimension contains two active rows for the same customer. Hardening the model with deduplication.
- **Agent proposal:** Viết dbt unit test `test_scd_customer_duplicate_active_rows_does_not_inflate_revenue` trong `unit_tests.yml`, đồng thời cập nhật `fct_daily_revenue.sql` sử dụng CTE `select distinct customer_id from stg_customers where is_active = true`.
- **Evidence/test:** `dbt build` chạy thành công với 2 unit tests và 9 data tests đều PASS (16/16 items passed).
- **Accept / reject / revise:** **Accept**.
- **Why:** Phép `distinct` trong CTE staging/mart triệt tiêu hoàn toàn nguy cơ nhân đôi dòng khi join dimension, giữ cho báo cáo tài chính của CEO luôn chính xác.

---

## Decision 3: Robust Anomaly Detection using MAD & Seasonality Awareness
- **Hypothesis:** Thuật toán Z-score truyền thống rất nhạy cảm với ngoại lai (outliers) và dễ báo động giả vào cuối tuần (thứ Bảy/Chủ Nhật thường có lượng đơn thấp tự nhiên).
- **Prompt / request to agent:** Implement a robust MAD-based detector with zero-MAD edge case handling. Make auto mode context-aware with same-weekday segmentation and known event handling.
- **Agent proposal:** Triển khai `mad_detector` tính toán Modified Z-score (`0.6745 * |x - median| / MAD`), xử lý edge case khi MAD = 0, và bộ định tuyến `auto` tự động ưu tiên `same_segment_history` khi có thông tin `day_of_week`.
- **Evidence/test:** Các test case `test_mad_detector_handles_outliers_robustly`, `test_zero_mad_identical_history` và `test_context_aware_segment_routing` đều passed 100%.
- **Accept / reject / revise:** **Accept**.
- **Why:** Giảm thiểu triệt để False Positives do tính mùa vụ (seasonality) và đảm bảo phát hiện chính xác sự cố sụt giảm lượng đơn (`volume_drop`).

---

## Decision 4: Google SRE Multi-Window Multi-Burn-Rate Alerting Policy
- **Hypothesis:** Cảnh báo dựa trên một cửa sổ thời gian đơn lẻ hoặc ngưỡng tĩnh dễ gây "alert fatigue" khi gặp các đợt tăng vọt ngắn hạn (transient spikes) không thực sự đe dọa Error Budget.
- **Prompt / request to agent:** Implement a multi-window burn-rate policy following Google SRE workbook. Distinguish sustained fast burns (page on-call) from short transient spikes (no page).
- **Agent proposal:** Lập trình hàm `evaluate_multiwindow_burn` kết hợp cả 2 cửa sổ `short_window_burn` và `long_window_burn`. Chỉ kích hoạt `page = True` khi CẢ HAI cửa sổ đều vượt ngưỡng tiêu hao ngân sách (sustained burn).
- **Evidence/test:** `test_sustained_fast_burn_pages_oncall` (burn=14.5x) trả về `page=True`, trong khi `test_transient_spike_does_not_page` (short=8.0x, long=1.2x) trả về `page=False, severity='warning'`.
- **Accept / reject / revise:** **Accept**.
- **Why:** Đảm bảo đội ngũ on-call chỉ bị đánh thức bởi các sự cố nghiêm trọng có nguy cơ làm cạn kiệt ngân sách lỗi của hệ thống.

---

## Decision 5: Transitive Column-Level Lineage Graph Traversal
- **Hypothesis:** Lineage cấp độ dataset chỉ cho biết bảng nào bị ảnh hưởng, nhưng không cho biết chính xác cột thuộc tính (metric) nào bị tác động từ nguồn đến dashboard. Hàm starter chỉ trả về direct children mà chưa duyệt transitive.
- **Prompt / request to agent:** Implement transitive column-level lineage traversal via BFS with cycle prevention.
- **Agent proposal:** Cập nhật hàm `get_column_downstream` sử hàng đợi `deque` và tập `seen` để duyệt toàn bộ các cột downstream phụ thuộc gián tiếp qua nhiều tầng trung gian.
- **Evidence/test:** Test `test_transitive_column_downstream` kiểm tra chuỗi `raw_orders.amount -> stg_orders.amount_usd -> fct_daily_revenue.daily_revenue -> ceo_dashboard.kpi_revenue` trả về chính xác 3 cột phụ thuộc theo thứ tự BFS.
- **Accept / reject / revise:** **Accept**.
- **Why:** Cho phép đo lường phạm vi ảnh hưởng (Blast Radius) chi tiết đến từng trường dữ liệu và KPI trên báo cáo.

---

## Decision 6: Statistical Distribution Drift with KS-Test & PSI
- **Hypothesis:** Chỉ so sánh tỷ số trung bình (`mean_ratio`) không thể phát hiện các trường hợp phân phối bị biến dạng hình dạng (variance shift, bimodal, skewness) khi giá trị trung bình vẫn xấp xỉ nhau.
- **Prompt / request to agent:** Implement Kolmogorov-Smirnov (KS) test and Population Stability Index (PSI) using pure NumPy without extra heavy dependencies.
- **Agent proposal:** Lập trình `_calculate_ks_statistic` (khoảng cách cực đại giữa 2 hàm phân phối tích lũy thực nghiệm ECDF) và `_calculate_psi` (chia quantile bins và tính khoảng cách phân bố).
- **Evidence/test:** `detect_distribution_shift` tự động kết hợp cả 3 tín hiệu (KS, PSI, Mean Ratio) và pass test `test_extreme_mean_shift_detected`.
- **Accept / reject / revise:** **Accept**.
- **Why:** Cung cấp khả năng quan sát phân phối dữ liệu (Data Distribution Drift Observability) chuẩn mực công nghiệp.
