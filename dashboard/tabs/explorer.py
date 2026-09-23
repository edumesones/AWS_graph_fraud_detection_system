from __future__ import annotations

from typing import List

import gradio as gr
import networkx as nx
import pandas as pd

from visualization.plotly_dashboard import plot_transaction_flow


def create_tab(graph_state: gr.State) -> None:
    with gr.Row():
        client_id = gr.Textbox(label="Client ID", value="C00001")
        num_hops = gr.Slider(1, 3, value=2, step=1, label="Hops")
    with gr.Row():
        plot = gr.Plot(label="Vecindario")
    with gr.Row():
        debug_info = gr.Textbox(label="DEBUG", interactive=False, lines=3)

    def _update(cid: str, hops: int):
        # Leer desde estado (patrón anomalies)
        G = graph_state.value
        debug_msg = f"Graph type: {type(G)}, Client ID: {cid}, Hops: {hops}"
        
        if G is None or cid is None:
            debug_msg += " | Status: Graph or Client ID is None"
            return None, debug_msg
        
        try:
            debug_msg += f" | Graph nodes: {G.number_of_nodes()}"
            
            if cid not in G.nodes:
                available_nodes = list(G.nodes())[:5]
                debug_msg += f" | Client {cid} not found. Available: {available_nodes}"
                if not available_nodes:
                    return None, debug_msg
                cid = available_nodes[0]
                debug_msg += f" | Using first available: {cid}"
            
            fig = plot_transaction_flow(G, cid, max_hops=int(hops))
            debug_msg += f" | Figure generated successfully"
            return fig, debug_msg
        except Exception as e:
            debug_msg += f" | ERROR: {str(e)}"
            return None, debug_msg

    client_id.change(_update, inputs=[client_id, num_hops], outputs=[plot, debug_info])
    num_hops.change(_update, inputs=[client_id, num_hops], outputs=[plot, debug_info])
