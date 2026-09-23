from __future__ import annotations

from analysis.anomaly_detection import detect_outlier_nodes
from analysis.graph_builder import build_graph_from_transactions
from analysis.network_metrics import compute_node_metrics
from data.synthetic_generator import generate_transactions


def test_detect_outliers_runs():
    df = generate_transactions(seed=20, num_transactions=150)
    G = build_graph_from_transactions(df)
    m = compute_node_metrics(G)
    out = detect_outlier_nodes(G, m, threshold=0.9)
    assert not out.empty
