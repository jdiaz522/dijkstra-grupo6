"""Algoritmo de Dijkstra paso a paso.

Se sigue el algoritmo 8.4.1 de Johnsonbaugh (2005, pp. 347-348) con dos
cambios que pide el proyecto:
  1. El grafo es dirigido, así que en cada iteración solo se revisan las
     aristas que salen del vértice seleccionado.
  2. Cada vértice guarda la lista de TODOS sus predecesores en caminos
     mínimos (no solo uno), para contar y reconstruir todos los caminos
     mínimos entre el origen y el destino.
"""
from grafo import INF


def _registrar(iteracion, v, L, pred, T, decisiones):
    """Copia el estado del algoritmo para poder mostrarlo después."""
    return {
        "iteracion": iteracion,
        "seleccionado": v,
        "L": dict(L),
        "pred": {x: list(p) for x, p in pred.items()},
        "temporales": set(T),
        "decisiones": decisiones,
    }


def dijkstra_paso_a_paso(grafo, origen, destino):
    """Ejecuta Dijkstra y devuelve la lista de pasos, las etiquetas L y los predecesores."""
    L = {v: INF for v in grafo}            # etiquetas L(v)            (líneas 3-4)
    pred = {v: [] for v in grafo}          # predecesores en caminos mínimos
    L[origen] = 0                          # L(a) = 0                  (línea 2)
    T = set(grafo)                         # vértices con etiqueta temporal (línea 5)
    pasos = [_registrar(0, None, L, pred, T, [])]

    iteracion = 0
    while destino in T:                                  # línea 8
        v = min(T, key=lambda x: (L[x], x))              # línea 9: menor L(v)
        if L[v] == INF:                                  # lo que queda es inalcanzable
            break
        T.remove(v)                                      # línea 10: etiqueta permanente
        iteracion += 1
        decisiones = []
        for x in sorted(grafo[v]):                       # línea 11: aristas (v, x)
            w = grafo[v][x]
            if x not in T:
                decisiones.append({"x": x, "w": w, "tipo": "permanente"})
                continue
            anterior, candidato = L[x], L[v] + w         # línea 12
            if candidato < anterior:
                L[x], pred[x], tipo = candidato, [v], "mejora"
            elif candidato == anterior:
                pred[x].append(v)                        # empate: otro camino mínimo
                tipo = "empate"
            else:
                tipo = "sin_cambio"
            decisiones.append({"x": x, "w": w, "anterior": anterior,
                               "candidato": candidato, "tipo": tipo})
        pasos.append(_registrar(iteracion, v, L, pred, T, decisiones))
    return pasos, L, pred


def contar_caminos(pred, origen, destino):
    """Número de caminos mínimos: N(origen) = 1 y N(x) = suma de N(p) para cada predecesor p."""
    memo = {origen: 1}

    def N(v):
        if v not in memo:
            memo[v] = sum(N(p) for p in pred[v])
        return memo[v]

    return N(destino)


def reconstruir_caminos(pred, origen, destino):
    """Recorre los predecesores hacia atrás (del destino al origen) y arma cada camino."""
    if destino == origen:
        return [[origen]]
    caminos = []
    for p in pred[destino]:
        for camino in reconstruir_caminos(pred, origen, p):
            caminos.append(camino + [destino])
    return caminos


def texto_decision(v, L_v, d):
    """Explicación en palabras de lo que se decidió con la arista (v, x)."""
    x, w = d["x"], d["w"]
    if d["tipo"] == "permanente":
        return f"({v}, {x}): {x} ya tiene etiqueta permanente, no se modifica."
    ant = "∞" if d["anterior"] == INF else d["anterior"]
    base = f"L({x}) = mín{{{ant}, {L_v} + {w}}}"
    if d["tipo"] == "mejora":
        return f"{base} = {d['candidato']} → se actualiza y su predecesor pasa a ser {v}."
    if d["tipo"] == "empate":
        return f"{base} = {d['candidato']} → empate: {v} se agrega como otro predecesor."
    return f"{base} = {ant} → no mejora, se mantiene."


def etiqueta(L, pred, v, origen):
    """Etiqueta del vértice al estilo del libro: 'pred, L' (o '∞' si aún no se alcanza)."""
    if v == origen:
        return "0"
    if L[v] == INF:
        return "∞"
    return f"{'/'.join(pred[v])}, {L[v]}"
