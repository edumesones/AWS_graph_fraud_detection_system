from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Optional

import networkx as nx
import pandas as pd


def build_graph_from_transactions(
    df: pd.DataFrame, client_profiles: Optional[Dict[str, dict]] = None
) -> nx.DiGraph:
    """Construye un grafo dirigido ponderado desde un DataFrame de transacciones.

    Args:
        df: DataFrame con columnas requeridas: [transaction_id, origin_id, destination_id,
            amount, timestamp, description, is_fraudulent, fraud_type, risk_score].
        client_profiles: Diccionario opcional {client_id: {profile_type, country, account_age_days}}.

    Returns:
        nx.DiGraph: Grafo con atributos en nodos y edges.

    Raises:
        KeyError: Si faltan columnas requeridas.
        ValueError: Si hay NaNs o montos no positivos.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     'transaction_id': ['T1'],
        ...     'origin_id': ['C001'],
        ...     'destination_id': ['C002'],
        ...     'amount': [100.0],
        ...     'timestamp': pd.to_datetime(['2024-01-01']),
        ...     'description': ['test'],
        ...     'is_fraudulent': [False],
        ...     'fraud_type': ['none'],
        ...     'risk_score': [0.1],
        ... })
        >>> G = build_graph_from_transactions(df)
        >>> isinstance(G, nx.DiGraph)
        True
    """

    required = {
        "transaction_id",
        "origin_id",
        "destination_id",
        "amount",
        "timestamp",
        "description",
        "is_fraudulent",
        "fraud_type",
        "risk_score",
    }
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Faltan columnas requeridas: {missing}")

    # Pandas no admite indexar con set; convertir a lista
    req_list = list(required)
    if df[req_list].isnull().any().any():
        raise ValueError("DataFrame contiene NaNs en columnas requeridas")

    if (df["amount"] <= 0).any():
        raise ValueError("Todas las transacciones deben tener monto positivo")

    # Pre-cálculos para atributos de nodos
    origin_counts = Counter(df["origin_id"].tolist())
    dest_counts = Counter(df["destination_id"].tolist())
    node_counts: Dict[str, int] = defaultdict(int)
    for k, v in origin_counts.items():
        node_counts[k] += v
    for k, v in dest_counts.items():
        node_counts[k] += v

    total_volume: Dict[str, float] = defaultdict(float)
    for row in df.itertuples(index=False):
        total_volume[row.origin_id] += float(row.amount)
        total_volume[row.destination_id] += float(row.amount)

    G = nx.DiGraph()

    # Añadir edges con atributos
    for row in df.itertuples(index=False):
        o = str(row.origin_id)
        d = str(row.destination_id)
        if o == d:
            # Permitir self-loops? Para AML se pueden permitir, pero aquí evitamos ruido.
            pass
        G.add_edge(
            o,
            d,
            transaction_id=str(row.transaction_id),
            amount=float(row.amount),
            timestamp=pd.to_datetime(row.timestamp),
            description=str(row.description),
            is_fraudulent=bool(row.is_fraudulent),
            fraud_type=str(row.fraud_type),
            risk_score=float(row.risk_score),
        )

    # Atributos de nodos
    profiles = client_profiles or {}
    for node in G.nodes():
        p = profiles.get(node, {})
        profile_type = str(p.get("profile_type", "unknown"))
        country = str(p.get("country", "NA"))
        account_age_days = int(p.get("account_age_days", 0))
        G.nodes[node]["profile_type"] = profile_type
        G.nodes[node]["country"] = country
        G.nodes[node]["account_age_days"] = account_age_days
        G.nodes[node]["num_transactions"] = int(node_counts.get(node, 0))
        G.nodes[node]["total_volume"] = float(total_volume.get(node, 0.0))

    return G
