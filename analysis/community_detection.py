from __future__ import annotations

from typing import Dict, List

import networkx as nx
from community import community_louvain


def detect_communities(G: nx.Graph, resolution: float = 1.0) -> Dict[str, int]:
    """Detecta comunidades con Louvain.

    Args:
        G: Grafo (se convertirá a no dirigido para Louvain).
        resolution: Parámetro de resolución.

    Returns:
        dict: {node_id: community_id}
    """

    undirected = G.to_undirected()
    partition = community_louvain.best_partition(undirected, resolution=resolution)
    # partition ya es dict node -> community
    return {str(k): int(v) for k, v in partition.items()}


def analyze_community(G: nx.DiGraph, community_id: int) -> Dict[str, float]:
    """Calcula estadísticas básicas de una comunidad específica."""

    nodes = [n for n, data in G.nodes(data=True) if data.get("community") == community_id]
    if not nodes:
        return {
            "community_id": float(community_id),
            "num_nodes": 0.0,
            "num_edges": 0.0,
            "avg_amount": 0.0,
            "total_amount": 0.0,
        }
    sub = G.subgraph(nodes)
    amounts = [float(d.get("amount", 0.0)) for _u, _v, d in sub.edges(data=True)]
    total_amount = float(sum(amounts))
    avg_amount = float(total_amount / max(1, len(amounts)))
    return {
        "community_id": float(community_id),
        "num_nodes": float(sub.number_of_nodes()),
        "num_edges": float(sub.number_of_edges()),
        "avg_amount": avg_amount,
        "total_amount": total_amount,
    }


def identify_bridge_nodes(G: nx.DiGraph, communities: Dict[str, int]) -> List[str]:
    """Nodos que conectan comunidades distintas (tienen vecinos de otra comunidad)."""

    bridge_nodes: List[str] = []
    for n in G.nodes():
        c = communities.get(n)
        neigh_comms = {communities.get(v) for v in G.successors(n)} | {communities.get(v) for v in G.predecessors(n)}
        if any((nc is not None and nc != c) for nc in neigh_comms):
            bridge_nodes.append(n)
    return bridge_nodes
