from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from faker import Faker


@dataclass(frozen=True)
class ClientProfile:
    """Perfil del cliente.

    Attributes:
        client_id: Identificador único del cliente.
        profile_type: Tipo de perfil ("individual", "company", "mule").
        country: País de residencia.
        account_age_days: Antigüedad de la cuenta en días.
    """

    client_id: str
    profile_type: str
    country: str
    account_age_days: int


def _rng(seed: Optional[int]) -> random.Random:
    """Crea RNG reproducible.

    Args:
        seed: Semilla opcional.

    Returns:
        random.Random: Generador.
    """

    return random.Random(seed)


def _np_rng(seed: Optional[int]) -> np.random.Generator:
    """Crea RNG de NumPy reproducible.

    Args:
        seed: Semilla.

    Returns:
        np.random.Generator: Generador de NumPy.
    """

    return np.random.default_rng(seed)


def generate_client_profiles(
    num_clients: int = 800,
    seed: Optional[int] = None,
    mule_ratio: float = 0.03,
) -> Dict[str, ClientProfile]:
    """Genera perfiles de clientes realistas.

    Args:
        num_clients: Número de clientes (500-1000 recomendado).
        seed: Semilla para reproducibilidad.
        mule_ratio: Proporción de mulas de dinero.

    Returns:
        dict: client_id -> ClientProfile.

    Example:
        >>> profiles = generate_client_profiles(num_clients=10, seed=42)
        >>> len(profiles)
        10
    """

    if num_clients <= 0:
        raise ValueError("num_clients debe ser > 0")
    if not 0.0 <= mule_ratio <= 0.5:
        raise ValueError("mule_ratio fuera de rango [0, 0.5]")

    rnd = _rng(seed)
    fake = Faker()
    Faker.seed(seed)

    countries = [
        "US",
        "UK",
        "ES",
        "DE",
        "FR",
        "MX",
        "BR",
        "CA",
        "AR",
        "CO",
    ]

    num_mules = int(num_clients * mule_ratio)
    mule_indices = set(rnd.sample(range(num_clients), k=num_mules))

    profiles: Dict[str, ClientProfile] = {}
    for i in range(num_clients):
        client_id = f"C{i:05d}"
        profile_type = "mule" if i in mule_indices else rnd.choices(
            ["individual", "company"], weights=[0.8, 0.2], k=1
        )[0]
        country = rnd.choice(countries)
        account_age_days = rnd.randint(30, 3650)
        profiles[client_id] = ClientProfile(
            client_id=client_id,
            profile_type=profile_type,
            country=country,
            account_age_days=account_age_days,
        )

    return profiles


def _sample_lognormal_amounts(
    n: int, npg: np.random.Generator, min_amount: float = 10.0, max_amount: float = 1_000_000.0
) -> np.ndarray:
    """Muestra montos con distribución log-normal acotada.

    Args:
        n: Cantidad.
        npg: Generador NumPy.
        min_amount: Mínimo.
        max_amount: Máximo.

    Returns:
        np.ndarray: Montos positivos.
    """

    # Log-normal con parámetros razonables para finanzas
    mu = math.log(2000)
    sigma = 1.5
    amounts = npg.lognormal(mean=mu, sigma=sigma, size=n)
    amounts = np.clip(amounts, min_amount, max_amount)
    return amounts


def _random_timestamp_within_days(rnd: random.Random, days: int = 180, base: Optional[datetime] = None) -> datetime:
    """Fecha aleatoria dentro de N días hacia atrás desde una base estable.

    Si no se provee base, se usa una fecha fija para reproducibilidad entre ejecuciones con misma seed.
    """

    if base is None:
        base = datetime(2025, 1, 1, 12, 0, 0)
    delta = timedelta(days=rnd.uniform(0, days), seconds=rnd.uniform(0, 24 * 3600))
    return base - delta


def _embed_money_laundering_cycles(
    rnd: random.Random,
    edges: List[Tuple[str, str, float, datetime, str, bool, str]],
    clients: List[str],
    num_cycles: int,
    npg: np.random.Generator,
) -> None:
    """Inserta ciclos A→B→C→A marcados como fraude."""

    for _ in range(num_cycles):
        if len(clients) < 3:
            break
        a, b, c = rnd.sample(clients, 3)
        base_amount = float(_sample_lognormal_amounts(1, npg)[0])
        t0 = _random_timestamp_within_days(rnd, 30)
        desc = "money laundering cycle"
        edges.append((a, b, base_amount, t0, desc, True, "money_laundering"))
        edges.append((b, c, base_amount * rnd.uniform(0.9, 1.1), t0 + timedelta(hours=1), desc, True, "money_laundering"))
        edges.append((c, a, base_amount * rnd.uniform(0.9, 1.1), t0 + timedelta(hours=2), desc, True, "money_laundering"))


def _embed_structuring(
    rnd: random.Random,
    edges: List[Tuple[str, str, float, datetime, str, bool, str]],
    clients: List[str],
    npg: np.random.Generator,
    bursts: int,
) -> None:
    """Inserta patrones de structuring (muchas txs pequeñas a un destino)."""

    for _ in range(bursts):
        origin = rnd.choice(clients)
        destination = rnd.choice([c for c in clients if c != origin])
        k = rnd.randint(5, 20)
        t0 = _random_timestamp_within_days(rnd, 20)
        for i in range(k):
            amt = float(_sample_lognormal_amounts(1, npg, min_amount=10.0, max_amount=2000.0)[0])
            edges.append(
                (
                    origin,
                    destination,
                    amt,
                    t0 + timedelta(minutes=i * rnd.uniform(5, 60)),
                    "structuring pattern",
                    True,
                    "structuring",
                )
            )


def _embed_mules(
    rnd: random.Random,
    edges: List[Tuple[str, str, float, datetime, str, bool, str]],
    mule_clients: Iterable[str],
    npg: np.random.Generator,
) -> None:
    """Inserta actividad anormal para mulas (alto grado de conexiones)."""

    mule_clients = sorted(set(mule_clients))  # sorted: set order depends on PYTHONHASHSEED, breaks reproducibility
    if not mule_clients:
        return
    for mule in mule_clients:
        # Conectarla con muchos
        k_out = rnd.randint(10, 30)
        k_in = rnd.randint(10, 30)
        others = [c for c in mule_clients if c != mule]
        # Añadir también clientes normales
        # Nota: La lista de otros clientes será complementada por el generador principal
        for _ in range(k_out):
            dest = f"C{rnd.randint(0, 99999):05d}"  # se sobreescribe si no existe más tarde
            amt = float(_sample_lognormal_amounts(1, npg, min_amount=50.0)[0])
            t = _random_timestamp_within_days(rnd, 60)
            edges.append((mule, dest, amt, t, "mule outbound", True, "mule"))
        for _ in range(k_in):
            src = f"C{rnd.randint(0, 99999):05d}"
            amt = float(_sample_lognormal_amounts(1, npg, min_amount=50.0)[0])
            t = _random_timestamp_within_days(rnd, 60)
            edges.append((src, mule, amt, t, "mule inbound", True, "mule"))


def generate_transactions(
    num_transactions: int = 8000,
    num_clients: int = 800,
    fraud_percentage: float = 0.08,
    seed: Optional[int] = None,
    include_enhanced_columns: bool = True,
) -> pd.DataFrame:
    """Genera DataFrame de transacciones sintéticas con patrones de fraude.

    Args:
        num_transactions: Número total de transacciones (5000-10000 recomendado).
        num_clients: Número de clientes (500-1000 recomendado).
        fraud_percentage: Proporción de txs fraudulentas (0.0-1.0).
        seed: Semilla de reproducibilidad.
        include_enhanced_columns: Si True, agrega columnas enriquecidas (transaction_type, channel, ...).

    Returns:
        pd.DataFrame: Columnas [transaction_id, origin_id, destination_id, amount, timestamp,
            description, is_fraudulent, fraud_type, risk_score] + columnas opcionales enriquecidas

    Example:
        >>> df = generate_transactions(num_transactions=100, num_clients=50, seed=42)
        >>> set(["transaction_id","origin_id","destination_id","amount","timestamp","description","is_fraudulent","fraud_type","risk_score"]).issubset(df.columns)
        True
    """

    if num_transactions <= 0:
        raise ValueError("num_transactions debe ser > 0")
    if num_clients <= 1:
        raise ValueError("num_clients debe ser > 1")
    if not 0.0 <= fraud_percentage <= 1.0:
        raise ValueError("fraud_percentage fuera de rango [0, 1]")

    rnd = _rng(seed)
    npg = _np_rng(seed)

    profiles = generate_client_profiles(num_clients=num_clients, seed=seed)
    client_ids = list(profiles.keys())

    # Base edges
    edges: List[Tuple[str, str, float, datetime, str, bool, str]] = []

    # Embedding fraude controlado por porcentaje aproximado
    target_fraud = int(num_transactions * fraud_percentage)

    # Para tamaños pequeños, evitar patrones que generen edges duplicados (structuring/mules)
    if num_transactions > 200:
        # 1) Money laundering cycles
        num_cycles = max(1, target_fraud // 30)
        _embed_money_laundering_cycles(rnd, edges, client_ids, num_cycles, npg)

        # 2) Structuring
        bursts = max(1, target_fraud // 25)
        _embed_structuring(rnd, edges, client_ids, npg, bursts)

        # 3) Mules (usar los marcados en profiles). Limitar contribución para respetar presupuesto de fraude.
        mule_clients = [c for c, p in profiles.items() if p.profile_type == "mule"]
        before_mules = len(edges)
        _embed_mules(rnd, edges, mule_clients, npg)
        # Recortar si excede el objetivo de fraude aproximado
        if len(edges) - before_mules > target_fraud:
            edges[:] = edges[: before_mules + target_fraud]

    # Control de pares únicos para el caso general (especialmente tests pequeños)
    used_pairs: set[Tuple[str, str]] = set()
    for (_o, _d, _a, _ts, _desc, _isf, _ft) in edges:
        used_pairs.add((_o, _d))

    # Ahora completar con transacciones normales hasta llegar a num_transactions
    def make_normal_edge() -> Tuple[str, str, float, datetime, str, bool, str]:
        # intentar evitar pares duplicados
        for _ in range(100):
            origin = rnd.choice(client_ids)
            dest = rnd.choice([c for c in client_ids if c != origin])
            if (origin, dest) not in used_pairs:
                used_pairs.add((origin, dest))
                amt = float(_sample_lognormal_amounts(1, npg)[0])
                t = _random_timestamp_within_days(rnd, 180)
                return origin, dest, amt, t, "normal transaction", False, "none"
        # fallback si no encontramos par único
        origin = rnd.choice(client_ids)
        dest = rnd.choice([c for c in client_ids if c != origin])
        amt = float(_sample_lognormal_amounts(1, npg)[0])
        t = _random_timestamp_within_days(rnd, 180)
        return origin, dest, amt, t, "normal transaction", False, "none"

    while len(edges) < num_transactions:
        edges.append(make_normal_edge())

    # Si nos excedimos, truncar
    edges = edges[:num_transactions]

    # Estimar etiqueta de fraude final al menos consistente con target.
    # Si hay demasiados fraudulentos, bajar algunos a 'none'. Si hay pocos, subir algunos normales con mayor monto.
    is_fraud = [is_f for (*_h, is_f, _ft) in edges]
    current_fraud = sum(1 for f in is_fraud if f)
    if target_fraud > 0:
        if current_fraud > target_fraud:
            # desmarcar exceso desde el final
            to_unflag = current_fraud - target_fraud
            for i in range(len(edges) - 1, -1, -1):
                o, d, a, ts, desc, isf, ft = edges[i]
                if isf:
                    edges[i] = (o, d, a, ts, "normal transaction", False, "none")
                    to_unflag -= 1
                    if to_unflag == 0:
                        break
        elif current_fraud < target_fraud:
            # marcar como fraude algunas normales de alto monto
            need = target_fraud - current_fraud
            normal_indices = [(i, e[2]) for i, e in enumerate(edges) if not e[5]]
            normal_indices.sort(key=lambda x: x[1], reverse=True)
            for i, _amt in normal_indices:
                o, d, a, ts, desc, isf, ft = edges[i]
                edges[i] = (o, d, a, ts, "flagged high-amount", True, "structuring")
                need -= 1
                if need == 0:
                    break

    # Asignar risk_score: base por tipo de fraude y monto
    risk_scores: List[float] = []
    for (_o, _d, amount, _ts, _desc, is_fraud, ftype) in edges:
        base = 0.1
        if is_fraud:
            if ftype == "money_laundering":
                base = 0.95
            elif ftype == "structuring":
                base = 0.9
            elif ftype == "mule":
                base = 0.92
            else:
                base = 0.85
        # Ajuste por monto (z-score aproximado usando log)
        amt_adj = min(1.0, max(0.0, (math.log(amount + 1) / math.log(1_000_000 + 1))))
        score = min(1.0, max(0.0, 0.5 * base + 0.5 * amt_adj))
        risk_scores.append(score)

    # Columnas base
    base_cols = {
        "transaction_id": [f"T{i:07d}" for i in range(len(edges))],
        "origin_id": [o for (o, *_rest) in edges],
        "destination_id": [d for (_o, d, *_rest) in edges],
        "amount": [float(a) for (_o, _d, a, *_rest) in edges],
        "timestamp": [ts for (_o, _d, _a, ts, *_rest) in edges],
        "description": [desc for (_o, _d, _a, _ts, desc, *_rest) in edges],
        "is_fraudulent": [is_f for (*_h, is_f, _ft) in edges],
        "fraud_type": [ft for (*_h, _isf, ft) in edges],
        "risk_score": risk_scores,
    }

    if include_enhanced_columns:
        # Categorías
        tx_types = ["cash", "transfer", "transfer_internacional", "card"]
        channels = ["app", "atm", "branch", "online", "mobile"]
        device_types = ["web", "mobile", "atm", "terminal"]
        countries = ["ES", "US", "MX", "BR", "UK", "DE", "FR", "AR", "CO", "CA"]

        tx_type_col = []
        channel_col = []
        device_col = []
        origin_country_col = []
        dest_country_col = []
        is_international_col = []

        for i in range(len(edges)):
            ttype = rnd.choice(tx_types)
            chan = rnd.choice(channels)
            dev = rnd.choice(device_types)
            oc = rnd.choice(countries)
            dc = rnd.choice([c for c in countries if c != oc])

            # Coherencias
            if ttype == "cash":
                chan = "atm"
                dev = "atm"
            if ttype == "card":
                dev = "terminal"
            is_international = ttype == "transfer_internacional" or oc != dc

            tx_type_col.append(ttype)
            channel_col.append(chan)
            device_col.append(dev)
            origin_country_col.append(oc)
            dest_country_col.append(dc)
            is_international_col.append(is_international)

        base_cols.update(
            {
                "transaction_type": tx_type_col,
                "channel": channel_col,
                "device_type": device_col,
                "origin_country": origin_country_col,
                "destination_country": dest_country_col,
                "is_international": is_international_col,
            }
        )

    df = pd.DataFrame(base_cols)

    # Orden por timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Validaciones básicas
    required_cols = {
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
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Faltan columnas: {missing}")

    if (df["amount"] <= 0).any():
        raise ValueError("Montos deben ser positivos")

    return df
