from __future__ import annotations

from typing import List

import networkx as nx
import numpy as np
import pandas as pd


def detect_outlier_nodes(
    G: nx.DiGraph, metrics: pd.DataFrame, threshold: float = 0.95
) -> pd.DataFrame:
    """Detecta nodos anómalos usando z-scores/percentiles en métricas.

    Args:
        G: Grafo.
        metrics: DataFrame devuelto por compute_node_metrics.
        threshold: Percentil global para marcar anomalías (0-1).

    Returns:
        pd.DataFrame: Subconjunto de métricas con columna extra 'anomaly_score'.
    """

    if not (0.0 <= threshold <= 1.0):
        raise ValueError("threshold debe estar en [0, 1]")

    if metrics.empty:
        return metrics.assign(anomaly_score=pd.Series(dtype=float))

    cols = [c for c in ["betweenness", "closeness", "pagerank", "degree"] if c in metrics.columns]
    if not cols:
        return metrics.assign(anomaly_score=0.0)

    values = metrics[cols].to_numpy(dtype=float)
    # Z-score simple
    mu = values.mean(axis=0)
    sigma = values.std(axis=0) + 1e-9
    z = (values - mu) / sigma
    z_abs = np.abs(z)
    # Score agregado
    agg = z_abs.mean(axis=1)

    cutoff = np.quantile(agg, threshold)
    anomaly_score = (agg - agg.min()) / (agg.max() - agg.min() + 1e-9)
    result = metrics.copy()
    result["anomaly_score"] = anomaly_score
    return result.sort_values("anomaly_score", ascending=False)


def flag_suspicious_edges(G: nx.DiGraph, amount_threshold: float) -> pd.DataFrame:
    """Marca edges con monto anómalo por encima de umbral."""

    rows = []
    for u, v, d in G.edges(data=True):
        amt = float(d.get("amount", 0.0))
        if amt >= amount_threshold:
            rows.append({
                "origin_id": u,
                "destination_id": v,
                "amount": amt,
                "timestamp": d.get("timestamp"),
                "description": d.get("description"),
                "risk_score": float(d.get("risk_score", 0.0)),
            })
    return pd.DataFrame(rows)


def compute_anomaly_score(G: nx.DiGraph, node: str) -> float:
    """Score individual simple basado en centralidad y grado."""

    if node not in G:
        return 0.0
    pr = nx.pagerank(G, alpha=0.85)
    degree = float(G.degree(node))
    max_degree = max((float(d) for _n, d in G.degree()), default=1.0)
    pr_norm = float(pr.get(node, 0.0))
    deg_norm = degree / (max_degree + 1e-9)
    return float(0.6 * pr_norm + 0.4 * deg_norm)
