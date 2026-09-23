from __future__ import annotations

import gradio as gr
import networkx as nx
import pandas as pd

from analysis.anomaly_detection import detect_outlier_nodes
from visualization.plotly_dashboard import plot_network_graph


def create_tab(graph_state: gr.State, metrics_state: gr.State) -> None:
    with gr.Row():
        threshold = gr.Slider(0.5, 0.99, value=0.9, step=0.01, label="Umbral de anomalía")
        top_n = gr.Slider(5, 100, value=20, step=1, label="Top N")
    with gr.Row():
        table = gr.Dataframe(label="Nodos anómalos")
        plot = gr.Plot(label="Visualización de anomalías")
    with gr.Row():
        debug_info = gr.Textbox(label="DEBUG", interactive=False, lines=3)

    def _update(thr: float, k: int):
        # LEER DEL ESTADO (no recibir como parámetro)
        G = graph_state.value
        metrics = metrics_state.value
        
        debug_msg = f"Graph type: {type(G)}, Metrics type: {type(metrics)}"
        
        if G is None or metrics is None:
            debug_msg += " | Status: Graph or Metrics is None"
            return pd.DataFrame([["status", "no data"]], columns=["metric", "value"]), None, debug_msg
        
        if isinstance(metrics, pd.DataFrame):
            debug_msg += f" | Metrics shape: {metrics.shape}, empty: {metrics.empty}"
        
        if metrics.empty:
            return pd.DataFrame([["status", "metrics empty"]], columns=["metric", "value"]), None, debug_msg
        
        try:
            out = detect_outlier_nodes(G, metrics, threshold=thr)
            debug_msg += f" | Outliers found: {len(out) if out is not None else 0}"
            
            if out is None or out.empty:
                return pd.DataFrame([["status", "no outliers"]], columns=["metric", "value"]), None, debug_msg
            
            out_top = out.head(int(k))
            highlight = out_top["node_id"].tolist() if "node_id" in out_top.columns else []
            fig = plot_network_graph(G, color_by="anomaly_score", highlight_nodes=highlight)
            debug_msg += f" | Figure generated successfully"
            return out_top, fig, debug_msg
        except Exception as e:
            debug_msg += f" | ERROR: {str(e)}"
            return pd.DataFrame([["error", str(e)]], columns=["metric", "value"]), None, debug_msg

    # SIN graph_state ni metrics_state en inputs
    threshold.change(_update, inputs=[threshold, top_n], outputs=[table, plot, debug_info])
    top_n.change(_update, inputs=[threshold, top_n], outputs=[table, plot, debug_info])