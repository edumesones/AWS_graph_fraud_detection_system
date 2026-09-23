from __future__ import annotations

from typing import Iterable

import gradio as gr
import networkx as nx
import pandas as pd

from analysis.network_metrics import compute_node_metrics
from visualization.plotly_dashboard import plot_network_graph


def create_tab(graph_state: gr.State, metrics_state: gr.State) -> None:
    with gr.Row():
        anomaly_threshold = gr.Slider(0.0, 1.0, value=0.85, step=0.01, label="Umbral de anomalía")
        color_by = gr.Dropdown(["community", "anomaly_score", "degree"], value="community", label="Color por")
    with gr.Row():
        stats_table = gr.Dataframe(headers=["metric", "value"], label="Estadísticas del grafo")
    with gr.Row():
        graph_plot = gr.Plot(label="Grafo completo")
    with gr.Row():
        debug_info = gr.Textbox(label="DEBUG", interactive=False, lines=3)

    def update_overview(min_score: float, color: str):
        # Leer desde estado (patrón anomalies)
        graph = graph_state.value
        debug_msg = f"Graph type: {type(graph)}, Graph is None: {graph is None}"
        
        if graph is None:
            debug_msg += " | Status: Graph is None"
            return pd.DataFrame([["status", "no graph"]], columns=["metric", "value"]), None, debug_msg
        
        try:
            debug_msg += f" | Nodes: {graph.number_of_nodes()}, Edges: {graph.number_of_edges()}"
            metrics_df = compute_node_metrics(graph)
            metrics_state.value = metrics_df
            debug_msg += f" | Metrics shape: {metrics_df.shape}"
            
            # annotate anomaly score simple
            metrics_df = metrics_df.copy()
            if "pagerank" in metrics_df.columns:
                max_pr = metrics_df["pagerank"].max() or 1.0
                metrics_df["anomaly_score"] = metrics_df["pagerank"] / max_pr
            
            # push into graph for coloring
            for _, row in metrics_df.iterrows():
                n = row["node_id"]
                graph.nodes[n]["anomaly_score"] = float(row.get("anomaly_score", 0.0))
            
            fig = plot_network_graph(graph, color_by=color)
            debug_msg += f" | Figure type: {type(fig)}"
            
            summary = pd.DataFrame(
                [["nodes", graph.number_of_nodes()], ["edges", graph.number_of_edges()]],
                columns=["metric", "value"],
            )
            return summary, fig, debug_msg
        except Exception as e:
            debug_msg += f" | ERROR: {str(e)}"
            return pd.DataFrame([["error", str(e)]], columns=["metric", "value"]), None, debug_msg

    anomaly_threshold.change(
        update_overview,
        inputs=[anomaly_threshold, color_by],
        outputs=[stats_table, graph_plot, debug_info],
    )
    color_by.change(
        update_overview,
        inputs=[anomaly_threshold, color_by],
        outputs=[stats_table, graph_plot, debug_info],
    )
