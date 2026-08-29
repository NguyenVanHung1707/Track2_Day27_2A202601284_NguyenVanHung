from student_api import detect_metric


def test_large_volume_drop_is_anomaly():
    history = [1000, 1010, 995, 1008, 1004, 1012, 998]
    result = detect_metric(300, history, method="zscore")
    assert result["is_anomaly"] is True


def test_stable_value_is_not_anomaly():
    history = [1000, 1010, 995, 1008, 1004, 1012, 998]
    result = detect_metric(1002, history, method="zscore")
    assert result["is_anomaly"] is False


def test_mad_detector_handles_outliers_robustly():
    # History contains an outlier, but MAD ignores it
    history = [100, 102, 98, 101, 100, 5000, 99]
    result = detect_metric(101, history, method="mad")
    assert result["is_anomaly"] is False
    # Large drop detected
    drop_result = detect_metric(20, history, method="mad")
    assert drop_result["is_anomaly"] is True


def test_zero_mad_identical_history():
    history = [100, 100, 100, 100, 100]
    match = detect_metric(100, history, method="mad")
    assert match["is_anomaly"] is False
    diff = detect_metric(150, history, method="mad")
    assert diff["is_anomaly"] is True


def test_context_aware_segment_routing():
    general_history = [500, 510, 490, 505, 495]
    saturday_history = [1200, 1250, 1180, 1220]
    context = {"day_of_week": 5, "same_segment_history": saturday_history}
    result = detect_metric(1210, general_history, method="auto", context=context)
    assert result["is_anomaly"] is False

