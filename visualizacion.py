"""Dibujo del grafo con NetworkX y Matplotlib."""
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import networkx as nx

from dijkstra import etiqueta

COLOR = {
    "temporal": "#E3ECF7",
    "permanente": "#7BC47F",
    "actual": "#F5A623",
    "borde": "#2B4C7E",
    "arista": "#9AA5B1",
    "revisada": "#1F6FD1",
    "arbol": "#3C8D40",
    "camino": "#D0312D",
}


def posiciones(grafo, nivel):
    """Ubica los vértices por niveles, de izquierda a derecha.

    Cada nivel se desplaza un poco en vertical (con un desfase distinto por
    nivel) para que las aristas largas no pasen por encima de otros vértices.
    """
    capas = {}
    for v in grafo:
        capas.setdefault(nivel[v], []).append(v)
    pos = {}
    for c, vs in capas.items():
        desfase = ((c * 0.618) % 1 - 0.5) * 0.9
        for i, v in enumerate(vs):
            pos[v] = (c * 1.3, (len(vs) - 1) / 2 - i + desfase)
    return pos


def _curvatura(u, v, pos):
    """Elige la curvatura de la arista (u, v) para que no pase sobre otros vértices."""
    (x1, y1), (x2, y2) = pos[u], pos[v]
    otros = [p for w, p in pos.items() if w not in (u, v)]
    mejor, holgura_max = 0.12, -1.0
    for rad in (0.12, -0.12, 0.25, -0.25, 0.4, -0.4):
        cx, cy = (x1 + x2) / 2 + rad * (y2 - y1), (y1 + y2) / 2 - rad * (x2 - x1)
        puntos = [((1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t ** 2 * x2,
                   (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t ** 2 * y2)
                  for t in (0.15, 0.3, 0.45, 0.6, 0.75, 0.9)]
        holgura = min((math.dist(a, b) for a in puntos for b in otros), default=9.0)
        if holgura >= 0.45:
            return f"arc3,rad={rad}"
        if holgura > holgura_max:
            mejor, holgura_max = rad, holgura
    return f"arc3,rad={mejor}"


def _a_networkx(grafo):
    G = nx.DiGraph()
    G.add_nodes_from(grafo)
    for u in grafo:
        for v, w in grafo[u].items():
            G.add_edge(u, v, peso=w)
    return G


def dibujar_grafo(grafo, pos, paso=None, origen=None, destino=None,
                  caminos=None, titulo=""):
    """Dibuja el grafo.

    paso    -> estado de una iteración de Dijkstra (colores y etiquetas L).
    caminos -> lista de caminos mínimos que se resaltan en rojo.
    """
    G = _a_networkx(grafo)
    fig, ax = plt.subplots(figsize=(11, 5.6))
    tam_nodo = 900

    # colores de los vértices según su estado
    colores = []
    for v in G.nodes:
        if paso is None:
            colores.append(COLOR["temporal"])
        elif v == paso["seleccionado"]:
            colores.append(COLOR["actual"])
        elif v not in paso["temporales"]:
            colores.append(COLOR["permanente"])
        else:
            colores.append(COLOR["temporal"])
    bordes = [3.2 if v in (origen, destino) else 1.4 for v in G.nodes]

    # aristas: normales, revisadas en esta iteración, árbol de predecesores y camino mínimo
    revisadas, arbol, en_camino = set(), set(), set()
    if paso is not None:
        v = paso["seleccionado"]
        revisadas = {(v, d["x"]) for d in paso["decisiones"]}
        arbol = {(p, x) for x, ps in paso["pred"].items() for p in ps}
    for c in caminos or []:
        en_camino |= set(zip(c, c[1:]))

    estilo = {}
    for e in G.edges:
        if e in en_camino:
            estilo[e] = (COLOR["camino"], 3.6)
        elif e in revisadas:
            estilo[e] = (COLOR["revisada"], 3.0)
        elif e in arbol:
            estilo[e] = (COLOR["arbol"], 2.4)
        else:
            estilo[e] = (COLOR["arista"], 1.2)

    # cada arista se curva hacia el lado que más la aleja de los otros vértices
    grupos = {}
    for u, v in G.edges:
        grupos.setdefault(_curvatura(u, v, pos), []).append((u, v))
    for curva, aristas in grupos.items():
        nx.draw_networkx_edges(G, pos, ax=ax, edgelist=aristas,
                               edge_color=[estilo[e][0] for e in aristas],
                               width=[estilo[e][1] for e in aristas], arrowsize=16,
                               node_size=tam_nodo, connectionstyle=curva)
        nx.draw_networkx_edge_labels(
            G, pos, ax=ax, edge_labels={e: G.edges[e]["peso"] for e in aristas},
            font_size=9, connectionstyle=curva, node_size=tam_nodo,
            bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.9})
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=colores, node_size=tam_nodo,
                           edgecolors=COLOR["borde"], linewidths=bordes)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=12, font_weight="bold")

    # etiquetas L(v) sobre cada vértice
    if paso is not None:
        for v, (x, y) in pos.items():
            ax.annotate(etiqueta(paso["L"], paso["pred"], v, origen), xy=(x, y),
                        xytext=(0, 19), textcoords="offset points",
                        ha="center", va="bottom", fontsize=9, color="#1B2A41",
                        bbox={"boxstyle": "round,pad=0.2", "fc": "#FFF8E1", "ec": "#E0C27A"})

    if paso is None:
        leyenda = [Patch(fc=COLOR["temporal"], ec=COLOR["borde"], label="Vértice"),
                   Line2D([], [], color=COLOR["arista"], lw=1.2, label="Arista (peso)")]
    else:
        leyenda = [Patch(fc=COLOR["temporal"], ec=COLOR["borde"], label="Etiqueta temporal"),
                   Patch(fc=COLOR["permanente"], ec=COLOR["borde"], label="Etiqueta permanente"),
                   Patch(fc=COLOR["actual"], ec=COLOR["borde"], label="Vértice seleccionado"),
                   Line2D([], [], color=COLOR["revisada"], lw=3, label="Arista revisada"),
                   Line2D([], [], color=COLOR["arbol"], lw=2.4, label="Arista de predecesor")]
    if caminos:
        leyenda.append(Line2D([], [], color=COLOR["camino"], lw=3.6, label="Camino mínimo"))
    ax.legend(handles=leyenda, loc="upper center", bbox_to_anchor=(0.5, -0.02),
              ncol=len(leyenda), fontsize=8.5, frameon=False)
    ax.set_title(titulo, fontsize=12)
    ax.margins(0.08, 0.14)
    ax.axis("off")
    fig.tight_layout()
    return fig
