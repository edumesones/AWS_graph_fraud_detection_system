from __future__ import annotations

from typing import Dict, Optional, List
import json

import networkx as nx
from pyvis.network import Network


class InteractiveGraphExplorer:
    """Renderiza un grafo enriquecido en HTML interactivo usando Pyvis."""

    def __init__(self, G: nx.DiGraph, df=None):
        self.G = G
        self.df = df

    def render(self, highlighted_node: str = None) -> str:
        """Renderiza el grafo con opciones por defecto y opcionalmente destaca un nodo."""
        return self.render_with_options(
            self.G,
            highlighted_node=highlighted_node,
            node_size_by="degree_in",
            edge_width_by="num_transactions",
            color_by="avg_risk_score",
            min_edge_weight=1,
        )

    def render_with_options(
        self,
        G: nx.DiGraph,
        highlighted_node: str = None,
        node_size_by: str = "degree_in",
        edge_width_by: str = "num_transactions",
        color_by: str = "avg_risk_score",
        min_edge_weight: int = 1,
        *,
        layout: str = "fixed",  # "fixed" | "hierarchical" | "force" | "radial"
        seed: int = 42,
        layout_cache_key: Optional[str] = None,
        reuse_cached_layout: bool = True,
        export_html_path: Optional[str] = None,
        spacing_scale: float = 1.35,
        radial_center_node: Optional[str] = None,
        show_labels: bool = True,
    ) -> str:
        net = Network(height="800px", directed=True, notebook=False)
        # Physics off by default for readability; zoom/pan enabled
        opts = {
            "physics": {"enabled": False},
            "interaction": {
                "dragNodes": False,
                "zoomView": True,
                "dragView": True,
                "keyboard": {"enabled": True}
            },
            "layout": {"improvedLayout": True},
            "edges": {
                "smooth": {"enabled": True, "type": "continuous"},
                "color": {"opacity": 0.25}
            },
        }
        if not show_labels:
            opts["nodes"] = {"font": {"size": 0}, "shape": "dot"}
        # Configure hierarchical layout with generous separations when requested
        if layout == "hierarchical":
            level_sep = int(320 * float(spacing_scale))
            node_space = int(220 * float(spacing_scale))
            opts["layout"] = {
                "hierarchical": {
                    "enabled": True,
                    "direction": "LR",
                    "sortMethod": "hubsize",
                    "levelSeparation": level_sep,
                    "nodeSpacing": node_space,
                }
            }
        net.set_options(json.dumps(opts))

        # Copiar y filtrar por peso mínimo
        H = nx.DiGraph()
        for u, v, d in G.edges(data=True):
            # Métrica base desde atributos de la arista
            raw_metric = d.get(edge_width_by, 0)
            try:
                metric = float(raw_metric)
            except Exception:
                metric = 0.0

            # Fallback: si filtramos por num_transactions pero no existe, calcularlo del DataFrame
            if edge_width_by == "num_transactions" and metric <= 0 and self.df is not None:
                try:
                    df = self.df
                    if "origin_id" in df.columns and "destination_id" in df.columns:
                        mask = (df["origin_id"] == u) & (df["destination_id"] == v)
                        tx_count = int(mask.sum())
                        metric = float(tx_count)
                        # Enriquecer atributos visibles
                        d = dict(d)
                        d["num_transactions"] = tx_count
                        if "amount" in df.columns:
                            d.setdefault("weight", float(df.loc[mask, "amount"].sum()))
                except Exception:
                    pass

            if metric >= float(min_edge_weight):
                H.add_edge(u, v, **d)
                for n in (u, v):
                    if n not in H:
                        H.add_node(n, **G.nodes[n])

        def _norm(val: float, lo: float, hi: float) -> float:
            if hi <= lo:
                return 1.0
            return (float(val) - float(lo)) / (float(hi) - float(lo) + 1e-9)

        # Stats para normalización
        node_vals = [float(H.nodes[n].get(node_size_by, 1.0)) for n in H.nodes]
        node_lo, node_hi = (min(node_vals) if node_vals else 0.0, max(node_vals) if node_vals else 1.0)
        edge_vals = [float(d.get(edge_width_by, 1.0)) for _, _, d in H.edges(data=True)]
        edge_lo, edge_hi = (min(edge_vals) if edge_vals else 0.0, max(edge_vals) if edge_vals else 1.0)

        # Colormap simple por color_by
        def _color(value: float) -> str:
            x = _norm(value, 0.0, 1.0)
            r = int(255 * x)
            b = int(255 * (1 - x))
            return f"rgb({r},100,{b})"

        # Deterministic layout: try load cached coordinates first
        positions: Dict[str, Dict[str, float]] = {}
        if layout in ("fixed", "force") and layout_cache_key and reuse_cached_layout:
            try:
                import os
                cache_dir = os.path.join("exports", "layouts")
                cache_path = os.path.join(cache_dir, f"{layout_cache_key}.json")
                if os.path.exists(cache_path):
                    with open(cache_path, "r", encoding="utf-8") as f:
                        positions = json.load(f)
            except Exception:
                positions = {}

        if layout == "radial":
            # Radial por niveles: calcular niveles BFS desde radial_center_node
            center = radial_center_node or highlighted_node
            positions = {}
            if center and center in H:
                # BFS en subgrafo no dirigido para estabilidad
                levels: Dict[str, int] = {center: 0}
                frontier: List[str] = [center]
                while frontier:
                    nxt: List[str] = []
                    for n in frontier:
                        neighbors = list(H.successors(n)) + list(H.predecessors(n))
                        for nb in neighbors:
                            if nb not in levels:
                                levels[nb] = levels[n] + 1
                                nxt.append(nb)
                    frontier = nxt
                # Distribuir por anillos
                max_level = max(levels.values()) if levels else 0
                by_level: Dict[int, List[str]] = {}
                for n, lv in levels.items():
                    by_level.setdefault(lv, []).append(n)
                base_r = 380.0 * float(spacing_scale)
                import math
                for lv, nodes_at in by_level.items():
                    nodes_at.sort()
                    # aumentar radio en función de cuántos nodos hay en el anillo para evitar solapamiento
                    # factor agresivo: 1 + n/2 para anillos muy poblados
                    ring_factor = 1.0 + (len(nodes_at) / 2.0)
                    r = base_r * max(1, lv) * ring_factor
                    count = max(1, len(nodes_at))
                    for idx, n in enumerate(nodes_at):
                        theta = 2.0 * math.pi * (idx / count)
                        x = r * math.cos(theta)
                        y = r * math.sin(theta)
                        positions[str(n)] = {"x": float(x), "y": float(y)}
            else:
                positions = {}
        elif layout == "hierarchical":
            # Keep coordinates free; vis.js hierarchical handles arrangement. Physics already disabled.
            pass
        else:
            # Compute coordinates if not provided by cache
            to_compute = [n for n in H.nodes if str(n) not in positions]
            if to_compute:
                try:
                    # kamada_kawai is stable and readable; fallback to spring
                    pos_calc = nx.kamada_kawai_layout(H.subgraph(to_compute), scale=1000)
                except Exception:
                    pos_calc = nx.spring_layout(H.subgraph(to_compute), seed=seed, k=None)
                for n, (x, y) in pos_calc.items():
                    positions[str(n)] = {"x": float(x) * float(spacing_scale), "y": float(y) * float(spacing_scale)}

        # Persist computed positions if a cache key is provided
        if layout in ("fixed", "force") and layout_cache_key and positions:
            try:
                import os
                os.makedirs(os.path.join("exports", "layouts"), exist_ok=True)
                cache_path = os.path.join("exports", "layouts", f"{layout_cache_key}.json")
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump({str(n): positions.get(str(n), {}) for n in H.nodes}, f)
            except Exception:
                pass

        for n, data in H.nodes(data=True):
            size_val = float(data.get(node_size_by, 1.0))
            color_val = float(data.get(color_by, 0.0))
            
            # Si es el nodo destacado, usar color especial
            if highlighted_node and str(n) == str(highlighted_node):
                node_color = "#FFD700"  # Dorado para el nodo seleccionado
                node_size = size_val * 2  # Hacerlo más grande
            else:
                node_color = _color(color_val)
                node_size = size_val
            
            node_kwargs: Dict[str, object] = {
                "label": (str(n) if show_labels else ""),
                "value": node_size,
                "color": node_color,
                "title": self.get_node_tooltip(G, str(n)),
            }
            if layout in ("fixed", "force"):
                xy = positions.get(str(n))
                if xy is not None:
                    node_kwargs.update({
                        "x": float(xy.get("x", 0.0)),
                        "y": float(xy.get("y", 0.0)),
                        "fixed": True,
                        "physics": False,
                    })

            net.add_node(str(n), **node_kwargs)

        for u, v, data in H.edges(data=True):
            width_val = float(data.get(edge_width_by, 1.0))
            net.add_edge(str(u), str(v), width=1 + 4 * _norm(width_val, edge_lo, edge_hi), title=self.get_edge_tooltip(G, str(u), str(v)))

        # Generar HTML usando Pyvis y embeberlo de forma segura dentro de Gradio
        import tempfile
        import os
        import base64
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html') as f:
            temp_path = f.name
        
        net.save_graph(temp_path)
        
        with open(temp_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        os.unlink(temp_path)

        # Guardado opcional a HTML estático (ligero; útil para compartir)
        if export_html_path:
            try:
                import os
                os.makedirs(os.path.dirname(export_html_path), exist_ok=True)
                with open(export_html_path, "w", encoding="utf-8") as outf:
                    outf.write(html_content)
            except Exception:
                pass

        # Envolver en un iframe con data URL para evitar conflictos de sandbox y link de descarga
        encoded = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
        data_url = f"data:text/html;base64,{encoded}"
        iframe = (
            f"<iframe src=\"{data_url}\" "
            f"style=\"width:100%; height:800px; border:none;\" "
            f"sandbox=\"allow-scripts allow-same-origin\"></iframe>"
        )
        download_html = (
            f"<div style=\"margin-top:8px; text-align:right;\">"
            f"<a href=\"{data_url}\" download=\"graph.html\" "
            f"style=\"font-family:Arial; font-size:14px; text-decoration:none; padding:6px 10px; border:1px solid #888; border-radius:6px;\">"
            f"⬇️ Download HTML</a></div>"
        )
        return iframe + download_html

    def get_node_tooltip(self, G: nx.DiGraph, node_id: str) -> str:
        d = G.nodes[node_id]
        df = self.df if hasattr(self, 'df') and isinstance(self.df, object) else None
        if df is not None:
            try:
                import pandas as pd  # ensure available
                deg_in = int(df[df['destination_id'] == node_id].shape[0]) if 'destination_id' in df.columns else int(d.get('degree_in', 0))
                deg_out = int(df[df['origin_id'] == node_id].shape[0]) if 'origin_id' in df.columns else int(d.get('degree_out', 0))
            except Exception:
                deg_in = int(d.get('degree_in', 0))
                deg_out = int(d.get('degree_out', 0))
        else:
            deg_in = int(d.get('degree_in', 0))
            deg_out = int(d.get('degree_out', 0))

        community = d.get('community')
        if community is None:
            community = d.get('community_id', d.get('comm_id', 'NA'))

        lines = [
            f"client_id - {node_id}",
            f"profile - {d.get('profile_type','-')}",
            f"country - {d.get('country','-')}",
            f"community - {community}",
            f"degree_in - {deg_in}",
            f"degree_out - {deg_out}",
            f"total_volume - {round(float(d.get('total_volume', 0.0)), 2)}",
        ]
        return "\n".join(lines)

    def get_edge_tooltip(self, G: nx.DiGraph, u: str, v: str) -> str:
        if not G.has_edge(u, v):
            return ""
        d = G[u][v]
        df = self.df if hasattr(self, 'df') and isinstance(self.df, object) else None
        total_tx = d.get('num_transactions', 0)
        total_amount = float(d.get('weight', 0.0))
        fraud_tx = 0
        cash_amount = 0.0
        intl_amount = 0.0
        try:
            if df is not None:
                mask = (df.get('origin_id') == u) & (df.get('destination_id') == v)
                df_ev = df[mask]
                if not df_ev.empty:
                    total_tx = int(df_ev.shape[0])
                    if 'is_fraudulent' in df_ev.columns:
                        fraud_tx = int(df_ev['is_fraudulent'].astype(bool).sum())
                    if 'amount' in df_ev.columns:
                        total_amount = float(df_ev['amount'].sum())
                    if 'transaction_type' in df_ev.columns:
                        cash_amount = float(df_ev[df_ev['transaction_type'] == 'CASH']['amount'].sum())
                    if 'is_international' in df_ev.columns:
                        intl_amount = float(df_ev[df_ev['is_international'] == True]['amount'].sum())
        except Exception:
            pass

        lines = [
            f"edge - {u} -> {v}",
            f"num_tx - {total_tx}",
            f"num_tx_fraud - {fraud_tx}",
            f"total_amount - {round(total_amount,2)}",
            f"cash_amount - {round(cash_amount,2)}",
            f"transfer_international_amount - {round(intl_amount,2)}",
        ]
        return "\n".join(lines)
