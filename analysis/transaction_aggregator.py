from __future__ import annotations

from collections import defaultdict
from typing import Dict, Tuple, Any

import pandas as pd


class TransactionAggregator:
    """Agrupa transacciones por par (origin_id, destination_id) y calcula métricas.

    Retorna un diccionario:
        {
            (origin, destination): {
                'num_transactions': int,
                'total_amount': float,
                'average_amount': float,
                'min_amount': float,
                'max_amount': float,
                'first_transaction': Timestamp,
                'last_transaction': Timestamp,
                'transaction_types': Dict[str, Dict],
                'channels': Dict[str, Dict],
                'is_international': bool,
                'num_fraudulent': int,
                'fraud_rate': float,
                'countries_path': List[str],  # opcional
                'avg_risk_score': float,
            }
        }
    """

    def aggregate(self, df: pd.DataFrame) -> Dict[Tuple[str, str], Dict[str, Any]]:
        required = {"origin_id", "destination_id", "amount", "timestamp", "is_fraudulent", "risk_score"}
        missing = required - set(df.columns)
        if missing:
            raise KeyError(f"Faltan columnas requeridas para agregación: {missing}")

        # Preparación
        dff = df.copy()
        dff["timestamp"] = pd.to_datetime(dff["timestamp"], errors="coerce")

        result: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for (o, d), group in dff.groupby(["origin_id", "destination_id"], dropna=False):
            g = group
            total_amount = float(pd.to_numeric(g["amount"], errors="coerce").sum())
            num_transactions = int(len(g))
            avg_amount = float(total_amount / max(1, num_transactions))
            min_amount = float(pd.to_numeric(g["amount"], errors="coerce").min())
            max_amount = float(pd.to_numeric(g["amount"], errors="coerce").max())
            first_ts = pd.to_datetime(g["timestamp"]).min()
            last_ts = pd.to_datetime(g["timestamp"]).max()

            # Breakdown por tipo y canal si existen
            tx_types: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0, "amount": 0.0})
            if "transaction_type" in g.columns:
                for ttype, sub in g.groupby("transaction_type"):
                    tx_types[str(ttype)]["count"] = int(len(sub))
                    tx_types[str(ttype)]["amount"] = float(pd.to_numeric(sub["amount"], errors="coerce").sum())

            channels: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0, "amount": 0.0})
            if "channel" in g.columns:
                for ch, sub in g.groupby("channel"):
                    channels[str(ch)]["count"] = int(len(sub))
                    channels[str(ch)]["amount"] = float(pd.to_numeric(sub["amount"], errors="coerce").sum())

            # Métricas de fraude
            num_fraud = int(pd.to_numeric(g["is_fraudulent"]).sum())
            fraud_rate = float(num_fraud / max(1, num_transactions))

            # Internacional
            is_int = False
            if "is_international" in g.columns:
                is_int = bool(pd.to_numeric(g["is_international"], errors="coerce").astype(bool).any())

            avg_risk = float(pd.to_numeric(g["risk_score"], errors="coerce").mean())

            result[(str(o), str(d))] = {
                "num_transactions": num_transactions,
                "total_amount": total_amount,
                "average_amount": avg_amount,
                "min_amount": min_amount,
                "max_amount": max_amount,
                "first_transaction": first_ts,
                "last_transaction": last_ts,
                "transaction_types": dict(tx_types),
                "channels": dict(channels),
                "is_international": is_int,
                "num_fraudulent": num_fraud,
                "fraud_rate": fraud_rate,
                "countries_path": self._countries_path(g),
                "avg_risk_score": avg_risk,
            }

        return result

    @staticmethod
    def _countries_path(g: pd.DataFrame) -> list:
        # Heurística simple: origen → destino si existen columnas
        oc = g["origin_country"].iloc[0] if "origin_country" in g.columns and not g["origin_country"].empty else None
        dc = (
            g["destination_country"].iloc[0]
            if "destination_country" in g.columns and not g["destination_country"].empty
            else None
        )
        if oc and dc:
            return [f"{oc}→{dc}"]
        return []
