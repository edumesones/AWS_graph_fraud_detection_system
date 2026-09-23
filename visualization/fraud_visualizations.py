from __future__ import annotations

from typing import Dict, List, Optional

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .interactive_graph_explorer import InteractiveGraphExplorer


class RiskScoreHeatmap:
    @staticmethod
    def render(G: nx.DiGraph, df: pd.DataFrame, title: str = "Risk Score Heatmap") -> str:
        origins = list(df["origin_id"].unique())
        destinations = list(df["destination_id"].unique())
        all_nodes = sorted(set(origins + destinations))
        matrix = np.zeros((len(all_nodes), len(all_nodes)))
        for u, v, data in G.edges(data=True):
            if u in all_nodes and v in all_nodes:
                i = all_nodes.index(u)
                j = all_nodes.index(v)
                matrix[i][j] = float(data.get("avg_risk_score", 0.0))
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=all_nodes,
            y=all_nodes,
            colorscale="RdYlGn_r",
            hovertemplate="%{y} → %{x}: %{z:.2f}<extra></extra>",
            colorbar=dict(title="Risk Score"),
        ))
        fig.update_layout(title=title, xaxis_title="Destination", yaxis_title="Origin", height=600, width=800)
        return fig.to_html(include_plotlyjs="cdn")


class TimelineVisualization:
    @staticmethod
    def render(df: pd.DataFrame, title: str = "Transaction Timeline") -> str:
        dff = df.copy()
        dff["timestamp"] = pd.to_datetime(dff["timestamp"])  # robusto
        fig = px.scatter(
            dff,
            x="timestamp",
            y="amount",
            color="is_fraudulent",
            size="amount",
            hover_data=["origin_id", "destination_id"],
            title=title,
            color_discrete_map={True: "red", False: "blue"},
            labels={"timestamp": "Time", "amount": "Amount ($)", "is_fraudulent": "Fraudulent"},
        )
        fig.update_layout(height=500, width=1000, hovermode="closest")
        return fig.to_html(include_plotlyjs="cdn")


class StructuringVisualization:
    def __init__(self, G: nx.DiGraph, df: pd.DataFrame):
        self.G = G
        self.df = df

    def render(self) -> str:
        from analysis.fraud_investigation import FraudPatternDetector

        detector = FraudPatternDetector(self.G, self.df)
        cases = detector.detect_structuring()
        if not cases:
            return "<i>No structuring patterns detected</i>"
        main = cases[0]
        origin = main["origin"]
        destinations = main["destinations"]
        df_case = self.df[(self.df["origin_id"] == origin) & (self.df["destination_id"].isin(destinations))].copy()
        timeline_html = TimelineVisualization.render(df_case, f"Structuring Timeline: {origin} → {destinations}")
        G_focus = self.G.subgraph([origin] + destinations).copy()
        heatmap_html = RiskScoreHeatmap.render(G_focus, df_case, f"Risk Heatmap: {origin}")
        return f"""
        <div style="font-family: Arial, sans-serif;">
            <h3>Structuring Detection</h3>
            <p><b>Origin:</b> {origin}</p>
            <p><b>Destinations:</b> {', '.join(destinations)}</p>
            <hr/>
            <h4>📊 Timeline</h4>
            {timeline_html}
            <hr/>
            <h4>🔥 Risk Heatmap</h4>
            {heatmap_html}
        </div>
        """


class MoneylauderingCycleVisualization:
    def __init__(self, G: nx.DiGraph, df: pd.DataFrame):
        self.G = G
        self.df = df

    def render(self) -> str:
        from analysis.fraud_investigation import FraudPatternDetector

        detector = FraudPatternDetector(self.G, self.df)
        cycles = detector.detect_cycles()
        if not cycles:
            return "<i>No cycles detected</i>"
        main_cycle, main_risk = cycles[0]
        G_cycle = self.G.subgraph(main_cycle).copy()
        explorer = InteractiveGraphExplorer()
        graph_html = explorer.render_with_options(G_cycle, node_size_by="avg_risk_score", edge_width_by="weight", color_by="avg_risk_score")
        cycles_list = "<br/>".join([f"{i+1}. {' → '.join(c)} (risk: {r:.2f})" for i, (c, r) in enumerate(cycles[:5])])
        return f"""
        <div style="font-family: Arial, sans-serif;">
            <h3>Money Laundering Cycles Detected</h3>
            <p><b>Main Cycle:</b> {' → '.join(main_cycle)} ↻</p>
            <p><b>Risk Score:</b> {main_risk:.2f}</p>
            <hr/>
            <h4>Top Cycles:</h4>
            <p>{cycles_list}</p>
            <hr/>
            <h4>Cycle Graph:</h4>
            {graph_html}
        </div>
        """


class MuleAccountVisualization:
    def __init__(self, G: nx.DiGraph, df: pd.DataFrame):
        self.G = G
        self.df = df

    def render(self) -> str:
        from analysis.fraud_investigation import FraudPatternDetector

        detector = FraudPatternDetector(self.G, self.df)
        mules = detector.detect_mule_accounts()
        if not mules:
            return "<i>No mule accounts detected</i>"
        main_mule = mules[0]
        mule_id = main_mule["mule_id"]
        neighbors: List[str] = []
        neighbors += list(self.G.successors(mule_id))
        neighbors += list(self.G.predecessors(mule_id))
        G_mule = self.G.subgraph([mule_id] + neighbors).copy()
        explorer = InteractiveGraphExplorer()
        graph_html = explorer.render_with_options(G_mule)
        table_rows = "".join(
            [
                f"<tr><td>{m['mule_id']}</td><td>{m['total_degree']}</td><td>${m['total_volume']:,.0f}</td><td>{m['num_transactions']}</td><td>{m['risk_score']:.2f}</td></tr>"
                for m in mules[:5]
            ]
        )
        return f"""
        <div style="font-family: Arial, sans-serif;">
            <h3>Mule Accounts Detected</h3>
            <p><b>Primary Mule:</b> {mule_id}</p>
            <hr/>
            <h4>Top Mule Accounts:</h4>
            <table border='1' cellpadding='5'>
                <tr><th>Mule ID</th><th>Degree</th><th>Volume</th><th>Transactions</th><th>Risk</th></tr>
                {table_rows}
            </table>
            <hr/>
            <h4>Mule Network Graph:</h4>
            {graph_html}
        </div>
        """


class InternationalHighValueVisualization:
    def __init__(self, G: nx.DiGraph, df: pd.DataFrame):
        self.G = G
        self.df = df

    def render(self) -> str:
        df_intl = self.df[self.df.get("is_international", pd.Series(False)).astype(bool)].copy()
        if df_intl.empty:
            return "<i>No international transactions</i>"
        country_flows = df_intl.groupby(["origin_country", "destination_country"]).agg({"amount": "sum", "is_fraudulent": "sum"}).reset_index()
        countries = sorted(set(country_flows["origin_country"].tolist() + country_flows["destination_country"].tolist()))
        matrix = np.zeros((len(countries), len(countries)))
        for _, row in country_flows.iterrows():
            i = countries.index(row["origin_country"])
            j = countries.index(row["destination_country"])
            matrix[i][j] = float(row["amount"])
        fig = go.Figure(data=go.Heatmap(z=matrix, x=countries, y=countries, colorscale="YlOrRd", hovertemplate="%{y} → %{x}: $%{z:,.0f}<extra></extra>"))
        fig.update_layout(title="International Transaction Flows (Amount in $)", xaxis_title="Destination Country", yaxis_title="Origin Country", height=600, width=800)
        heatmap_html = fig.to_html(include_plotlyjs="cdn")
        df_top = df_intl.nlargest(10, "amount")[
            ["origin_id", "destination_id", "origin_country", "destination_country", "amount", "is_fraudulent"]
        ]
        table_html = df_top.to_html(index=False)
        return f"""
        <div style="font-family: Arial, sans-serif;">
            <h3>International High-Value Transactions</h3>
            <hr/>
            <h4>Transaction Flows by Country:</h4>
            {heatmap_html}
            <hr/>
            <h4>Top 10 Transactions:</h4>
            {table_html}
        </div>
        """


class AnomaliesVisualization:
    def __init__(self, G: nx.DiGraph, df: pd.DataFrame):
        self.G = G
        self.df = df

    def render(self, highlighted_node: str = None) -> str:
        from analysis.fraud_investigation import FraudPatternDetector

        detector = FraudPatternDetector(self.G, self.df)
        anomalies = detector.detect_anomalies()
        
        # Siempre generar visualización del grafo
        explorer = InteractiveGraphExplorer(self.G, self.df)
        graph_html = explorer.render(highlighted_node=highlighted_node)
        
        if not anomalies:
            return f"""
            <div style="font-family: Arial, sans-serif;">
                <h3>Client Network Visualization</h3>
                <p><i>No anomalies detected in this network</i></p>
                {graph_html}
            </div>
            """
        
        rows = "".join(
            [
                f"<tr><td>{a['client_id']}</td><td>{a['account_age_days']}</td><td>{a['num_transactions']}</td><td>${a['total_volume']:,.0f}</td><td>{a['anomaly_score']:.2f}</td></tr>"
                for a in anomalies[:10]
            ]
        )
        return f"""
        <div style="font-family: Arial, sans-serif;">
            <h3>Detected Anomalies</h3>
            <table border='1' cellpadding='5'>
                <tr><th>Client ID</th><th>Account Age (days)</th><th>Transactions</th><th>Volume</th><th>Anomaly Score</th></tr>
                {rows}
            </table>
            <br>
            {graph_html}
        </div>
        """


class ClientNetworkVisualization:
    def __init__(self, G: nx.DiGraph, df: pd.DataFrame):
        self.G = G
        self.df = df

    def render(self, highlighted_node: Optional[str] = None) -> str:
        explorer = InteractiveGraphExplorer(self.G, self.df)
        # Usar atributos existentes en el grafo construido: nodos (num_transactions, total_volume), edges (amount)
        cache_key = None
        export_path = None
        if highlighted_node:
            cache_key = f"client_{highlighted_node}"
            export_path = f"exports/client_{highlighted_node}_graph.html"

        graph_html = explorer.render_with_options(
            self.G,
            highlighted_node=highlighted_node,
            node_size_by="num_transactions",
            edge_width_by="num_transactions",
            color_by="total_volume",
            min_edge_weight=1,
            layout="radial",
            seed=42,
            layout_cache_key=cache_key,
            reuse_cached_layout=True,
            export_html_path=export_path,
            spacing_scale=2.4,
            radial_center_node=highlighted_node,
            show_labels=False,
        )
        return f"""
        <div style="font-family: Arial, sans-serif;">
            <h3>Client Network</h3>
            {graph_html}
        </div>
        """


class FraudVisualizationFactory:
    @staticmethod
    def get_viz(pattern_type: str, G: nx.DiGraph, df: pd.DataFrame, highlighted_node: str = None) -> str:
        if pattern_type == "structuring":
            return StructuringVisualization(G, df).render()
        if pattern_type == "money_laundering":
            return MoneylauderingCycleVisualization(G, df).render()
        if pattern_type == "mule_accounts":
            return MuleAccountVisualization(G, df).render()
        if pattern_type == "international_highvalue":
            return InternationalHighValueVisualization(G, df).render()
        if pattern_type == "anomalies":
            return AnomaliesVisualization(G, df).render(highlighted_node=highlighted_node)
        if pattern_type == "client_network":
            return ClientNetworkVisualization(G, df).render(highlighted_node=highlighted_node)
        return f"<i>Unknown pattern type: {pattern_type}</i>"
