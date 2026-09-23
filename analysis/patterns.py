from __future__ import annotations

from typing import List, Tuple

import networkx as nx
import pandas as pd


def detect_money_laundering_cycles(G: nx.DiGraph, max_cycle_length: int = 4) -> List[List[str]]:
    """Detecta ciclos A→B→C→A hasta longitud máxima.

    Args:
        G: Grafo dirigido.
        max_cycle_length: Longitud máxima del ciclo (>=3).

    Returns:
        list[list[str]]: Lista de ciclos (listas de nodos en orden).
    """

    if max_cycle_length < 3:
        raise ValueError("max_cycle_length debe ser >= 3")

    cycles: List[List[str]] = []
    for cycle in nx.simple_cycles(G, length_bound=max_cycle_length):  # cota ANTES de enumerar: sin ella no termina a escala real
        if 3 <= len(cycle) <= max_cycle_length:
            cycles.append([str(n) for n in cycle])
    return cycles


def detect_structuring(
    df: pd.DataFrame, window_days: int = 30, threshold_count: int = 10
) -> pd.DataFrame:
    """Detecta múltiples transacciones pequeñas a un mismo destino en ventana temporal.

    Args:
        df: DataFrame de transacciones.
        window_days: Ventana en días.
        threshold_count: Conteo mínimo para marcar.

    Returns:
        pd.DataFrame: Registros agregados por (origin_id, destination_id) sospechosos.
    """

    dff = df.copy()
    dff = dff.sort_values("timestamp")
    dff["date"] = pd.to_datetime(dff["timestamp"]).dt.date
    grouped = (
        dff.groupby(["origin_id", "destination_id"])  # noqa: PD013
        .agg(count=("transaction_id", "count"), total_amount=("amount", "sum"))
        .reset_index()
    )
    suspicious = grouped[grouped["count"] >= threshold_count].copy()
    return suspicious


def detect_mules(G: nx.DiGraph, imbalance_threshold: float = 0.7) -> List[str]:
    """Detecta clientes con desbalance fuerte entre in/out degree.

    Args:
        G: Grafo.
        imbalance_threshold: |in-out|/(in+out) mínimo.

    Returns:
        list[str]: Nodos sospechosos.
    """

    suspects: List[str] = []
    for n in G.nodes():
        in_d = float(G.in_degree(n))
        out_d = float(G.out_degree(n))
        total = in_d + out_d
        if total == 0:
            continue
        imbalance = abs(in_d - out_d) / total
        if imbalance >= imbalance_threshold and total >= 5:
            suspects.append(str(n))
    return suspects


def detect_rapid_cycling(G: nx.DiGraph, max_hours: float = 4.0) -> List[Tuple[str, str]]:
    """Detecta pares de nodos con transacciones de ida y vuelta muy rápidas."""

    suspects: List[Tuple[str, str]] = []
    for u, v, data in G.edges(data=True):
        rev = G.get_edge_data(v, u, default=None)
        if rev is None:
            continue
        t1 = pd.to_datetime(data.get("timestamp"))
        t2 = pd.to_datetime(rev.get("timestamp"))
        if pd.notna(t1) and pd.notna(t2):
            delta_h = abs((t2 - t1).total_seconds()) / 3600.0
            if delta_h <= max_hours:
                suspects.append((str(u), str(v)))
    return suspects
