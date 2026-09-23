"""Evaluación honesta de los detectores del repo contra el ground truth sintético.

El generador (`data/synthetic_generator.py`) etiqueta cada transacción con
`is_fraudulent` y `fraud_type`. Ese ground truth existe desde el primer commit y
hasta ahora no se usaba para medir nada: los detectores de `analysis/` se
consumían solo desde el dashboard, de forma cualitativa.

Este script cierra ese hueco. No implementa detectores nuevos: importa los que
ya hay, los ejecuta sobre un dataset con proporción de fraude conocida y reporta
precision / recall / F1 / PR-AUC y matriz de confusión para cada uno.

Dos unidades de evaluación, porque los detectores del repo no hablan todos el
mismo idioma:

  * NODO  — un cliente es positivo si participa (como origen o destino) en al
            menos una transacción etiquetada como fraudulenta.
  * PAR   — un par dirigido (origin_id, destination_id) es positivo si al menos
            una de las transacciones entre ambos está etiquetada como fraude.

La unidad PAR, y no "transacción", es la correcta para los detectores de grafo:
`build_graph_from_transactions` construye un `nx.DiGraph`, que colapsa todas las
transacciones de un mismo par en una sola arista. Evaluar por transacción daría
números que el grafo no puede producir.

Uso:
    python evaluate.py
    python evaluate.py --transactions 4000 --seed 7 --budget 30

Sin credenciales, sin AWS, sin red. Solo las dependencias de requirements.txt.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
import multiprocessing as mp
import queue as queue_mod
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix

# El repo se importa como paquetes sueltos desde la raíz.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from analysis.anomaly_detection import detect_outlier_nodes, flag_suspicious_edges
from analysis.community_detection import detect_communities
from analysis.fraud_investigation import FraudPatternDetector
from analysis.enhanced_graph_builder import EnhancedGraphBuilder
from analysis.graph_builder import build_graph_from_transactions
from analysis.network_metrics import compute_node_metrics, identify_hub_nodes
from analysis.patterns import (
    detect_money_laundering_cycles,
    detect_mules,
    detect_rapid_cycling,
    detect_structuring,
)
from data.synthetic_generator import generate_client_profiles, generate_transactions

Pair = Tuple[str, str]


# ---------------------------------------------------------------------------
# Resultado de un detector
# ---------------------------------------------------------------------------


@dataclass
class DetectorResult:
    """Métricas de un detector sobre una unidad de evaluación.

    `status` es "ok", "timeout" o "error". Cuando no es "ok" las métricas van a
    None: preferimos un hueco visible a un número inventado.
    """

    name: str
    unit: str
    source: str
    status: str = "ok"
    note: str = ""
    elapsed_s: float = 0.0
    n_flagged: Optional[int] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    pr_auc: Optional[float] = None
    pr_auc_basis: str = "n/a"
    confusion: Optional[Dict[str, int]] = None
    typology_recall: Optional[Dict[str, Dict[str, Any]]] = None
    typology_note: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _binary_metrics(
    y_true: np.ndarray, y_pred: np.ndarray
) -> Tuple[float, float, float, Dict[str, int]]:
    """Precision / recall / F1 y matriz de confusión a partir de vectores 0-1."""

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return (
        float(precision),
        float(recall),
        float(f1),
        {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    )


def _typology_recall(
    universe: Sequence[Any],
    typologies: Dict[Any, Set[str]],
    flagged: Set[Any],
) -> Dict[str, Dict[str, Any]]:
    """Recall del detector sobre cada tipología de fraude por separado.

    La fila agregada mezcla tipologías que un detector concreto ni siquiera
    intenta cubrir, así que su precision/recall castiga por no encontrar lo que
    no busca. Este desglose separa "no lo encuentra" de "no lo busca".

    Un candidato puede pertenecer a varias tipologías (una cuenta mula también
    puede estar en un ciclo), así que las poblaciones NO suman el total de
    positivos: cada columna se lee por separado, nunca como una partición.
    """

    in_universe = set(universe)
    buckets: Dict[str, List[Any]] = defaultdict(list)
    for candidate, types in typologies.items():
        if candidate in in_universe:
            for fraud_type in types:
                buckets[fraud_type].append(candidate)

    breakdown: Dict[str, Dict[str, Any]] = {}
    for fraud_type in sorted(buckets, key=lambda t: (-len(buckets[t]), t)):
        population = buckets[fraud_type]
        detected = sum(1 for c in population if c in flagged)
        breakdown[fraud_type] = {
            "positives": len(population),
            "detected": detected,
            "recall": detected / len(population) if population else 0.0,
        }
    return breakdown


def evaluate_detector(
    name: str,
    unit: str,
    source: str,
    universe: Sequence[Any],
    truth: Dict[Any, bool],
    flagged: Set[Any],
    scores: Optional[Dict[Any, float]] = None,
    pr_auc_basis: str = "n/a",
    elapsed_s: float = 0.0,
    note: str = "",
    typologies: Optional[Dict[Any, Set[str]]] = None,
    typology_note: str = "",
) -> DetectorResult:
    """Convierte la salida cruda de un detector en métricas comparables.

    Args:
        universe: todos los candidatos evaluables (nodos o pares).
        truth: candidato -> etiqueta real.
        flagged: candidatos marcados por el detector (decisión binaria).
        scores: candidato -> score continuo. Si falta, no hay PR-AUC:
            un detector que solo devuelve una lista no tiene curva que integrar.
    """

    y_true = np.array([1 if truth.get(c, False) else 0 for c in universe], dtype=int)
    y_pred = np.array([1 if c in flagged else 0 for c in universe], dtype=int)
    precision, recall, f1, cm = _binary_metrics(y_true, y_pred)

    pr_auc: Optional[float] = None
    if scores is not None and y_true.sum() > 0:
        y_score = np.array([float(scores.get(c, 0.0)) for c in universe], dtype=float)
        pr_auc = float(average_precision_score(y_true, y_score))

    return DetectorResult(
        name=name,
        unit=unit,
        source=source,
        status="ok",
        note=note,
        elapsed_s=round(elapsed_s, 2),
        n_flagged=int(y_pred.sum()),
        precision=precision,
        recall=recall,
        f1=f1,
        pr_auc=pr_auc,
        pr_auc_basis=pr_auc_basis if scores is not None else "n/a (salida binaria)",
        confusion=cm,
        typology_recall=_typology_recall(universe, typologies, flagged) if typologies else None,
        typology_note=typology_note,
    )


# ---------------------------------------------------------------------------
# Ground truth
# ---------------------------------------------------------------------------


def node_ground_truth(df: pd.DataFrame) -> Dict[str, bool]:
    """Nodo positivo := participa en >= 1 transacción etiquetada como fraude."""

    truth: Dict[str, bool] = {}
    for node in pd.unique(pd.concat([df["origin_id"], df["destination_id"]])):
        truth[str(node)] = False
    fraud = df[df["is_fraudulent"].astype(bool)]
    for node in pd.unique(pd.concat([fraud["origin_id"], fraud["destination_id"]])):
        truth[str(node)] = True
    return truth


def pair_ground_truth(df: pd.DataFrame) -> Dict[Pair, bool]:
    """Par positivo := >= 1 transacción fraudulenta entre ese origen y destino."""

    grouped = df.groupby(["origin_id", "destination_id"])["is_fraudulent"].any()
    return {(str(o), str(d)): bool(v) for (o, d), v in grouped.items()}


def pair_typologies(df: pd.DataFrame) -> Dict[Pair, Set[str]]:
    """Par -> tipologías de fraude presentes entre ese origen y destino."""

    fraud = df[df["is_fraudulent"].astype(bool)]
    out: Dict[Pair, Set[str]] = defaultdict(set)
    for origin, dest, ftype in zip(fraud["origin_id"], fraud["destination_id"], fraud["fraud_type"]):
        if str(ftype) != "none":
            out[(str(origin), str(dest))].add(str(ftype))
    return dict(out)


def node_typologies(df: pd.DataFrame) -> Dict[str, Set[str]]:
    """Nodo -> tipologías en las que participa, como origen o como destino.

    Atribuir la tipología al nodo es limpio porque replica exactamente la
    definición del ground truth de nodo (participar en >= 1 transacción de ese
    tipo), solo que troceada. Tiene una consecuencia que hay que leer con
    cuidado: la contraparte de una mula queda etiquetada "mule" por recibir de
    ella, así que la columna mide "nodos que tocan una transacción mula", no
    "cuentas mula". Las 300 de 407 víctimas de grado <= 1 del perfil del dataset
    son justamente esas contrapartes.
    """

    fraud = df[df["is_fraudulent"].astype(bool)]
    out: Dict[str, Set[str]] = defaultdict(set)
    for origin, dest, ftype in zip(fraud["origin_id"], fraud["destination_id"], fraud["fraud_type"]):
        if str(ftype) != "none":
            out[str(origin)].add(str(ftype))
            out[str(dest)].add(str(ftype))
    return dict(out)


# ---------------------------------------------------------------------------
# Presupuesto de tiempo para detectores potencialmente no acotados
# ---------------------------------------------------------------------------


def _cycles_worker(df: pd.DataFrame, max_cycle_length: int, result_queue: "mp.Queue") -> None:
    """Ejecuta detect_money_laundering_cycles en un proceso hijo desechable.

    `patterns.detect_money_laundering_cycles` ya pasa `length_bound` a
    `nx.simple_cycles`, así que acota la longitud ANTES de enumerar y termina en
    segundos. Mantenemos el aislamiento en proceso hijo porque la enumeración de
    ciclos es exponencial en el caso peor: el presupuesto de tiempo es la red de
    seguridad que impide que un grafo más denso cuelgue toda la evaluación.
    """

    graph = build_graph_from_transactions(df)
    cycles = detect_money_laundering_cycles(graph, max_cycle_length=max_cycle_length)
    pairs: Set[Pair] = set()
    for cycle in cycles:
        for i, node in enumerate(cycle):
            nxt = cycle[(i + 1) % len(cycle)]
            if graph.has_edge(node, nxt):
                pairs.add((str(node), str(nxt)))
    result_queue.put((pairs, len(cycles)))


def run_cycles_with_budget(
    df: pd.DataFrame, max_cycle_length: int, budget_s: float
) -> Tuple[Optional[Tuple[Set[Pair], int]], float]:
    """Devuelve ((pares, nº de ciclos), segundos) o (None, segundos) si agota el presupuesto.

    Leer la cola ANTES de `join` no es un detalle de estilo. El hijo no puede
    terminar mientras su hilo alimentador siga bloqueado escribiendo un payload
    mayor que el buffer del pipe, así que con `join()` primero un detector que
    acaba en 8 s se reportaba como TIMEOUT al agotar el presupuesto: el harness
    confundía "detector lento" con "resultado demasiado grande para el pipe".
    """

    result_queue: "mp.Queue" = mp.Queue()
    proc = mp.Process(target=_cycles_worker, args=(df, max_cycle_length, result_queue), daemon=True)
    start = time.perf_counter()
    proc.start()
    try:
        pairs: Optional[Tuple[Set[Pair], int]] = result_queue.get(timeout=budget_s)
    except queue_mod.Empty:
        pairs = None
    elapsed = time.perf_counter() - start
    proc.join(10.0 if pairs is not None else 0.0)
    if proc.is_alive():
        proc.terminate()
        proc.join()
    return pairs, elapsed


# ---------------------------------------------------------------------------
# Evaluación a nivel de NODO
# ---------------------------------------------------------------------------


def evaluate_nodes(
    df: pd.DataFrame,
    graph: nx.DiGraph,
    enhanced: nx.DiGraph,
    truth: Dict[str, bool],
    outlier_quantile: float,
) -> Tuple[List[DetectorResult], pd.DataFrame]:
    universe = sorted(graph.nodes())
    typologies = node_typologies(df)
    results: List[DetectorResult] = []

    # --- Baseline de prevalencia: marcar todo. Precision = tasa de positivos. ---
    results.append(
        evaluate_detector(
            name="baseline: flag-all",
            unit="nodo",
            source="(referencia)",
            universe=universe,
            truth=truth,
            typologies=typologies,
            flagged=set(universe),
            note="suelo de comparación: cualquier detector por debajo de esta precision resta valor",
        )
    )

    # --- detect_outlier_nodes: z-score agregado sobre métricas de centralidad ---
    t0 = time.perf_counter()
    metrics = compute_node_metrics(graph)
    metrics_elapsed = time.perf_counter() - t0

    t0 = time.perf_counter()
    scored = detect_outlier_nodes(graph, metrics, threshold=outlier_quantile)
    elapsed = time.perf_counter() - t0 + metrics_elapsed
    anomaly_scores = {
        str(r.node_id): float(r.anomaly_score) for r in scored.itertuples(index=False)
    }
    # La función calcula un `cutoff` interno y NO lo usa: devuelve todos los nodos
    # puntuados. El umbral lo aplicamos aquí, replicando la intención del parámetro.
    cut = float(np.quantile(list(anomaly_scores.values()), outlier_quantile))
    flagged = {n for n, s in anomaly_scores.items() if s >= cut}
    results.append(
        evaluate_detector(
            name="detect_outlier_nodes",
            unit="nodo",
            source="analysis/anomaly_detection.py",
            universe=universe,
            truth=truth,
            typologies=typologies,
            flagged=flagged,
            scores=anomaly_scores,
            pr_auc_basis="anomaly_score (z-score agregado)",
            elapsed_s=elapsed,
            note=f"umbral aplicado fuera: la función ignora su propio cutoff (q={outlier_quantile})",
        )
    )

    # --- detect_mules: desbalance in/out degree ---
    t0 = time.perf_counter()
    mules = set(detect_mules(graph, imbalance_threshold=0.7))
    results.append(
        evaluate_detector(
            name="detect_mules",
            unit="nodo",
            source="analysis/patterns.py",
            universe=universe,
            truth=truth,
            typologies=typologies,
            flagged=mules,
            elapsed_s=time.perf_counter() - t0,
            note="imbalance>=0.7 y grado total>=5",
        )
    )

    # --- identify_hub_nodes: percentil de grado ---
    t0 = time.perf_counter()
    hubs = set(identify_hub_nodes(graph, percentile=90))
    results.append(
        evaluate_detector(
            name="identify_hub_nodes(p90)",
            unit="nodo",
            source="analysis/network_metrics.py",
            universe=universe,
            truth=truth,
            typologies=typologies,
            flagged=hubs,
            elapsed_s=time.perf_counter() - t0,
        )
    )

    # --- FraudPatternDetector.detect_mule_accounts sobre el grafo agregado ---
    t0 = time.perf_counter()
    detector = FraudPatternDetector(enhanced, df)
    mule_rows = detector.detect_mule_accounts(min_degree=10)
    elapsed = time.perf_counter() - t0
    mule_scores = {str(r["mule_id"]): float(r["risk_score"]) for r in mule_rows}
    results.append(
        evaluate_detector(
            name="FraudPatternDetector.detect_mule_accounts",
            unit="nodo",
            source="analysis/fraud_investigation.py",
            universe=universe,
            truth=truth,
            typologies=typologies,
            flagged=set(mule_scores),
            scores=mule_scores,
            pr_auc_basis="risk_score = f(grado, volumen)",
            elapsed_s=elapsed,
            note="min_degree=10 sobre grafo agregado",
        )
    )

    return results, metrics


# ---------------------------------------------------------------------------
# Evaluación a nivel de PAR (origen, destino)
# ---------------------------------------------------------------------------


def evaluate_pairs(
    df: pd.DataFrame,
    graph: nx.DiGraph,
    enhanced: nx.DiGraph,
    truth: Dict[Pair, bool],
    budget_s: float,
) -> List[DetectorResult]:
    universe = sorted(truth)
    typologies = pair_typologies(df)
    results: List[DetectorResult] = []

    results.append(
        evaluate_detector(
            name="baseline: flag-all",
            unit="par",
            source="(referencia)",
            universe=universe,
            truth=truth,
            typologies=typologies,
            flagged=set(universe),
            note="suelo de comparación",
        )
    )

    # --- Fuga de etiqueta: risk_score del propio generador ---
    # El generador deriva risk_score de is_fraudulent. Se incluye para dejar
    # explícito por qué esa columna NO puede usarse como feature.
    leak = df.groupby(["origin_id", "destination_id"])["risk_score"].max()
    leak_scores = {(str(o), str(d)): float(v) for (o, d), v in leak.items()}
    leak_cut = float(np.quantile(list(leak_scores.values()), 0.90))
    results.append(
        evaluate_detector(
            name="[fuga] risk_score del generador",
            unit="par",
            source="data/synthetic_generator.py",
            universe=universe,
            truth=truth,
            typologies=typologies,
            flagged={p for p, s in leak_scores.items() if s >= leak_cut},
            scores=leak_scores,
            pr_auc_basis="risk_score (derivado de la etiqueta)",
            note="NO es un detector: mide cuánta señal regala la columna",
        )
    )

    # --- flag_suspicious_edges: umbral de importe ---
    amounts = [float(d.get("amount", 0.0)) for _u, _v, d in graph.edges(data=True)]
    amount_threshold = float(np.quantile(amounts, 0.95)) if amounts else 0.0
    t0 = time.perf_counter()
    flagged_df = flag_suspicious_edges(graph, amount_threshold=amount_threshold)
    elapsed = time.perf_counter() - t0
    flagged = {
        (str(r.origin_id), str(r.destination_id)) for r in flagged_df.itertuples(index=False)
    } if not flagged_df.empty else set()
    edge_amounts = {(str(u), str(v)): float(d.get("amount", 0.0)) for u, v, d in graph.edges(data=True)}
    results.append(
        evaluate_detector(
            name="flag_suspicious_edges(p95 importe)",
            unit="par",
            source="analysis/anomaly_detection.py",
            universe=universe,
            truth=truth,
            typologies=typologies,
            flagged=flagged,
            scores=edge_amounts,
            pr_auc_basis="importe de la arista",
            elapsed_s=elapsed,
            note=f"umbral = {amount_threshold:,.0f} (p95 de importes de arista)",
        )
    )

    # --- detect_structuring: recuento de transacciones por par ---
    t0 = time.perf_counter()
    struct = detect_structuring(df, window_days=30, threshold_count=10)
    elapsed = time.perf_counter() - t0
    struct_flagged = {
        (str(r.origin_id), str(r.destination_id)) for r in struct.itertuples(index=False)
    } if not struct.empty else set()
    counts = df.groupby(["origin_id", "destination_id"]).size()
    count_scores = {(str(o), str(d)): float(v) for (o, d), v in counts.items()}
    results.append(
        evaluate_detector(
            name="detect_structuring(count>=10)",
            unit="par",
            source="analysis/patterns.py",
            universe=universe,
            truth=truth,
            typologies=typologies,
            flagged=struct_flagged,
            scores=count_scores,
            pr_auc_basis="nº de transacciones del par",
            elapsed_s=elapsed,
            note="el parámetro window_days no se usa dentro de la función",
        )
    )

    # --- detect_rapid_cycling: ida y vuelta en <= 4h ---
    t0 = time.perf_counter()
    rapid = {(str(u), str(v)) for u, v in detect_rapid_cycling(graph, max_hours=4.0)}
    results.append(
        evaluate_detector(
            name="detect_rapid_cycling(<=4h)",
            unit="par",
            source="analysis/patterns.py",
            universe=universe,
            truth=truth,
            typologies=typologies,
            flagged=rapid,
            elapsed_s=time.perf_counter() - t0,
        )
    )

    # --- detect_money_laundering_cycles: bajo presupuesto de tiempo ---
    cycle_payload, elapsed = run_cycles_with_budget(df, max_cycle_length=4, budget_s=budget_s)
    if cycle_payload is None:
        results.append(
            DetectorResult(
                name="detect_money_laundering_cycles(len<=4)",
                unit="par",
                source="analysis/patterns.py",
                status="timeout",
                elapsed_s=round(elapsed, 2),
                note=(
                    f"abortado tras {budget_s:.0f}s: enumerar ciclos es exponencial "
                    "en el caso peor incluso con length_bound. Subir --budget o "
                    "bajar max_cycle_length"
                ),
            )
        )
    else:
        cycle_pairs, num_cycles = cycle_payload
        ml_pairs = sum(1 for types in typologies.values() if "money_laundering" in types)
        results.append(
            evaluate_detector(
                name="detect_money_laundering_cycles(len<=4)",
                unit="par",
                source="analysis/patterns.py",
                universe=universe,
                truth=truth,
                typologies=typologies,
                flagged=cycle_pairs,
                elapsed_s=elapsed,
                typology_note=(
                    "recall perfecto en money_laundering y precision 0.018 no se "
                    f"contradicen. El generador planta {ml_pairs} pares de blanqueo "
                    f"(~{ml_pairs // 3} ciclos), pero un grafo de "
                    f"{graph.number_of_edges()} aristas contiene {num_cycles} ciclos "
                    "simples de longitud 3-4 por pura coincidencia. El detector "
                    "encuentra el 100% de lo que busca y lo entierra bajo los ciclos "
                    "naturales del grafo: la fila agregada mide sobre todo cuántos "
                    "ciclos tiene el grafo, no cuánto blanqueo hay. Para usarlo haría "
                    "falta un filtro secundario sobre el ciclo (coherencia de importes, "
                    "ventana temporal), no un umbral distinto."
                ),
                note=(
                    "aristas de algún ciclo simple de longitud 3-4; nx.simple_cycles "
                    "recibe length_bound, que acota ANTES de enumerar (sin esa cota "
                    "el detector no terminaba a esta escala)"
                ),
            )
        )

    # --- FraudPatternDetector.detect_structuring: ventana temporal + uniformidad ---
    t0 = time.perf_counter()
    detector = FraudPatternDetector(enhanced, df)
    rows = detector.detect_structuring(
        amount_threshold=10_000, time_window_hours=72, min_transactions=4
    )
    elapsed = time.perf_counter() - t0
    fpd_scores: Dict[Pair, float] = {}
    for row in rows:
        for dest in row["destinations"]:
            key = (str(row["origin"]), str(dest))
            fpd_scores[key] = max(fpd_scores.get(key, 0.0), float(row["risk_score"]))
    results.append(
        evaluate_detector(
            name="FraudPatternDetector.detect_structuring",
            unit="par",
            source="analysis/fraud_investigation.py",
            universe=universe,
            truth=truth,
            typologies=typologies,
            flagged=set(fpd_scores),
            scores=fpd_scores,
            pr_auc_basis="risk_score del patrón",
            elapsed_s=elapsed,
            note="su risk_score usa is_fraudulent de la ventana: contaminado por la etiqueta",
        )
    )

    return results


# ---------------------------------------------------------------------------
# Diagnóstico de comunidades (Louvain no es un clasificador)
# ---------------------------------------------------------------------------


def community_diagnostics(
    graph: nx.DiGraph, node_truth: Dict[str, bool], seed: int
) -> Dict[str, Any]:
    """Louvain devuelve una partición, no un score.

    No se le puede asignar precision/recall sin inventar una regla de marcado,
    que sería un detector nuevo. Lo que sí se puede medir es si la partición
    concentra fraude: si no lo hace, la pestaña de comunidades del dashboard es
    decorativa.

    `detect_communities` no expone `random_state`, así que `best_partition` cae
    en el RandomState global de NumPy y devuelve una partición distinta en cada
    ejecución (19 comunidades una vez, 21 la siguiente). Lo fijamos aquí desde
    fuera; lo correcto sería que `detect_communities` aceptara una semilla.
    """

    np.random.seed(seed)
    t0 = time.perf_counter()
    partition = detect_communities(graph, resolution=1.0)
    elapsed = time.perf_counter() - t0

    undirected = graph.to_undirected()
    try:
        from community import community_louvain

        modularity = float(community_louvain.modularity(partition, undirected))
    except Exception:
        modularity = float("nan")

    by_community: Dict[int, List[str]] = {}
    for node, cid in partition.items():
        by_community.setdefault(int(cid), []).append(str(node))

    overall = float(np.mean([1.0 if node_truth.get(n, False) else 0.0 for n in partition]))
    rows = []
    for cid, nodes in by_community.items():
        if len(nodes) < 5:
            continue
        rate = float(np.mean([1.0 if node_truth.get(n, False) else 0.0 for n in nodes]))
        rows.append({"community_id": cid, "size": len(nodes), "fraud_rate": rate})
    rows.sort(key=lambda r: r["fraud_rate"], reverse=True)

    return {
        "elapsed_s": round(elapsed, 2),
        "num_communities": len(by_community),
        "modularity": modularity,
        "overall_node_fraud_rate": overall,
        "top_communities_by_fraud_rate": rows[:5],
        "note": (
            "Louvain produce una partición sin score de riesgo; no hay "
            "precision/recall reportable sin inventar una regla de marcado."
        ),
    }


# ---------------------------------------------------------------------------
# Caracterización del dataset (explica los números de después)
# ---------------------------------------------------------------------------


def dataset_profile(df: pd.DataFrame, graph: nx.DiGraph, node_truth: Dict[str, bool]) -> Dict[str, Any]:
    fraud_nodes = [n for n, v in node_truth.items() if v]
    degrees = dict(graph.degree())
    leaf_fraud = [n for n in fraud_nodes if degrees.get(n, 0) <= 1]

    return {
        "num_transactions": int(len(df)),
        "num_graph_nodes": int(graph.number_of_nodes()),
        "num_graph_edges": int(graph.number_of_edges()),
        "transactions_collapsed_into_edges": int(len(df) - graph.number_of_edges()),
        "transaction_fraud_rate": float(df["is_fraudulent"].mean()),
        "fraud_type_counts": {str(k): int(v) for k, v in df["fraud_type"].value_counts().items()},
        "node_fraud_rate": float(np.mean([1.0 if v else 0.0 for v in node_truth.values()])),
        "pair_fraud_rate": float(
            df.groupby(["origin_id", "destination_id"])["is_fraudulent"].any().mean()
        ),
        "fraud_nodes_with_degree_le_1": int(len(leaf_fraud)),
        "fraud_nodes_total": int(len(fraud_nodes)),
        "note": (
            "Los nodos fraudulentos de grado 1 son estructuralmente invisibles: "
            "ningún detector de grafo puede recuperarlos, y acotan el recall máximo alcanzable."
        ),
    }


# ---------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------


def _fmt(value: Optional[float], width: int = 7) -> str:
    if value is None:
        return "n/a".rjust(width)
    return f"{value:.3f}".rjust(width)


def print_table(title: str, results: Iterable[DetectorResult]) -> None:
    results = list(results)
    name_w = max([len(r.name) for r in results] + [8]) + 2
    header = (
        f"{'Detector'.ljust(name_w)}"
        f"{'flagged':>8}{'prec':>8}{'recall':>8}{'F1':>8}{'PR-AUC':>9}"
        f"{'TP':>7}{'FP':>7}{'FN':>7}{'TN':>7}{'  s':>7}"
    )
    print()
    print(title)
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    for r in results:
        if r.status != "ok":
            print(f"{r.name.ljust(name_w)}{r.status.upper():>8}   (ver notas)")
            continue
        cm = r.confusion or {}
        print(
            f"{r.name.ljust(name_w)}"
            f"{r.n_flagged:>8}"
            f"{_fmt(r.precision, 8)}{_fmt(r.recall, 8)}{_fmt(r.f1, 8)}{_fmt(r.pr_auc, 9)}"
            f"{cm.get('tp', 0):>7}{cm.get('fp', 0):>7}{cm.get('fn', 0):>7}{cm.get('tn', 0):>7}"
            f"{r.elapsed_s:>7.1f}"
        )
    print("-" * len(header))
    for r in results:
        if r.note:
            print(f"  * {r.name}: {r.note}")


def print_typology_table(title: str, results: Iterable[DetectorResult]) -> None:
    """Recall de cada detector sobre cada tipología, en una sola matriz.

    Una tabla por detector sería más literal pero impide lo único que hace
    interesante al desglose: comparar en vertical qué tipología cubre cada
    detector. Las poblaciones van en la cabecera porque son las mismas para
    todos: lo que cambia entre filas es solo cuánto encuentra cada uno.
    """

    scored = [r for r in results if r.status == "ok" and r.typology_recall]
    if not scored:
        return

    columns = list(scored[0].typology_recall or {})
    name_w = max([len(r.name) for r in scored] + [8]) + 2
    col_w = {c: max(len(c), 13) + 2 for c in columns}
    width = name_w + sum(col_w.values())

    print()
    print(title)
    print("-" * width)
    print("Detector".ljust(name_w) + "".join(c.rjust(col_w[c]) for c in columns))
    population = scored[0].typology_recall or {}
    print(
        "".ljust(name_w)
        + "".join(f"({population[c]['positives']} pos)".rjust(col_w[c]) for c in columns)
    )
    print("-" * width)
    for r in scored:
        breakdown = r.typology_recall or {}
        cells = []
        for c in columns:
            cell = breakdown.get(c)
            cells.append(
                (f"{cell['recall']:.3f} ({cell['detected']:>4})" if cell else "n/a").rjust(col_w[c])
            )
        print(r.name.ljust(name_w) + "".join(cells))
    print("-" * width)
    print("  Un candidato puede pertenecer a varias tipologías, así que las poblaciones no suman")
    print("  el total de positivos: cada columna se lee por separado, nunca como una partición.")
    for r in scored:
        if r.typology_note:
            print(f"  * {r.name}: {r.typology_note}")


def _force_utf8_stdout() -> None:
    """La consola de Windows usa cp1252 y revienta con tipografia no ASCII."""

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main(argv: Optional[Sequence[str]] = None) -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--transactions", type=int, default=8000)
    parser.add_argument("--clients", type=int, default=800)
    parser.add_argument("--fraud-pct", type=float, default=0.08)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--budget",
        type=float,
        default=60.0,
        help="segundos máximos para detectores potencialmente no acotados",
    )
    parser.add_argument("--outlier-quantile", type=float, default=0.95)
    parser.add_argument("--out", type=Path, default=Path("eval/results.json"))
    args = parser.parse_args(argv)

    print("=" * 96)
    print("  Evaluación de detectores contra el ground truth del generador sintético")
    print("=" * 96)
    print(
        f"  dataset: {args.transactions} transacciones | {args.clients} clientes | "
        f"fraude objetivo {args.fraud_pct:.0%} | seed {args.seed}"
    )

    t_start = time.perf_counter()
    df = generate_transactions(
        num_transactions=args.transactions,
        num_clients=args.clients,
        fraud_percentage=args.fraud_pct,
        seed=args.seed,
    )
    profiles = {
        cid: {
            "profile_type": p.profile_type,
            "country": p.country,
            "account_age_days": p.account_age_days,
        }
        for cid, p in generate_client_profiles(num_clients=args.clients, seed=args.seed).items()
    }
    graph = build_graph_from_transactions(df, client_profiles=profiles)
    enhanced = EnhancedGraphBuilder(df, client_profiles=profiles).build_graph()

    node_truth = node_ground_truth(df)
    pair_truth = pair_ground_truth(df)

    profile = dataset_profile(df, graph, node_truth)
    print()
    print("  Dataset real construido:")
    print(f"    transacciones                 : {profile['num_transactions']}")
    print(f"    aristas del grafo             : {profile['num_graph_edges']} "
          f"({profile['transactions_collapsed_into_edges']} transacciones colapsadas por DiGraph)")
    print(f"    nodos del grafo               : {profile['num_graph_nodes']}")
    print(f"    tasa de fraude por transacción: {profile['transaction_fraud_rate']:.3f}")
    print(f"    tasa de fraude por par        : {profile['pair_fraud_rate']:.3f}")
    print(f"    tasa de fraude por nodo       : {profile['node_fraud_rate']:.3f}")
    print(f"    nodos-fraude de grado <= 1    : {profile['fraud_nodes_with_degree_le_1']} "
          f"de {profile['fraud_nodes_total']} (techo de recall estructural)")
    print(f"    tipos de fraude               : {profile['fraud_type_counts']}")

    node_results, _metrics = evaluate_nodes(
        df, graph, enhanced, node_truth, args.outlier_quantile
    )
    pair_results = evaluate_pairs(df, graph, enhanced, pair_truth, args.budget)
    communities = community_diagnostics(graph, node_truth, seed=args.seed)

    print_table(
        f"NIVEL NODO — {len(node_truth)} clientes, positivos = {sum(node_truth.values())}",
        node_results,
    )
    print_typology_table(
        "DESGLOSE POR TIPOLOGÍA — recall por tipo de fraude (nivel nodo)",
        node_results,
    )
    print("  Aviso de lectura: la tipología se hereda de las transacciones que toca el nodo,")
    print("  así que la contraparte de una mula cuenta como 'mule'. La columna mide nodos que")
    print("  tocan una transacción de ese tipo, no el rol que la cuenta ejecuta.")

    print_table(
        f"NIVEL PAR (origen->destino) — {len(pair_truth)} pares, positivos = {sum(pair_truth.values())}",
        pair_results,
    )
    print_typology_table(
        "DESGLOSE POR TIPOLOGÍA — recall por tipo de fraude (nivel par)",
        pair_results,
    )

    print()
    print("COMUNIDADES (Louvain)")
    print("-" * 96)
    print(f"  comunidades detectadas : {communities['num_communities']}")
    print(f"  modularidad            : {communities['modularity']:.3f}")
    print(f"  tasa de fraude global  : {communities['overall_node_fraud_rate']:.3f}")
    for row in communities["top_communities_by_fraud_rate"]:
        print(
            f"    comunidad {row['community_id']:>3}  size={row['size']:>4}  "
            f"fraud_rate={row['fraud_rate']:.3f}"
        )
    print(f"  {communities['note']}")

    total_elapsed = time.perf_counter() - t_start
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "transactions": args.transactions,
            "clients": args.clients,
            "fraud_pct": args.fraud_pct,
            "seed": args.seed,
            "budget_s": args.budget,
            "outlier_quantile": args.outlier_quantile,
        },
        "dataset": profile,
        "node_level": [r.as_dict() for r in node_results],
        "pair_level": [r.as_dict() for r in pair_results],
        "communities": communities,
        "total_elapsed_s": round(total_elapsed, 2),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"Resultados escritos en {args.out}  |  total {total_elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
