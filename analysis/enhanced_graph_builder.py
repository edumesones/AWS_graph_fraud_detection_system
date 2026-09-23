from __future__ import annotations

from typing import Any, Dict, Optional

import networkx as nx
import pandas as pd

from .dynamic_filter_engine import DynamicFilterEngine
from .transaction_aggregator import TransactionAggregator


class EnhancedGraphBuilder:
    """Construye grafos enriquecidos con filtros y agregación de transacciones."""

    def __init__(self, df: pd.DataFrame, client_profiles: Optional[Dict[str, Dict[str, Any]]] = None):
        if not isinstance(df, pd.DataFrame):
            raise TypeError("df debe ser pandas.DataFrame")
        self.df = df.copy()
        self.client_profiles = client_profiles or {}
        self.filter_engine = DynamicFilterEngine(self.df)
        self.aggregator = TransactionAggregator()

    def get_available_filters(self) -> Dict[str, Dict[str, Any]]:
        return self.filter_engine.get_filter_suggestions()

    def build_graph(self, filters: Optional[Dict[str, Any]] = None) -> nx.DiGraph:
        # 1. Filtrar
        df_filtered = self.filter_engine.apply_filters(filters or {})
        # 2. Agregar transacciones por arista
        agg = self.aggregator.aggregate(df_filtered)
        # 3. Construir grafo
        G = nx.DiGraph()

        # Nodos desde df (origen y destino)
        nodes = pd.unique(pd.concat([df_filtered["origin_id"], df_filtered["destination_id"]], ignore_index=True))
        for n in nodes:
            if pd.isna(n):
                continue
            n_str = str(n)
            prof = self.client_profiles.get(n_str, {})
            G.add_node(
                n_str,
                profile_type=str(prof.get("profile_type", prof.get("perfil", "unknown"))),
                country=str(prof.get("country", "NA")),
                nationality=str(prof.get("nationality", prof.get("country", "NA"))),
                account_age_days=int(prof.get("account_age_days", 0)),
            )

        # Edges con atributos agregados
        for (o, d), attrs in agg.items():
            if o not in G:
                G.add_node(o)
            if d not in G:
                G.add_node(d)
            G.add_edge(
                o,
                d,
                weight=float(attrs["total_amount"]),
                num_transactions=int(attrs["num_transactions"]),
                transaction_types=attrs.get("transaction_types", {}),
                channels=attrs.get("channels", {}),
                average_amount=float(attrs["average_amount"]),
                min_amount=float(attrs["min_amount"]),
                max_amount=float(attrs["max_amount"]),
                first_transaction=attrs.get("first_transaction"),
                last_transaction=attrs.get("last_transaction"),
                is_international=bool(attrs.get("is_international", False)),
                num_fraudulent=int(attrs.get("num_fraudulent", 0)),
                fraud_rate=float(attrs.get("fraud_rate", 0.0)),
                avg_risk_score=float(attrs.get("avg_risk_score", 0.0)),
            )

        # Atributos derivados de grado y volumen
        for n in list(G.nodes()):
            G.nodes[n]["degree_in"] = int(G.in_degree(n))
            G.nodes[n]["degree_out"] = int(G.out_degree(n))
            total_volume = 0.0
            for _, _, d in G.out_edges(n, data=True):
                total_volume += float(d.get("weight", 0.0))
            for _, _, d in G.in_edges(n, data=True):
                total_volume += float(d.get("weight", 0.0))
            G.nodes[n]["total_volume"] = float(total_volume)

        return G
