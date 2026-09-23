from __future__ import annotations

from typing import List

import gradio as gr
import networkx as nx
import pandas as pd

from analysis.community_detection import analyze_community
from visualization.plotly_dashboard import plot_subgraph


def create_tab(graph_state: gr.State, communities_state: gr.State) -> None:
    with gr.Row():
        community_id = gr.Number(label="Comunidad", value=0)
    with gr.Row():
        stats_df = gr.Dataframe(label="Estadísticas de comunidad")
        community_plot = gr.Plot(label="Subgrafo de comunidad")
    with gr.Row():
        debug_info = gr.Textbox(label="DEBUG", interactive=False, lines=3)

    def update_community(cid: int):
        # Leer estado (patrón anomalies)
        graph = graph_state.value
        community_map = communities_state.value
        debug_msg = f"Graph type: {type(graph)}, Communities type: {type(community_map)}"
        
        if graph is None or community_map is None:
            debug_msg += " | Status: Graph or Communities is None"
            return pd.DataFrame([["status", "no data"]], columns=["metric", "value"]), None, debug_msg
        
        try:
            debug_msg += f" | Nodes: {graph.number_of_nodes()}, Community_map len: {len(community_map) if isinstance(community_map, dict) else 'N/A'}"
            # Asignar community al grafo si falta
            if isinstance(community_map, dict):
                for node, comm in community_map.items():
                    if node in graph.nodes:
                        graph.nodes[node]["community"] = comm
            # filtrar nodos de la comunidad
            nodes = [n for n, data in graph.nodes(data=True) if data.get("community") == int(cid)]
            debug_msg += f" | Nodes in community {cid}: {len(nodes)}"
            if not nodes:
                return pd.DataFrame([["status", f"No nodes in community {cid}"]], columns=["metric", "value"]), None, debug_msg
            stats = analyze_community(graph, int(cid))
            fig = plot_subgraph(graph, nodes)
            stats_df_out = pd.DataFrame(list(stats.items()), columns=["metric", "value"])
            debug_msg += f" | Figure generated successfully"
            return stats_df_out, fig, debug_msg
        except Exception as e:
            debug_msg += f" | ERROR: {str(e)}"
            return pd.DataFrame([["error", str(e)]], columns=["metric", "value"]), None, debug_msg

    community_id.change(
        update_community,
        inputs=[community_id],
        outputs=[stats_df, community_plot, debug_info],
    )
