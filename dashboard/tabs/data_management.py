from __future__ import annotations

import functools
from typing import Tuple

import gradio as gr
import networkx as nx
import pandas as pd

from data.synthetic_generator import generate_transactions, generate_client_profiles
from analysis.graph_builder import build_graph_from_transactions
from analysis.network_metrics import compute_node_metrics
from analysis.community_detection import detect_communities


@functools.lru_cache(maxsize=2)
def _compute_all(df_csv: str) -> Tuple[nx.DiGraph, pd.DataFrame, dict, dict, pd.DataFrame]:
    try:
        df = pd.read_csv(df_csv, parse_dates=["timestamp"], infer_datetime_format=True)
        num_clients = len(df["origin_id"].unique())
        
        profiles = generate_client_profiles(num_clients=num_clients)
        # Convertir a dict si es necesario
        if not isinstance(profiles, dict):
            profiles = {i: p for i, p in enumerate(profiles)} if isinstance(profiles, (list, tuple)) else profiles
        G = build_graph_from_transactions(df, client_profiles=None)

        metrics = compute_node_metrics(G)
        comms = detect_communities(G)
        
        # Asignar communities a nodos
        for n, c in comms.items():
            if n in G.nodes:
                G.nodes[n]["community"] = c
        
        return G, metrics, comms, profiles, df
    except Exception as e:
        print(f"Error en _compute_all: {e}")
        raise

def create_tab(graph_state: gr.State, metrics_state: gr.State, communities_state: gr.State, data_state: gr.State, sync_trigger = None) -> None:
    with gr.Row():
        mode = gr.Radio(["Generar datos", "Cargar CSV"], value="Generar datos", label="Fuente de datos")
    with gr.Row():
        num_clients = gr.Slider(100, 1500, value=800, step=50, label="Clientes")
        num_transactions = gr.Slider(1000, 20000, value=8000, step=500, label="Transacciones")
        fraud_pct = gr.Slider(0.0, 0.5, value=0.08, step=0.01, label="% Fraude")
    with gr.Row():
        file_csv = gr.File(label="CSV de transacciones", file_types=[".csv"])
    with gr.Row():
        btn = gr.Button("Procesar")
    
    status_output = gr.Textbox(label="Estado", interactive=False)
    nodes_output = gr.Number(label="Nodos", interactive=False)
    edges_output = gr.Number(label="Edges", interactive=False)

    def _process(mode_val, nc, nt, fpct, uploaded):
        try:
            if mode_val == "Generar datos":
                df = generate_transactions(
                    num_transactions=int(nt), 
                    num_clients=int(nc), 
                    fraud_percentage=float(fpct), 
                    seed=42,
                    include_enhanced_columns=True,
                )
                tmp = "data/sample_data/generated_tmp.csv"
                df.to_csv(tmp, index=False)
                _compute_all.cache_clear()
                G, metrics, comms, profiles, df_out = _compute_all(tmp)
            else:
                if uploaded is None:
                    return "Suba un CSV válido", 0, 0
                _compute_all.cache_clear()
                G, metrics, comms, profiles, df_out = _compute_all(uploaded.name)
            
            # Actualizar estados directamente
            graph_state.value = G
            metrics_state.value = metrics
            communities_state.value = comms
            
            # Solo guardar tipos serializables en data_state
            # NO incluir objetos complejos como builders o filter engines
            data_state.value = {
                'df': df_out,
                'graph': G,
            }
            
            if sync_trigger is not None:
                sync_trigger.value = str((int(sync_trigger.value or 0) + 1))
            
            return f"✅ OK: {G.number_of_nodes()} nodos, {G.number_of_edges()} edges", G.number_of_nodes(), G.number_of_edges()
            
        except Exception as e:
            return f"❌ Error: {str(e)}", 0, 0

    btn.click(
        _process,
        inputs=[mode, num_clients, num_transactions, fraud_pct, file_csv],
        outputs=[status_output, nodes_output, edges_output],
    )