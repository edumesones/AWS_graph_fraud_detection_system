from __future__ import annotations

import pandas as pd

from analysis.network_metrics import compute_node_metrics, compute_graph_metrics, identify_hub_nodes
from data.synthetic_generator import generate_transactions
from analysis.graph_builder import build_graph_from_transactions


def test_metrics_ranges():
    df = generate_transactions(seed=10, num_transactions=150)
    G = build_graph_from_transactions(df)
    m = compute_node_metrics(G)
    assert ((m["betweenness"] >= 0) & (m["betweenness"] <= 1)).all()


def test_graph_metrics_basic():
    df = generate_transactions(seed=11, num_transactions=120)
    G = build_graph_from_transactions(df)
    gm = compute_graph_metrics(G)
    assert gm["num_nodes"] > 0
    assert gm["num_edges"] > 0


def test_identify_hubs():
    df = generate_transactions(seed=12, num_transactions=200)
    G = build_graph_from_transactions(df)
    hubs = identify_hub_nodes(G, percentile=90)
    assert isinstance(hubs, list)
