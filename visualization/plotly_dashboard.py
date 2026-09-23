from __future__ import annotations

from typing import Iterable, List, Optional

import networkx as nx
import plotly.graph_objects as go

from .components import make_network_figure


def plot_network_graph(
    G: nx.DiGraph, color_by: str = "community", highlight_nodes: Optional[Iterable[str]] = None
) -> go.Figure:
    """Renderiza grafo con coloración básica.

    Args:
        G: Grafo dirigido.
        color_by: community | anomaly_score | degree
        highlight_nodes: nodos a resaltar.
    """

    node_color_map: dict[str, str] = {}
    if color_by == "degree":
        # Mapa simple por percentiles
        deg = dict(G.degree())
        # No aplicamos escala continua por simplicidad del MVP
        for n, d in deg.items():
            node_color_map[n] = "#60a5fa" if d <= 3 else "#2563eb"
    elif color_by == "anomaly_score":
        for n, data in G.nodes(data=True):
            score = float(data.get("anomaly_score", 0.0))
            node_color_map[n] = "#60a5fa" if score < 0.7 else "#ef4444"
    else:  # community
        for n, data in G.nodes(data=True):
            c = int(data.get("community", -1))
            node_color_map[n] = {
                -1: "#60a5fa",
                0: "#a78bfa",
                1: "#34d399",
                2: "#f472b6",
                3: "#f59e0b",
            }.get(c, "#60a5fa")

    return make_network_figure(G, node_color_map=node_color_map, highlight_nodes=highlight_nodes)


def plot_transaction_flow(G: nx.DiGraph, start_node: str, max_hops: int = 3) -> go.Figure:
    """Visualiza flujo de transacciones desde un nodo dado."""

    nodes = {start_node}
    frontier = {start_node}
    for _ in range(max_hops):
        new_frontier = set()
        for n in frontier:
            new_frontier.update(G.successors(n))
        nodes.update(new_frontier)
        frontier = new_frontier
    sub = G.subgraph(nodes).copy()
    return make_network_figure(sub, highlight_nodes=[start_node])


def plot_subgraph(G: nx.DiGraph, nodes: List[str]) -> go.Figure:
    """Visualiza un subgrafo específico."""

    sub = G.subgraph(nodes).copy()
    return make_network_figure(sub, highlight_nodes=nodes)
