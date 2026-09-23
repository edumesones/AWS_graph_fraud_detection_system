from __future__ import annotations

import networkx as nx

from analysis.graph_builder import build_graph_from_transactions
from data.synthetic_generator import generate_transactions


def test_graph_structure():
    df = generate_transactions(seed=42, num_transactions=100)
    G = build_graph_from_transactions(df)
    assert isinstance(G, nx.DiGraph)
    assert G.number_of_nodes() > 0
    assert G.number_of_edges() == len(df)


def test_node_attributes():
    df = generate_transactions(seed=1, num_transactions=50)
    G = build_graph_from_transactions(df)
    n = next(iter(G.nodes()))
    data = G.nodes[n]
    for key in ["profile_type", "country", "account_age_days", "num_transactions", "total_volume"]:
        assert key in data


def test_edge_attributes():
    df = generate_transactions(seed=5, num_transactions=50)
    G = build_graph_from_transactions(df)
    u, v = next(iter(G.edges()))
    data = G[u][v]
    for key in ["transaction_id", "amount", "timestamp", "description", "is_fraudulent", "fraud_type", "risk_score"]:
        assert key in data
