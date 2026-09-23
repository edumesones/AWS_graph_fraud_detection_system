from __future__ import annotations

from typing import Tuple
import logging
import os

import gradio as gr
import networkx as nx
import pandas as pd

from analysis.fraud_investigation import (
    FraudPatternPresetsUI,
    ClientCentricGraphBuilder,
)
from visualization.fraud_visualizations import FraudVisualizationFactory


# Configure file logger to write into gradio.log at workspace root
_LOGGER = logging.getLogger("advanced_explorer")
if not _LOGGER.handlers:
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = False
    try:
        from logging.handlers import RotatingFileHandler
        _BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        _LOG_DIR = os.path.join(_BASE_DIR, "fraud-detection-graphs", "logs")
        os.makedirs(_LOG_DIR, exist_ok=True)
        _LOG_PATH = os.path.join(_LOG_DIR, "advanced_explorer.log")
        _rfh = RotatingFileHandler(_LOG_PATH, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
        _rfh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        _LOGGER.addHandler(_rfh)
    except Exception:
        _LOGGER.addHandler(logging.StreamHandler())

def create_tab(graph_state: gr.State, data_state: gr.State, sync_trigger=None) -> None:
    gr.Markdown(
        """
        # 🔍 Advanced Explorer - Fraud Investigation Mode
        Analiza patrones de fraude con visualizaciones interactivas.
        """
    )

    presets = FraudPatternPresetsUI.get_all_presets()
    preset_choices = [f"{p.emoji} {p.name}" for p in presets.values()]
    preset_ids = list(presets.keys())

    gr.Markdown("## 🎯 Step 1: Select Fraud Pattern")
    selected_pattern = gr.Radio(choices=preset_choices, value=preset_choices[0], label="Select Pattern")
    pattern_description = gr.Markdown()

    gr.Markdown("## 🔎 OR: Direct Client Search")
    with gr.Row():
        client_search = gr.Textbox(label="Client ID", placeholder="e.g., C00001", interactive=True)
        search_mode = gr.Radio(["Fraud Pattern", "Direct Client"], value="Fraud Pattern", label="Search Mode")

    gr.Markdown("## ⚙️ Step 2: Configure Analysis")
    with gr.Row():
        risk_threshold = gr.Slider(0.5, 1.0, value=0.7, step=0.05, label="Risk Threshold")
        max_clients = gr.Slider(5, 50, value=10, step=1, label="Max Clients")
        max_hops = gr.Slider(1, 5, value=2, step=1, label="Max Hops")
    render_btn = gr.Button("🔄 Analyze & Visualize")
    reset_btn = gr.Button("↻ Reset")

    gr.Markdown("## 📊 Step 3: Visualization")
    viz_html = gr.HTML(value="<i>Click 'Analyze & Visualize'</i>")

    gr.Markdown("## 📈 Statistics")
    
    # Selector de mes
    with gr.Row():
        month_selector = gr.Dropdown(choices=["All Time"], value="All Time", label="Select Month", interactive=True, allow_custom_value=False)
    
    with gr.Row():
        stat_nodes = gr.Textbox(interactive=False, label="Nodes", value="0")
        stat_edges = gr.Textbox(interactive=False, label="Edges", value="0")
        stat_fraud_rate = gr.Textbox(interactive=False, label="Fraud Rate (%)", value="0%")
        stat_avg_risk = gr.Textbox(interactive=False, label="Avg Risk", value="0.00")
    
    with gr.Row():
        stat_tx_total = gr.Textbox(interactive=False, label="Transactions Total", value="0")
        stat_tx_in = gr.Textbox(interactive=False, label="Transactions In", value="0")
        stat_tx_out = gr.Textbox(interactive=False, label="Transactions Out", value="0")
    
    with gr.Row():
        stat_amount_total = gr.Textbox(interactive=False, label="Total Amount", value="$0")
        stat_amount_in = gr.Textbox(interactive=False, label="Amount In", value="$0")
        stat_amount_out = gr.Textbox(interactive=False, label="Amount Out", value="$0")
    
    with gr.Row():
        stat_cash_in = gr.Textbox(interactive=False, label="Cash In", value="$0")
        stat_cash_out = gr.Textbox(interactive=False, label="Cash Out", value="$0")
    
    with gr.Row():
        stat_intl_in = gr.Textbox(interactive=False, label="International In", value="$0")
        stat_intl_out = gr.Textbox(interactive=False, label="International Out", value="$0")

    gr.Markdown("## 🔍 Details")
    details_dataframe = gr.Dataframe()

    def _on_pattern_selected(selected_text: str) -> str:
        pid = None
        for k, p in presets.items():
            if f"{p.emoji} {p.name}" == selected_text:
                pid = k
                break
        if pid is None:
            return "Pattern not found"
        p = presets[pid]
        return f"""
        ### {p.emoji} {p.name}
        **Description:** {p.description}
        **Severity:** {p.severity.upper()}
        """

    def _on_render(
        search_mode_val,
        risk_threshold_val,
        max_clients_val,
        max_hops_val,
        client_search_val,
        selected_pattern_val,
        month_val,
    ) -> Tuple[str, str, str, str, str, str, str, str, str, str, str, str, str, pd.DataFrame, list]:
        try:
            # Acceder al estado directamente
            _LOGGER.info(
                "_on_render called | mode=%s risk=%s max_clients=%s max_hops=%s client=%s month=%s",
                search_mode_val, risk_threshold_val, max_clients_val, max_hops_val, client_search_val, month_val,
            )
            if data_state.value is None or not isinstance(data_state.value, dict):
                empty_stats = ("0", "0", "0%", "0.00", "0", "0", "0", "$0", "$0", "$0", "$0", "$0", "$0", "$0")
                return ("<i>No data loaded. Go to Data Management tab first.</i>", *empty_stats, pd.DataFrame(), gr.update())

            df = data_state.value.get("df")
            G_full = data_state.value.get("graph")

            if df is None or df.empty:
                empty_stats = ("0", "0", "0%", "0.00", "0", "0", "0", "$0", "$0", "$0", "$0", "$0", "$0", "$0")
                return ("<i>Empty dataframe</i>", *empty_stats, pd.DataFrame(), gr.update())

            if G_full is None or G_full.number_of_nodes() == 0:
                empty_stats = ("0", "0", "0%", "0.00", "0", "0", "0", "$0", "$0", "$0", "$0", "$0", "$0", "$0")
                return ("<i>Invalid graph. Rebuild from Data Management tab.</i>", *empty_stats, pd.DataFrame(), gr.update())

            mode = search_mode_val if search_mode_val else "Fraud Pattern"
            risk_th = float(risk_threshold_val) if risk_threshold_val else 0.7
            max_cli = int(max_clients_val) if max_clients_val else 10
            max_h = int(max_hops_val) if max_hops_val else 2

            if mode == "Direct Client":
                cid = (client_search_val or "").strip()
                empty_stats = ("0", "0", "0%", "0.00", "0", "0", "0", "$0", "$0", "$0", "$0", "$0", "$0", "$0")
                if not cid:
                    return ("<i>Please enter a Client ID</i>", *empty_stats, pd.DataFrame(), gr.update())
                if cid not in df["origin_id"].values and cid not in df["destination_id"].values:
                    return (f"<i>Client '{cid}' not found in data</i>", *empty_stats, pd.DataFrame(), gr.update())
                builder_focused = ClientCentricGraphBuilder(G_full, df)
                G_focused = builder_focused.build_focused_graph(max_hops=max_h, client_id=cid)
                if G_focused.number_of_nodes() == 0:
                    return (f"<i>Client '{cid}' has no connections</i>", *empty_stats, pd.DataFrame(), ["All Time"])
                # Filtrar transacciones EXACTAS presentes en el grafo enfocado (frontera)
                edge_set = set(G_focused.edges())
                if len(edge_set) == 0:
                    return (f"<i>No edges after frontier filtering</i>", *empty_stats, pd.DataFrame(), ["All Time"])
                df_filtered = df[df.apply(lambda r: (r.get("origin_id"), r.get("destination_id")) in edge_set, axis=1)].copy()
                # Forzar visualización completa de red del cliente
                pid = "client_network"
                highlighted_client = cid
            else:
                selected_text = selected_pattern_val
                pid = None
                empty_stats = ("0", "0", "0%", "0.00", "0", "0", "0", "$0", "$0", "$0", "$0", "$0", "$0", "$0")
                for k, p in presets.items():
                    if f"{p.emoji} {p.name}" == selected_text:
                        pid = k
                        break
                if pid is None:
                    return ("<i>Pattern not found</i>", *empty_stats, pd.DataFrame(), ["All Time"])
                preset = presets[pid]
                highlighted_client = None

                df_filtered = df.copy()
                filter_dict = preset.filters
                for col, rule in filter_dict.items():
                    if col not in df_filtered.columns:
                        continue
                    if col == "is_fraudulent" and isinstance(rule, bool):
                        df_filtered = df_filtered[df_filtered[col] == rule]
                    elif col == "transaction_type" and isinstance(rule, list):
                        df_filtered = df_filtered[df_filtered[col].isin(rule)]
                    elif col == "fraud_type" and isinstance(rule, list):
                        df_filtered = df_filtered[df_filtered[col].isin(rule)]
                    elif col == "is_international" and isinstance(rule, bool):
                        df_filtered = df_filtered[df_filtered[col] == rule]
                    elif col == "is_anomaly" and isinstance(rule, bool):
                        df_filtered = df_filtered[df_filtered[col] == rule]
                    elif col == "amount_min" and isinstance(rule, (int, float)):
                        df_filtered = df_filtered[df_filtered["amount"] >= rule]
                    elif col == "risk_score_min" and isinstance(rule, (int, float)):
                        # Usar risk_score en lugar de avg_risk_score
                        if "risk_score" in df_filtered.columns:
                            df_filtered = df_filtered[df_filtered["risk_score"] >= rule]
                        elif "avg_risk_score" in df_filtered.columns:
                            df_filtered = df_filtered[df_filtered["avg_risk_score"] >= rule]

                if df_filtered.empty:
                    empty_stats = ("0", "0", "0%", "0.00", "0", "0", "0", "$0", "$0", "$0", "$0", "$0", "$0", "$0")
                    return (f"<i>No matches for {preset.name}</i>", *empty_stats, pd.DataFrame(), gr.update())

                builder_focused = ClientCentricGraphBuilder(G_full, df_filtered)
                G_focused = builder_focused.build_focused_graph(
                    risk_threshold=risk_th,
                    max_clients=max_cli,
                    max_hops=max_h,
                )
                if G_focused.number_of_nodes() == 0:
                    empty_stats = ("0", "0", "0%", "0.00", "0", "0", "0", "$0", "$0", "$0", "$0", "$0", "$0", "$0")
                    return ("<i>No nodes after filtering</i>", *empty_stats, pd.DataFrame(), gr.update())

            # Calcular estadísticas mensuales
            df_filtered['timestamp'] = pd.to_datetime(df_filtered['timestamp'])
            df_filtered['month'] = df_filtered['timestamp'].dt.to_period('M').astype(str)

            # Obtener meses disponibles
            available_months = ["All Time"] + sorted(df_filtered['month'].unique().tolist())

            # Filtrar por mes si no es "All Time"
            if month_val and month_val != "All Time" and month_val in df_filtered['month'].values:
                df_month = df_filtered[df_filtered['month'] == month_val].copy()
            else:
                df_month = df_filtered.copy()

            # Si es modo cliente directo, calcular estadísticas del cliente
            if mode == "Direct Client" and highlighted_client:
                df_in = df_month[df_month['destination_id'] == highlighted_client]
                df_out = df_month[df_month['origin_id'] == highlighted_client]

                tx_total = len(df_month)
                tx_in = len(df_in)
                tx_out = len(df_out)

                amount_total = df_month['amount'].sum()
                amount_in = df_in['amount'].sum()
                amount_out = df_out['amount'].sum()

                # Cash in/out (transacciones tipo CASH)
                cash_in = df_in[df_in['transaction_type'] == 'CASH']['amount'].sum() if 'transaction_type' in df_in.columns else 0
                cash_out = df_out[df_out['transaction_type'] == 'CASH']['amount'].sum() if 'transaction_type' in df_out.columns else 0

                # International in/out
                intl_in = df_in[df_in['is_international'] == True]['amount'].sum() if 'is_international' in df_in.columns else 0
                intl_out = df_out[df_out['is_international'] == True]['amount'].sum() if 'is_international' in df_out.columns else 0
            else:
                # Estadísticas generales
                tx_total = len(df_month)
                tx_in = 0
                tx_out = 0

                amount_total = df_month['amount'].sum()
                amount_in = 0
                amount_out = 0

                cash_in = df_month[df_month['transaction_type'] == 'CASH']['amount'].sum() if 'transaction_type' in df_month.columns else 0
                cash_out = 0

                intl_in = df_month[df_month['is_international'] == True]['amount'].sum() if 'is_international' in df_month.columns else 0
                intl_out = 0

            html = FraudVisualizationFactory.get_viz(pid, G_focused, df_filtered, highlighted_node=highlighted_client)
            n_nodes = str(G_focused.number_of_nodes())
            n_edges = str(G_focused.number_of_edges())
            fraud_rate = 100.0 * df_month.get("is_fraudulent", pd.Series(dtype=float)).mean() if "is_fraudulent" in df_month.columns else 0.0

            # Usar risk_score en lugar de avg_risk_score
            risk_col = "risk_score" if "risk_score" in df_month.columns else "avg_risk_score"
            avg_risk = df_month.get(risk_col, pd.Series(dtype=float)).mean() if risk_col in df_month.columns else 0.0

            # Seleccionar columnas para el detalle
            base_cols = ["origin_id", "destination_id", "amount", "timestamp", "is_fraudulent"]
            if "risk_score" in df_month.columns:
                base_cols.insert(4, "risk_score")
            elif "avg_risk_score" in df_month.columns:
                base_cols.insert(4, "avg_risk_score")

            cols = [c for c in base_cols if c in df_month.columns]
            df_details = df_month[cols].head(20).copy()

            rename_dict = {
                "origin_id": "Origin",
                "destination_id": "Destination",
                "amount": "Amount",
                "timestamp": "Timestamp",
                "risk_score": "Risk Score",
                "avg_risk_score": "Risk Score",
                "is_fraudulent": "Fraudulent",
            }
            df_details = df_details.rename(columns={k: v for k, v in rename_dict.items() if k in df_details.columns})

            _LOGGER.info(
                "render ok | mode=%s pid=%s nodes=%s edges=%s tx_total=%s amount_total=%s",
                mode, pid, n_nodes, n_edges, tx_total, amount_total,
            )
            return (
                html,
                n_nodes,
                n_edges,
                f"{fraud_rate:.1f}%",
                f"{avg_risk:.2f}",
                str(tx_total),
                str(tx_in),
                str(tx_out),
                f"${amount_total:,.2f}",
                f"${amount_in:,.2f}",
                f"${amount_out:,.2f}",
                f"${cash_in:,.2f}",
                f"${cash_out:,.2f}",
                f"${intl_in:,.2f}",
                f"${intl_out:,.2f}",
                df_details,
                gr.update(choices=available_months, value=(month_val if month_val in available_months else "All Time")),
            )
        except Exception as e:
            import traceback
            _LOGGER.error("render failed: %s", str(e), exc_info=True)
            error_msg = f"<i>Error: {str(e)}<br><br>{traceback.format_exc()}</i>"
            empty_stats = ("0", "0", "0%", "0.00", "0", "0", "0", "$0", "$0", "$0", "$0", "$0", "$0", "$0")
            return (error_msg, *empty_stats, pd.DataFrame(), gr.update())

    def _on_reset() -> Tuple[str, str, str, str, str, str, str, str, str, str, str, str, str, str, pd.DataFrame, list]:
        _LOGGER.info("reset visualization requested")
        empty_stats = ("0", "0", "0%", "0.00", "0", "0", "0", "$0", "$0", "$0", "$0", "$0", "$0", "$0")
        return (
            "<i>Visualization cleared. Click 'Analyze & Visualize' to start again.</i>",
            *empty_stats,
            pd.DataFrame(),
            ["All Time"],
        )

    selected_pattern.change(_on_pattern_selected, inputs=[selected_pattern], outputs=[pattern_description])
    
    # Definir los inputs y outputs comunes para todas las acciones de renderizado
    render_inputs = [search_mode, risk_threshold, max_clients, max_hops, client_search, selected_pattern, month_selector]
    render_outputs = [
        viz_html, 
        stat_nodes, 
        stat_edges, 
        stat_fraud_rate, 
        stat_avg_risk,
        stat_tx_total,
        stat_tx_in,
        stat_tx_out,
        stat_amount_total,
        stat_amount_in,
        stat_amount_out,
        stat_cash_in,
        stat_cash_out,
        stat_intl_in,
        stat_intl_out,
        details_dataframe,
        month_selector,
    ]
    
    render_btn.click(
        _on_render,
        inputs=render_inputs,
        outputs=render_outputs,
    )
    # Simplificar: evitar triggers automáticos que pueden colisionar; usar solo el botón y el cambio de mes
    month_selector.change(
        _on_render,
        inputs=render_inputs,
        outputs=render_outputs,
    )
    reset_btn.click(_on_reset, inputs=[], outputs=render_outputs)
