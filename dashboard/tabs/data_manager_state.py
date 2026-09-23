"""
Gestor centralizado del estado de datos para evitar problemas de serialización en Gradio.
Solo almacenamos objetos serializables: df, graph y diccionarios.
"""

from __future__ import annotations

import pickle
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

import networkx as nx
import pandas as pd


class DataStateManager:
    """
    Maneja el estado de datos de forma segura para Gradio.
    - Solo almacena tipos serializables
    - Proporciona métodos para acceder a datos
    - Cache temporal para objetos no serializables
    """
    
    _temp_dir = Path(tempfile.gettempdir()) / "fraud_detection_cache"
    _cache: Dict[str, Any] = {}
    
    def __init__(self):
        self._temp_dir.mkdir(exist_ok=True)
    
    @classmethod
    def save_state(
        cls,
        df: Optional[pd.DataFrame] = None,
        G: Optional[nx.DiGraph] = None,
        metrics: Optional[dict] = None,
        communities: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Guarda el estado de forma segura.
        Retorna un diccionario que Gradio puede serializar.
        
        Args:
            df: DataFrame de transacciones
            G: Grafo NetworkX
            metrics: Métricas del grafo
            communities: Comunidades detectadas
        
        Returns:
            Dict con estado serializable
        """
        state = {
            'has_data': False,
            'df_shape': None,
            'graph_nodes': 0,
            'graph_edges': 0,
            'metrics_keys': None,
            'communities_keys': None,
            'cache_id': None,
        }
        
        if df is not None and not df.empty:
            state['has_data'] = True
            state['df_shape'] = df.shape
            cache_id = hash(str(df.shape) + str(df['origin_id'].nunique()))
            state['cache_id'] = cache_id
            cls._cache[cache_id] = {'df': df}
        
        if G is not None and G.number_of_nodes() > 0:
            state['graph_nodes'] = G.number_of_nodes()
            state['graph_edges'] = G.number_of_edges()
            if 'cache_id' in state and state['cache_id']:
                cls._cache[state['cache_id']]['graph'] = G
            else:
                cache_id = G.number_of_nodes()
                state['cache_id'] = cache_id
                cls._cache[cache_id] = {'graph': G}
        
        if metrics is not None:
            state['metrics_keys'] = list(metrics.keys()) if isinstance(metrics, dict) else None
        
        if communities is not None:
            state['communities_keys'] = list(communities.keys()) if isinstance(communities, dict) else None
        
        return state
    
    @classmethod
    def get_df(cls, state: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Recupera el DataFrame del estado cacheado."""
        if state and state.get('cache_id'):
            cache = cls._cache.get(state['cache_id'], {})
            return cache.get('df')
        return None
    
    @classmethod
    def get_graph(cls, state: Dict[str, Any]) -> Optional[nx.DiGraph]:
        """Recupera el grafo del estado cacheado."""
        if state and state.get('cache_id'):
            cache = cls._cache.get(state['cache_id'], {})
            return cache.get('graph')
        return None
    
    @classmethod
    def clear_cache(cls) -> None:
        """Limpia el caché."""
        cls._cache.clear()
