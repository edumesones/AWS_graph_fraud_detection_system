from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

import networkx as nx
import numpy as np
import pandas as pd


# =========================================================================
# 1. FRAUD PATTERN PRESETS
# =========================================================================

@dataclass
class FraudPreset:
    id: str
    name: str
    description: str
    filters: Dict[str, Any]
    viz_type: str  # 'timeline_heatmap' | 'cycle_graph' | 'hub_graph' | 'risk_matrix' | 'temporal_anomaly'
    emoji: str
    severity: str  # 'critical' | 'high' | 'medium'


class FraudPatternPresetsUI:
    PRESETS: Dict[str, FraudPreset] = {
        "structuring": FraudPreset(
            id="structuring",
            name="Cash Structuring",
            description=(
                "Muchas transacciones pequeñas (~$5K) desde un cliente hacia múltiples "
                "destinatarios en corto tiempo"
            ),
            filters={
                "transaction_type": ["cash"],
                "is_fraudulent": True,
                "fraud_type": ["structuring"],
            },
            viz_type="timeline_heatmap",
            emoji="🔴",
            severity="critical",
        ),
        "money_laundering": FraudPreset(
            id="money_laundering",
            name="Money Laundering Cycles",
            description="Ciclos cerrados A→B→C→A donde dinero regresa al origen",
            filters={
                "transaction_type": ["wire"],
                "is_fraudulent": True,
                "fraud_type": ["money_laundering"],
            },
            viz_type="cycle_graph",
            emoji="🔴",
            severity="critical",
        ),
        "mule_accounts": FraudPreset(
            id="mule_accounts",
            name="Mule Accounts",
            description=(
                "Cuentas con alto grado entrada/salida (>10 conexiones), típica rápida rotación de dinero"
            ),
            filters={"is_fraudulent": True, "fraud_type": ["mule"]},
            viz_type="hub_graph",
            emoji="🔴",
            severity="critical",
        ),
        "international_highvalue": FraudPreset(
            id="international_highvalue",
            name="International High-Value",
            description="Transacciones internacionales > $50K con riesgo > 0.7",
            filters={"is_international": True, "amount_min": 50000, "risk_score_min": 0.7},
            viz_type="risk_matrix",
            emoji="🟠",
            severity="high",
        ),
        "anomalies": FraudPreset(
            id="anomalies",
            name="Anomalies Detection",
            description="Nuevos clientes con conexiones múltiples y alto volumen en corto tiempo",
            filters={"is_anomaly": True},
            viz_type="temporal_anomaly",
            emoji="🟡",
            severity="high",
        ),
    }

    @classmethod
    def get_preset(cls, preset_id: str) -> Optional[FraudPreset]:
        return cls.PRESETS.get(preset_id)

    @classmethod
    def get_all_presets(cls) -> Dict[str, FraudPreset]:
        return cls.PRESETS

    @classmethod
    def get_filters(cls, preset_id: str) -> Dict[str, Any]:
        preset = cls.get_preset(preset_id)
        return preset.filters if preset else {}


# =========================================================================
# 2. CLIENT-CENTRIC GRAPH BUILDER
# =========================================================================

class ClientCentricGraphBuilder:
    """Construye grafo filtrado alrededor de clientes de riesgo."""

    def __init__(self, G_full: nx.DiGraph, df: pd.DataFrame):
        self.G_full = G_full
        self.df = df
        self._node_risk_scores = self._compute_node_risk_scores()
        # Use the same logger configured by the tab to write to gradio.log
        self._logger = logging.getLogger("advanced_explorer")

    def _compute_node_risk_scores(self) -> Dict[str, float]:
        node_risks: Dict[str, float] = {}
        for node in self.G_full.nodes():
            all_edge_risks: List[float] = []
            for _, _, data in self.G_full.out_edges(node, data=True):
                all_edge_risks.append(float(data.get("avg_risk_score", 0.0)))
            for _, _, data in self.G_full.in_edges(node, data=True):
                all_edge_risks.append(float(data.get("avg_risk_score", 0.0)))
            node_risks[node] = float(np.mean(all_edge_risks)) if all_edge_risks else 0.0
        return node_risks

    def _get_neighbors_by_hops(self, start_node: str, max_hops: int) -> Set[str]:
        nodes: Set[str] = {start_node}
        frontier: Set[str] = {start_node}
        for _ in range(max(0, int(max_hops))):
            next_frontier: Set[str] = set()
            for n in frontier:
                next_frontier.update(self.G_full.successors(n))
                next_frontier.update(self.G_full.predecessors(n))
            nodes.update(next_frontier)
            frontier = next_frontier
            if not frontier:
                break
        return nodes

    def _build_frontier_only(self, start_node: str, max_hops: int) -> nx.DiGraph:
        self._logger.info("frontier_only BFS | start=%s hops=%s", start_node, max_hops)
        # BFS por niveles sobre grafo no dirigido para niveles estables
        levels: Dict[str, int] = {start_node: 0}
        current: Set[str] = {start_node}
        for d in range(1, max(0, int(max_hops)) + 1):
            next_layer: Set[str] = set()
            for n in current:
                for nb in set(self.G_full.successors(n)).union(set(self.G_full.predecessors(n))):
                    if nb not in levels:
                        levels[nb] = d
                        next_layer.add(nb)
            if not next_layer:
                break
            current = next_layer

        included_nodes = {n for n, lv in levels.items() if lv <= int(max_hops)}
        Gf = nx.DiGraph()
        for n in included_nodes:
            if n in self.G_full:
                Gf.add_node(n, **self.G_full.nodes[n])

        # incluir solo aristas entre niveles consecutivos (frontera)
        edge_count = 0
        for u, v, data in self.G_full.edges(data=True):
            lu = levels.get(u, None)
            lv = levels.get(v, None)
            if lu is None or lv is None:
                continue
            if max(lu, lv) <= int(max_hops) and abs(lu - lv) == 1:
                Gf.add_edge(u, v, **data)
                edge_count += 1
        self._logger.info("frontier_only result | nodes=%s edges=%s", Gf.number_of_nodes(), edge_count)
        return Gf

    def build_focused_graph(
        self,
        risk_threshold: float = 0.7,
        max_clients: int = 10,
        max_hops: int = 2,
        filters: Optional[Dict[str, Any]] = None,
        client_id: Optional[str] = None,
    ) -> nx.DiGraph:
        if client_id is not None:
            if client_id not in self.G_full:
                self._logger.warning("client not in graph | client=%s", client_id)
                return nx.DiGraph()
            # MODO FRONTIER-ONLY para cliente directo
            G_focused = self._build_frontier_only(client_id, max_hops)
            self._logger.info("focused graph built | client=%s nodes=%s edges=%s", client_id, G_focused.number_of_nodes(), G_focused.number_of_edges())
            return G_focused
        else:
            high_risk_clients = [n for n, r in self._node_risk_scores.items() if float(r) >= float(risk_threshold)]
            high_risk_clients.sort(key=lambda n: self._node_risk_scores[n], reverse=True)
            high_risk_clients = high_risk_clients[: max(1, int(max_clients))]
            if not high_risk_clients:
                return nx.DiGraph()

            nodes_to_include: Set[str] = set(high_risk_clients)
            frontier: Set[str] = set(high_risk_clients)
            for _ in range(max(0, int(max_hops))):
                next_frontier: Set[str] = set()
                for n in frontier:
                    next_frontier.update(self.G_full.successors(n))
                    next_frontier.update(self.G_full.predecessors(n))
                nodes_to_include.update(next_frontier)
                frontier = next_frontier
                if not frontier:
                    break

        G_focused = nx.DiGraph()
        for n in nodes_to_include:
            if n in self.G_full:
                G_focused.add_node(n, **self.G_full.nodes[n])
        for u, v, data in self.G_full.edges(data=True):
            if u in nodes_to_include and v in nodes_to_include:
                G_focused.add_edge(u, v, **data)
        return G_focused


# =========================================================================
# 3. FRAUD PATTERN DETECTOR
# =========================================================================

class FraudPatternDetector:
    """Detecta patrones específicos (structuring, ciclos, mulas, anomalías)."""

    def __init__(self, G: nx.DiGraph, df: pd.DataFrame):
        self.G = G
        self.df = df.copy()

    def detect_structuring(
        self, amount_threshold: float = 10000, time_window_hours: int = 72, min_transactions: int = 4
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        self.df["timestamp_dt"] = pd.to_datetime(self.df["timestamp"])  # robusto
        self.df.sort_values("timestamp_dt", inplace=True)
        for origin in self.df["origin_id"].unique():
            origin_txs = self.df[self.df["origin_id"] == origin]
            if len(origin_txs) < min_transactions:
                continue
            for i in range(len(origin_txs) - min_transactions + 1):
                window = origin_txs.iloc[i : i + min_transactions]
                span_h = (window["timestamp_dt"].max() - window["timestamp_dt"].min()).total_seconds() / 3600.0
                if span_h <= time_window_hours:
                    amts = window["amount"].astype(float).values
                    avg_amt = float(np.mean(amts))
                    std_amt = float(np.std(amts))
                    if avg_amt < amount_threshold and (std_amt < avg_amt * 0.2):
                        destinations = window["destination_id"].unique().tolist()
                        total_amount = float(np.sum(amts))
                        uniformity = 1 - (std_amt / avg_amt) if avg_amt > 0 else 0.0
                        pattern_strength = float(min(1.0, uniformity))
                        fraud_count = int(window.get("is_fraudulent", pd.Series([0] * len(window))).sum())
                        fraud_rate = float(fraud_count / max(1, len(window)))
                        risk_score = float(min(1.0, fraud_rate + pattern_strength * 0.5))
                        results.append(
                            {
                                "origin": origin,
                                "destinations": destinations,
                                "total_amount": total_amount,
                                "num_transactions": int(len(window)),
                                "time_window": f"{window['timestamp_dt'].min()} to {window['timestamp_dt'].max()}",
                                "risk_score": risk_score,
                                "pattern_strength": pattern_strength,
                            }
                        )
        results.sort(key=lambda x: x["risk_score"], reverse=True)
        return results

    def detect_cycles(self, min_cycle_length: int = 3, max_cycle_length: int = 6) -> List[Tuple[List[str], float]]:
        cycles: List[Tuple[List[str], float]] = []
        try:
            for cycle in nx.simple_cycles(self.G, length_bound=max_cycle_length):  # cota ANTES de enumerar
                if len(cycle) >= min_cycle_length:
                    edge_risks: List[float] = []
                    for i, node in enumerate(cycle):
                        nxt = cycle[(i + 1) % len(cycle)]
                        if self.G.has_edge(node, nxt):
                            edge_risks.append(float(self.G[node][nxt].get("avg_risk_score", 0.0)))
                    avg_risk = float(np.mean(edge_risks)) if edge_risks else 0.0
                    cycles.append((list(cycle), avg_risk))
        except Exception:
            pass
        cycles.sort(key=lambda x: x[1], reverse=True)
        return cycles

    def detect_mule_accounts(self, min_degree: int = 10) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for node in self.G.nodes():
            deg_in = int(self.G.in_degree(node))
            deg_out = int(self.G.out_degree(node))
            total_deg = deg_in + deg_out
            if total_deg >= min_degree:
                total_vol = 0.0
                num_txs = 0
                for _, _, d in self.G.in_edges(node, data=True):
                    total_vol += float(d.get("weight", 0.0))
                    num_txs += int(d.get("num_transactions", 0))
                for _, _, d in self.G.out_edges(node, data=True):
                    total_vol += float(d.get("weight", 0.0))
                    num_txs += int(d.get("num_transactions", 0))
                degree_risk = min(1.0, total_deg / 50.0)
                volume_risk = min(1.0, total_vol / 1_000_000.0)
                risk_score = float((degree_risk + volume_risk) / 2.0)
                avg_tx = float(total_vol / num_txs) if num_txs > 0 else 0.0
                results.append(
                    {
                        "mule_id": node,
                        "degree_in": deg_in,
                        "degree_out": deg_out,
                        "total_degree": total_deg,
                        "total_volume": float(total_vol),
                        "num_transactions": int(num_txs),
                        "avg_transaction": avg_tx,
                        "risk_score": risk_score,
                    }
                )
        results.sort(key=lambda x: x["risk_score"], reverse=True)
        return results

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if "account_created_at" not in self.df.columns:
            return results
        self.df["timestamp_dt"] = pd.to_datetime(self.df["timestamp"])  # robusto
        now = self.df["timestamp_dt"].max()
        all_clients = pd.unique(pd.concat([self.df["origin_id"], self.df["destination_id"]]))
        for client_id in all_clients:
            if client_id in self.df["origin_id"].values:
                first_row = self.df[self.df["origin_id"] == client_id].iloc[0]
                age_days = int((now - pd.to_datetime(first_row.get("account_created_at", now))).days)
                if age_days <= 7:
                    txs = int(len(self.df[self.df["origin_id"] == client_id]))
                    vol = float(self.df[self.df["origin_id"] == client_id]["amount"].sum())
                    if txs > 10 or vol > 100_000:
                        anomaly_score = float(min(1.0, (txs / 20.0) + (vol / 200_000.0)))
                        results.append(
                            {
                                "client_id": client_id,
                                "account_age_days": age_days,
                                "num_transactions": txs,
                                "total_volume": vol,
                                "anomaly_score": anomaly_score,
                            }
                        )
        results.sort(key=lambda x: x["anomaly_score"], reverse=True)
        return results
