from student_api import rag_embedding_shift, rag_length_shift


def test_rag_length_collapse_is_detected():
    baseline_batch_means = [40, 42, 39, 41, 43, 40, 42]
    current_texts = ["x y", "a b c", "one two"]
    assert rag_length_shift(current_texts, baseline_batch_means)["is_anomaly"] is True


def test_rag_embedding_drift_is_detected():
    baseline_norms = [1.0, 1.02, 0.98, 1.01, 0.99, 1.0]
    corrupted_norms = [25.0, 26.0, 24.5]
    assert rag_embedding_shift(corrupted_norms, baseline_norms)["is_anomaly"] is True
    healthy_norms = [1.01, 0.99, 1.0]
    assert rag_embedding_shift(healthy_norms, baseline_norms)["is_anomaly"] is False

