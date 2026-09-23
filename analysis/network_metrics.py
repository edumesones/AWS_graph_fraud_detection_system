from __future__ import annotations

from typing import Dict, List

import networkx as nx
import numpy as np
import pandas as pd


def compute_node_metrics(G: nx.DiGraph) -> pd.DataFrame:
    """Calcula métricas por nodo.

    Incluye: degree (in/out), betweenness, closeness, clustering (no dirigido), PageRank.

    Args:
        G: Grafo dirigido.

    Returns:
        pd.DataFrame: Una fila por nodo con métricas.
    """

    nodes = list(G.nodes())
    if not nodes:
        return pd.DataFrame(columns=[
            "node_id",
            "in_degree",
            "out_degree",
            "degree",
            "betweenness",
            "closeness",
            "clustering",
            "pagerank",
        ])

    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())
    deg = dict(G.degree())

    # Para centralidades, trabajar sobre versión no ponderada y, para clustering, no dirigido
    bet = nx.betweenness_centrality(G, normalized=True)
    clo = nx.closeness_centrality(G)
    undirected = G.to_undirected(as_view=True)
    clus = nx.clustering(undirected)
    pr = nx.pagerank(G, alpha=0.85)

    rows = []
    for n in nodes:
        rows.append({
            "node_id": n,
            "in_degree": float(in_deg.get(n, 0)),
            "out_degree": float(out_deg.get(n, 0)),
            "degree": float(deg.get(n, 0)),
            "betweenness": float(bet.get(n, 0.0)),
            "closeness": float(clo.get(n, 0.0)),
            "clustering": float(clus.get(n, 0.0)),
            "pagerank": float(pr.get(n, 0.0)),
        })

    return pd.DataFrame(rows)


def compute_graph_metrics(G: nx.DiGraph) -> Dict[str, float]:
    """Calcula métricas globales del grafo.

    Returns:
        dict: densidad, num_componentes, diámetro (en componente mayor, no dirigido).
    """

    result: Dict[str, float] = {}
    result["num_nodes"] = float(G.number_of_nodes())
    result["num_edges"] = float(G.number_of_edges())
    result["density"] = float(nx.density(G))

    undirected = G.to_undirected()
    if undirected.number_of_nodes() == 0:
        result["num_components"] = 0.0
        result["diameter"] = 0.0
        return result

    components = list(nx.connected_components(undirected))
    result["num_components"] = float(len(components))
    largest = undirected.subgraph(max(components, key=len)).copy()
    try:
        result["diameter"] = float(nx.diameter(largest))
    except nx.exception.NetworkXError:
        result["diameter"] = 0.0

    return result


def identify_hub_nodes(G: nx.DiGraph, percentile: float = 90) -> List[str]:
    """Identifica nodos hub por percentil de grado.

    Args:
        G: Grafo.
        percentile: Percentil de corte (0-100).

    Returns:
        list[str]: IDs de nodos hub.
    """

    if not (0 <= percentile <= 100):
        raise ValueError("percentile debe estar en [0, 100]")

    degrees = [d for _n, d in G.degree()]
    if not degrees:
        return []
    cutoff = float(np.percentile(degrees, percentile))
    hubs = [n for n, d in G.degree() if float(d) >= cutoff]
    return hubs
