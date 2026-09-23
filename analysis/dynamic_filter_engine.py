from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


@dataclass
class FilterSuggestion:
    """Representa un filtro sugerido para la UI.

    Attributes:
        type: Tipo de control de UI (multiselect | slider | checkbox | date_range)
        options: Opciones para multiselect
        min: Valor mínimo (slider/date)
        max: Valor máximo (slider/date)
    """

    type: str
    options: Optional[List[Any]] = None
    min: Optional[float] = None
    max: Optional[float] = None


class DynamicFilterEngine:
    """Analiza un DataFrame y genera filtros dinámicos y aplica filtros genéricos.

    - Detecta tipos de columnas: categórico, numérico, booleano, datetime
    - Sugiere controles para Gradio en base a los tipos
    - Aplica un diccionario de filtros de forma robusta y agnóstica a columnas faltantes
    """

    def __init__(self, df: pd.DataFrame):
        if not isinstance(df, pd.DataFrame):
            raise TypeError("df debe ser un pandas.DataFrame")
        # No mutar el original
        self._df = df.copy()
        self._col_types: Dict[str, str] = self._analyze_columns(self._df)

    # -----------------------------
    # Public API
    # -----------------------------
    def get_filter_suggestions(self) -> Dict[str, Dict[str, Any]]:
        """Retorna sugerencias de filtros para UI.

        Returns:
            dict: {column_name: {"type": ..., "options": [...], "min": x, "max": y}}
        """
        suggestions: Dict[str, Dict[str, Any]] = {}
        for col, ctype in self._col_types.items():
            if ctype == "categorical":
                options = self._get_unique_values(self._df[col])
                if 0 < len(options) <= 1000:  # límite razonable
                    suggestions[col] = {
                        "type": "multiselect",
                        "options": options,
                    }
            elif ctype == "numeric":
                cmin, cmax = self._get_numeric_range(self._df[col])
                if cmin is not None and cmax is not None:
                    suggestions[col] = {
                        "type": "slider",
                        "min": float(cmin),
                        "max": float(cmax),
                    }
            elif ctype == "boolean":
                suggestions[col] = {"type": "checkbox"}
            elif ctype == "datetime":
                dt_min = pd.to_datetime(self._df[col]).min()
                dt_max = pd.to_datetime(self._df[col]).max()
                suggestions[col] = {
                    "type": "date_range",
                    "min": str(dt_min),
                    "max": str(dt_max),
                }
        return suggestions

    def apply_filters(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Aplica un diccionario de filtros y retorna un nuevo DataFrame.

        El formato de `filters` debe concordar con `get_filter_suggestions`:
        - multiselect: list de valores → df[col].isin(values)
        - slider: {"min": x, "max": y} → rango cerrado
        - checkbox: bool → df[col] == value
        - date_range: {"min": iso, "max": iso} → rango de fechas
        Columnas inexistentes o valores None son ignorados.
        """
        if not filters:
            return self._df.copy()

        dff = self._df.copy()
        for col, rule in filters.items():
            if col not in dff.columns:
                continue
            ctype = self._col_types.get(col)
            if ctype == "categorical":
                values = rule if isinstance(rule, list) else None
                if values:
                    dff = dff[dff[col].isin(values)]
            elif ctype == "numeric":
                rmin = None
                rmax = None
                if isinstance(rule, dict):
                    rmin = rule.get("min")
                    rmax = rule.get("max")
                if rmin is not None:
                    dff = dff[dff[col] >= float(rmin)]
                if rmax is not None:
                    dff = dff[dff[col] <= float(rmax)]
            elif ctype == "boolean":
                if isinstance(rule, bool):
                    dff = dff[dff[col] == rule]
            elif ctype == "datetime":
                if isinstance(rule, dict):
                    rmin = rule.get("min")
                    rmax = rule.get("max")
                    series_dt = pd.to_datetime(dff[col], errors="coerce")
                    if rmin is not None:
                        dff = dff[series_dt >= pd.to_datetime(rmin)]
                    if rmax is not None:
                        dff = dff[series_dt <= pd.to_datetime(rmax)]
        return dff.reset_index(drop=True)

    # -----------------------------
    # Internals
    # -----------------------------
    def _analyze_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        col_types: Dict[str, str] = {}
        for col in df.columns:
            dtype = df[col].dtype
            if pd.api.types.is_bool_dtype(dtype):
                col_types[col] = "boolean"
            elif pd.api.types.is_numeric_dtype(dtype):
                col_types[col] = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                col_types[col] = "datetime"
            else:
                # Heurística para categórico (pocos valores únicos contra filas)
                nunique = df[col].nunique(dropna=True)
                if nunique <= max(30, int(0.05 * len(df))):
                    col_types[col] = "categorical"
                else:
                    # por defecto categórico (string) para UI si no es numérica/fecha/bool
                    col_types[col] = "categorical"
        return col_types

    @staticmethod
    def _get_unique_values(series: pd.Series) -> List[Any]:
        vals = series.dropna().unique().tolist()
        # Orden estable
        try:
            return sorted(vals)
        except Exception:
            return vals

    @staticmethod
    def _get_numeric_range(series: pd.Series) -> Tuple[Optional[float], Optional[float]]:
        try:
            s = pd.to_numeric(series, errors="coerce")
            return float(s.min()), float(s.max())
        except Exception:
            return None, None
