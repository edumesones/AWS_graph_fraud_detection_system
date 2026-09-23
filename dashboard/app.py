from __future__ import annotations

import gradio as gr

from dashboard.tabs import data_management, overview, communities, anomalies, explorer ,debug_tab


def main() -> gr.Blocks:
    graph_state = gr.State()
    metrics_state = gr.State()
    communities_state = gr.State()
    data_state = gr.State()

    with gr.Blocks(title="Fraud Detection") as demo:
        gr.Markdown("# 🔍 Fraud Detection - Transaction Graph Analytics")
        with gr.Tabs():
            with gr.Tab("📤 Data Management"):
                data_management.create_tab(graph_state, metrics_state, communities_state, data_state)
            with gr.Tab("📊 Overview"):
                overview.create_tab(graph_state, metrics_state)
            with gr.Tab("🔗 Communities"):
                communities.create_tab(graph_state, communities_state)
            with gr.Tab("⚠️ Anomalies"):
                anomalies.create_tab(graph_state, metrics_state)
            with gr.Tab("🔍 Explorer"):
                explorer.create_tab(graph_state)
            with gr.Tab("🧭 Advanced Explorer"):
                from dashboard.tabs.advanced_explorer_v2 import create_tab as create_adv_tab
                create_adv_tab(graph_state, data_state)
            with gr.Tab("🐛 DEBUG STATE"):
                debug_tab.create_debug_tab(graph_state, metrics_state, communities_state)
    return demo


if __name__ == "__main__":
    app = main()
    app.launch(server_name="127.0.0.1", share=False)

