from __future__ import annotations

from typing import Iterable, List

import pandas as pd

REQUIRED_TX_COLUMNS = {
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

REQUIRED_PROFILE_COLUMNS = {
    "client_id",
    "profile_type",
    "country",
    "account_age_days",
}


def _validate_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    missing = set(required) - set(df.columns)
    if missing:
        raise KeyError(f"Faltan columnas requeridas: {missing}")


def load_transactions_from_csv(path: str) -> pd.DataFrame:
    """Carga CSV de transacciones y valida columnas.

    Args:
        path: Ruta al archivo CSV.

    Returns:
        pd.DataFrame: DataFrame validado.
    """

    df = pd.read_csv(path, parse_dates=["timestamp"], infer_datetime_format=True)
    _validate_columns(df, REQUIRED_TX_COLUMNS)
    if (df["amount"] <= 0).any():
        raise ValueError("Montos deben ser positivos")
    return df


def load_client_profiles_from_csv(path: str) -> pd.DataFrame:
    """Carga CSV de perfiles de clientes y valida columnas."""

    df = pd.read_csv(path)
    _validate_columns(df, REQUIRED_PROFILE_COLUMNS)
    return df
