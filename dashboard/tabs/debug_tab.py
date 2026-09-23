from __future__ import annotations

import gradio as gr
import networkx as nx
import pandas as pd


def create_debug_tab(graph_state: gr.State, metrics_state: gr.State, communities_state: gr.State, data_state: gr.State = None) -> None:
    with gr.Row():
        refresh_btn = gr.Button("Refrescar Estado")
    
    state_info = gr.Textbox(label="Estado Global", interactive=False, lines=25)
    
    def show_state():
        msg = ""
        msg += "=" * 60 + "\n"
        msg += "GRAPH STATE\n"
        msg += "=" * 60 + "\n"
        msg += f"Type: {type(graph_state.value)}\n"
        
        if graph_state.value is not None:
            if isinstance(graph_state.value, nx.DiGraph):
                msg += f"✓ Nodos: {graph_state.value.number_of_nodes()}\n"
                msg += f"✓ Edges: {graph_state.value.number_of_edges()}\n"
                if graph_state.value.number_of_nodes() > 0:
                    first_node = list(graph_state.value.nodes())[0]
                    msg += f"✓ Sample node: {first_node}\n"
            else:
                msg += f"✗ No es DiGraph: {str(graph_state.value)[:100]}\n"
        else:
            msg += "✗ Es None\n"
        
        msg += "\n" + "=" * 60 + "\n"
        msg += "DATA STATE\n"
        msg += "=" * 60 + "\n"
        
        if data_state is not None:
            msg += f"Type: {type(data_state.value)}\n"
            if data_state.value is not None:
                if isinstance(data_state.value, dict):
                    msg += f"✓ Es dict\n"
                    msg += f"  Keys: {list(data_state.value.keys())}\n"
                    
                    if 'df' in data_state.value:
                        df = data_state.value['df']
                        if isinstance(df, pd.DataFrame):
                            msg += f"  ✓ df: {df.shape}\n"
                            msg += f"    Columns: {df.columns.tolist()}\n"
                            if len(df) > 0:
                                msg += f"    Sample is_fraudulent: {df['is_fraudulent'].iloc[0] if 'is_fraudulent' in df.columns else 'N/A'}\n"
                        else:
                            msg += f"  ✗ df no es DataFrame: {type(df)}\n"
                    else:
                        msg += f"  ✗ 'df' no en data_state\n"
                    
                    if 'graph' in data_state.value:
                        graph = data_state.value['graph']
                        if isinstance(graph, nx.DiGraph):
                            msg += f"  ✓ graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges\n"
                        else:
                            msg += f"  ✗ graph no es DiGraph: {type(graph)}\n"
                    else:
                        msg += f"  ✗ 'graph' no en data_state\n"
                else:
                    msg += f"✗ No es dict: {type(data_state.value)}\n"
            else:
                msg += "✗ Es None\n"
        else:
            msg += "✗ data_state no pasado a debug_tab\n"
        
        msg += "\n" + "=" * 60 + "\n"
        msg += "METRICS STATE\n"
        msg += "=" * 60 + "\n"
        msg += f"Type: {type(metrics_state.value)}\n"
        if metrics_state.value is not None:
            if isinstance(metrics_state.value, pd.DataFrame):
                msg += f"✓ Shape: {metrics_state.value.shape}\n"
            else:
                msg += f"✗ No es DataFrame: {type(metrics_state.value)}\n"
        else:
            msg += "✗ Es None\n"
        
        msg += "\n" + "=" * 60 + "\n"
        msg += "COMMUNITIES STATE\n"
        msg += "=" * 60 + "\n"
        msg += f"Type: {type(communities_state.value)}\n"
        if communities_state.value is not None:
            if isinstance(communities_state.value, dict):
                msg += f"✓ Len: {len(communities_state.value)}\n"
            else:
                msg += f"✗ No es dict: {type(communities_state.value)}\n"
        else:
            msg += "✗ Es None\n"
        
        return msg
    
    refresh_btn.click(show_state, outputs=[state_info])
