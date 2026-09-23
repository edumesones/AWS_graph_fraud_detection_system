from __future__ import annotations

from typing import Optional

import networkx as nx
from pyvis.network import Network


def export_to_pyvis(
    G: nx.DiGraph,
    output_path: str = "graph.html",
    physics_enabled: bool = True,
    height: str = "800px",
) -> None:
    """Exporta el grafo a HTML autónomo con Pyvis.

    Args:
        G: Grafo dirigido.
        output_path: Ruta de salida.
        physics_enabled: Si habilitar física.
        height: Alto del canvas.
    """

    net = Network(height=height, directed=True, notebook=False)
    net.barnes_hut() if physics_enabled else net.hrepulsion()
    for n, data in G.nodes(data=True):
        net.add_node(str(n), label=str(n))
    for u, v, data in G.edges(data=True):
        label = f"{data.get('amount', '')}"
        net.add_edge(str(u), str(v), title=label)
    net.show(output_path)
