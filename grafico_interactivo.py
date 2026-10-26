"""Gráficos interactivos del grafo con Plotly: hover, clic sobre los vértices y animación.

Se respeta el estilo de visualizacion.py (colores, posiciones y curvatura de las
aristas); Matplotlib se sigue usando solo para la imagen PNG del informe.
"""
import math

import plotly.graph_objects as go

from dijkstra import etiqueta, texto_decision
from grafo import INF
from visualizacion import COLOR, _curvatura

FUENTE = '"Source Sans Pro", "Source Sans", sans-serif'
TAM_VERTICE = 34                 # diámetro del vértice en píxeles
TAM_PESO = 21                    # diámetro del círculo blanco del peso
BORDE, BORDE_GRUESO = 1.6, 4.2   # borde normal y de origen/destino
TRAMO_FLECHA = 0.4               # fracción final de la curva que, como máximo, cubre la flecha

# las cuatro trazas de aristas, en orden de dibujo: (color, grosor en px)
ESTILOS = {
    "normal": (COLOR["arista"], 1.6),
    "arbol": (COLOR["arbol"], 3.0),
    "revisada": (COLOR["revisada"], 3.6),
    "camino": (COLOR["camino"], 4.4),
}

CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


# ---------------------------------------------------------------- geometría
def _bezier(p0, c, p2, t):
    return ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t ** 2 * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t ** 2 * p2[1])


def _geometria(grafo, pos):
    """Forma de cada arista (se calcula una sola vez y sirve para todos los cuadros).

    Es la Bézier cuadrática de _curvatura (punto medio + rad·(dy, −dx)). La curva se
    dibuja completa; la annotation solo pone la punta, orientada según la cuerda que va
    de la cola al vértice (en ese tramo final la cuerda casi coincide con la curva).
    """
    geo = {}
    for u in grafo:
        for x in grafo[u]:
            p0, p2 = pos[u], pos[x]
            (x1, y1), (x2, y2) = p0, p2
            rad = float(_curvatura(u, x, pos).split("=")[1])
            c = ((x1 + x2) / 2 + rad * (y2 - y1), (y1 + y2) / 2 - rad * (x2 - x1))
            puntos = [_bezier(p0, c, p2, i / 30) for i in range(31)]
            # cola a unas 0,75 unidades del vértice (como máximo el 40 % final de la curva),
            # para que la flecha sea más larga que el radio del vértice
            tramo = min(TRAMO_FLECHA, 0.75 / math.dist(p0, p2))
            geo[(u, x)] = {"puntos": puntos, "cola": _bezier(p0, c, p2, 1 - tramo),
                           "medio": _bezier(p0, c, p2, 0.5)}
    return geo


# ---------------------------------------------------------------- textos
def _hover_vertice(grafo, v, paso, origen, destino, solucion):
    rol = " (origen)" if v == origen else " (destino)" if v == destino else ""
    lineas = [f"<b>{v}</b>{rol}"]
    if paso is None:
        salen = ", ".join(f"{v}→{x} ({w})" for x, w in sorted(grafo[v].items()))
        llegan = ", ".join(f"{u}→{v} ({grafo[u][v]})" for u in grafo if v in grafo[u])
        lineas += [f"Aristas que salen: {salen or 'ninguna'}",
                   f"Aristas que llegan: {llegan or 'ninguna'}"]
    else:
        if v == paso["seleccionado"] and not solucion:
            estado = "seleccionado en esta iteración (pasa a permanente)"
        else:
            estado = "temporal" if v in paso["temporales"] else "permanente"
        L = "∞" if paso["L"][v] == INF else paso["L"][v]
        lineas += [f"L({v}) = {L}", f"Estado: {estado}",
                   f"Predecesores: {', '.join(paso['pred'][v]) or '—'}"]
    return "<br>".join(lineas)


def _hover_arista(u, x, w, paso, decisiones, arbol, camino):
    lineas = [f"<b>w({u}, {x}) = {w}</b>"]
    if (u, x) in decisiones:
        v = paso["seleccionado"]
        lineas.append("Revisada en esta iteración: " +
                      texto_decision(v, paso["L"][v], decisiones[(u, x)]))
    if (u, x) in arbol:
        lineas.append(f"Arista de predecesor: {u} es predecesor de {x}.")
    if (u, x) in camino:
        lineas.append("Forma parte del camino mínimo.")
    return "<br>".join(lineas)


# ---------------------------------------------------------------- contenido de un cuadro
def _contenido(grafo, pos, geo, paso, origen, destino, caminos, solucion=False):
    """Trazas (4 de aristas, pesos y vértices) y annotations (flechas y etiquetas L)."""
    decisiones, arbol, camino = {}, set(), set()
    if paso is not None:
        if not solucion:
            decisiones = {(paso["seleccionado"], d["x"]): d for d in paso["decisiones"]}
        arbol = {(p, x) for x, ps in paso["pred"].items() for p in ps}
    for c in caminos or []:
        camino |= set(zip(c, c[1:]))

    def estilo(e):
        if e in camino:
            return "camino"
        if e in decisiones:
            return "revisada"
        return "arbol" if e in arbol else "normal"

    borde = {v: BORDE_GRUESO if v in (origen, destino) else BORDE for v in grafo}
    tramos = {s: ([], []) for s in ESTILOS}
    flechas, pesos_x, pesos_y, pesos_txt, pesos_hover, pesos_id = [], [], [], [], [], []
    for (u, x), g in geo.items():
        s = estilo((u, x))
        color, ancho = ESTILOS[s]
        xs, ys = tramos[s]
        xs.extend([p[0] for p in g["puntos"]] + [None])
        ys.extend([p[1] for p in g["puntos"]] + [None])
        # el tamaño de la punta es arrowsize·arrowwidth: con el ancho mínimo el trazo recto
        # de la annotation no se ve y solo queda la punta sobre la curva
        flechas.append(dict(
            x=pos[x][0], y=pos[x][1], ax=g["cola"][0], ay=g["cola"][1],
            xref="x", yref="y", axref="x", ayref="y", text="", showarrow=True,
            arrowhead=2, arrowwidth=0.1, arrowsize=10 * max(2.4, 0.75 * ancho),
            arrowcolor=color, standoff=TAM_VERTICE / 2 + borde[x] / 2))
        pesos_x.append(g["medio"][0])
        pesos_y.append(g["medio"][1])
        pesos_txt.append(str(grafo[u][x]))
        pesos_hover.append(_hover_arista(u, x, grafo[u][x], paso, decisiones, arbol, camino))
        pesos_id.append(["e", u, x])

    sin_atenuar = dict(selected=dict(marker=dict(opacity=1)),
                       unselected=dict(marker=dict(opacity=1)))
    trazas = [go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=ESTILOS[s][0],
                         width=ESTILOS[s][1]), hoverinfo="skip", showlegend=False)
              for s, (xs, ys) in tramos.items()]
    trazas.append(go.Scatter(
        x=pesos_x, y=pesos_y, mode="markers+text", text=pesos_txt, customdata=pesos_id,
        marker=dict(size=TAM_PESO, color="white", opacity=1, line=dict(width=0)),
        textfont=dict(size=12, color="#1B2A41"), hovertext=pesos_hover, hoverinfo="text",
        showlegend=False, cliponaxis=False, **sin_atenuar))

    colores = []
    for v in grafo:
        if paso is None or v in paso["temporales"]:
            colores.append(COLOR["temporal"])
        elif v == paso["seleccionado"] and not solucion:
            colores.append(COLOR["actual"])
        else:
            colores.append(COLOR["permanente"])
    vertices = list(grafo)
    trazas.append(go.Scatter(
        x=[pos[v][0] for v in vertices], y=[pos[v][1] for v in vertices],
        mode="markers+text", text=vertices, customdata=[["v", v] for v in vertices],
        marker=dict(size=TAM_VERTICE, color=colores, opacity=1,
                    line=dict(color=COLOR["borde"], width=[borde[v] for v in vertices])),
        textfont=dict(size=14, color="black", weight="bold"),
        hovertext=[_hover_vertice(grafo, v, paso, origen, destino, solucion)
                   for v in vertices],
        hoverinfo="text", showlegend=False, cliponaxis=False, **sin_atenuar))

    etiquetas = []
    if paso is not None:
        etiquetas = [dict(x=pos[v][0], y=pos[v][1], xref="x", yref="y", yshift=29,
                          text=etiqueta(paso["L"], paso["pred"], v, origen), showarrow=False,
                          font=dict(size=12, color="#1B2A41"), bgcolor="#FFF8E1",
                          bordercolor="#E0C27A", borderwidth=1, borderpad=2)
                     for v in vertices]
    return trazas, flechas + etiquetas


# ---------------------------------------------------------------- leyenda y layout
def _leyenda(con_paso, con_camino):
    """Trazas vacías que solo aparecen en la leyenda (como los Patch de Matplotlib)."""
    def vertice(nombre, color):
        return go.Scatter(x=[None], y=[None], mode="markers", name=nombre, hoverinfo="skip",
                          marker=dict(size=14, color=color,
                                      line=dict(color=COLOR["borde"], width=1.4)))

    def arista(nombre, s):
        return go.Scatter(x=[None], y=[None], mode="lines", name=nombre, hoverinfo="skip",
                          line=dict(color=ESTILOS[s][0], width=ESTILOS[s][1]))

    if con_paso:
        items = [vertice("Etiqueta temporal", COLOR["temporal"]),
                 vertice("Etiqueta permanente", COLOR["permanente"]),
                 vertice("Vértice seleccionado", COLOR["actual"]),
                 arista("Arista revisada", "revisada"),
                 arista("Arista de predecesor", "arbol")]
    else:
        items = [vertice("Vértice", COLOR["temporal"]), arista("Arista (peso)", "normal")]
    if con_camino:
        items.append(arista("Camino mínimo", "camino"))
    return items


def _layout(grafo, pos, geo, titulo, alto, leyenda_arriba=False):
    xs = [p[0] for p in pos.values()] + [p[0] for g in geo.values() for p in g["puntos"]]
    ys = [p[1] for p in pos.values()] + [p[1] for g in geo.values() for p in g["puntos"]]
    eje = dict(visible=False, showgrid=False, zeroline=False)
    if leyenda_arriba:
        leyenda = dict(orientation="h", x=0.5, xanchor="center", y=1.0, yanchor="bottom")
        margen = dict(l=10, r=10, t=90, b=80)
    else:
        leyenda = dict(orientation="h", x=0.5, xanchor="center", y=-0.01, yanchor="top")
        margen = dict(l=10, r=10, t=50, b=40)
    return go.Layout(
        title=dict(text=titulo, x=0.5, xanchor="center", y=0.98, yanchor="top",
                   font=dict(size=17)),
        xaxis=dict(eje, range=[min(xs) - 0.5, max(xs) + 0.5]),
        yaxis=dict(eje, range=[min(ys) - 0.5, max(ys) + 0.75]),
        height=alto, margin=margen, font=dict(family=FUENTE, size=13, color="#1B2A41"),
        plot_bgcolor="white", paper_bgcolor="white", hovermode="closest", dragmode="pan",
        hoverlabel=dict(bgcolor="white", bordercolor=COLOR["borde"], align="left",
                        font=dict(family=FUENTE, size=13, color="#1B2A41")),
        legend=dict(leyenda, itemclick=False, itemdoubleclick=False, font=dict(size=13)),
        uirevision="|".join(f"{u}{x}{grafo[u][x]}" for u in grafo for x in grafo[u]),
    )


# ---------------------------------------------------------------- funciones públicas
def figura_grafo(grafo, pos, paso=None, origen=None, destino=None, caminos=None,
                 titulo="", alto=540):
    """Gráfico interactivo del grafo (o de una iteración de Dijkstra si se pasa paso)."""
    geo = _geometria(grafo, pos)
    trazas, notas = _contenido(grafo, pos, geo, paso, origen, destino, caminos)
    fig = go.Figure(data=trazas + _leyenda(paso is not None, bool(caminos)),
                    layout=_layout(grafo, pos, geo, titulo, alto))
    fig.update_layout(annotations=notas)
    return fig


def animacion(grafo, pos, pasos, origen, destino, caminos=None, alto=640):
    """Animación de Dijkstra: un cuadro por iteración y un cuadro final con la solución."""
    geo = _geometria(grafo, pos)
    cuadros = []
    for p in pasos:
        titulo = ("Inicialización" if p["iteracion"] == 0 else
                  f"Iteración {p['iteracion']}: se fija el vértice {p['seleccionado']}")
        trazas, notas = _contenido(grafo, pos, geo, p, origen, destino, None)
        cuadros.append((str(p["iteracion"]), titulo, trazas, notas))
    final = pasos[-1]
    if caminos:
        titulo = (f"Solución: camino mínimo de {origen} a {destino} "
                  f"(distancia {final['L'][destino]})")
    else:
        titulo = f"Solución: no existe camino de {origen} a {destino}"
    trazas, notas = _contenido(grafo, pos, geo, final, origen, destino, caminos, solucion=True)
    cuadros.append(("Solución", titulo, trazas, notas))

    frames = [go.Frame(name=nombre, data=trazas, traces=list(range(len(trazas))),
                       layout=dict(annotations=notas,
                                   title=dict(text=titulo, x=0.5, xanchor="center",
                                              y=0.98, yanchor="top", font=dict(size=17))))
              for nombre, titulo, trazas, notas in cuadros]
    _, titulo0, trazas0, notas0 = cuadros[0]
    fig = go.Figure(data=trazas0 + _leyenda(True, bool(caminos)), frames=frames,
                    layout=_layout(grafo, pos, geo, titulo0, alto, leyenda_arriba=True))
    inmediato = {"frame": {"duration": 0, "redraw": True}, "mode": "immediate",
                 "transition": {"duration": 0}}
    fig.update_layout(
        annotations=notas0,
        updatemenus=[dict(
            type="buttons", direction="left", showactive=False, x=0, xanchor="left",
            y=0, yanchor="top", pad=dict(t=12, r=10),
            buttons=[dict(label="▶ Play", method="animate",
                          args=[None, {"frame": {"duration": 1400, "redraw": True},
                                       "fromcurrent": True, "transition": {"duration": 0}}]),
                     dict(label="❚❚ Pausa", method="animate",
                          args=[[None], {"frame": {"duration": 0, "redraw": False},
                                         "mode": "immediate", "transition": {"duration": 0}}])])],
        sliders=[dict(
            active=0, x=0.2, len=0.77, y=0, yanchor="top", pad=dict(t=8),
            currentvalue=dict(visible=False),
            steps=[dict(label=nombre, method="animate", args=[[nombre], inmediato])
                   for nombre, *_ in cuadros])],
    )
    return fig
