from __future__ import annotations

from data.synthetic_generator import generate_transactions
from analysis.graph_builder import build_graph_from_transactions
from analysis.network_metrics import compute_node_metrics
from analysis.community_detection import detect_communities
from analysis.anomaly_detection import detect_outlier_nodes


def main() -> None:
    df = generate_transactions(seed=42, num_transactions=1000)
    G = build_graph_from_transactions(df)
    metrics = compute_node_metrics(G)
    communities = detect_communities(G)
    anomalies = detect_outlier_nodes(G, metrics, threshold=0.9)
    print(f"Grafo: {G.number_of_nodes()} nodos, {G.number_of_edges()} edges")
    print(f"Anomalías detectadas: {len(anomalies)}")


if __name__ == "__main__":
    main()
