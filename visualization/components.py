from __future__ import annotations

from typing import Iterable, List, Optional

import networkx as nx
import plotly.graph_objects as go


def _layout_positions(G: nx.Graph, layout: str = "spring") -> dict:
    if layout == "kamada-kawai":
        return nx.kamada_kawai_layout(G)
    return nx.spring_layout(G, seed=42)


def make_network_figure(
    G: nx.DiGraph,
    node_color_map: Optional[dict] = None,
    highlight_nodes: Optional[Iterable[str]] = None,
    layout: str = "spring",
) -> go.Figure:
    pos = _layout_positions(G, layout=layout)
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=0.5, color="#94a3b8"),
        hoverinfo="none",
        mode="lines",
        name="edges",
    )

    node_x, node_y, colors, texts = [], [], [], []
    highlight_set = set(highlight_nodes or [])
    for n, data in G.nodes(data=True):
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)
        label = f"{n}<br>degree={G.degree(n)}"  # simple hover
        texts.append(label)
        c = None
        if node_color_map is not None and n in node_color_map:
            c = node_color_map[n]
        else:
            c = "#60a5fa"
        if n in highlight_set:
            c = "#22c55e"
        colors.append(c)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers",
        hoverinfo="text",
        text=texts,
        marker=dict(
            showscale=False,
            color=colors,
            size=8,
            line_width=1,
        ),
        name="nodes",
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return fig
