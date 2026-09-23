from __future__ import annotations

import gradio as gr

THRESHOLDS = {
    "anomaly_score": 0.85,
    "degree_percentile": 90,
    "amount_z_score": 3.0,
}

GRADIO_CONFIG = {
    "title": "Fraud Detection - Transaction Graph Analytics",
    "description": "AML & Fraud Detection Dashboard",
    "theme": gr.themes.Soft(),
}
