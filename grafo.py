"""Construcción y validación del grafo dirigido ponderado.

El enunciado del proyecto pide un grafo dirigido, sin ciclos y con pesos
en las aristas. En este módulo se genera ese grafo (de forma aleatoria o a
partir de los datos del usuario) y se comprueba que cumpla las condiciones.
"""
import random
import string

INF = float("inf")


def nombres_vertices(n):
    """Devuelve las etiquetas A, B, C, ... para n vértices."""
    return list(string.ascii_uppercase[:n])


def crear_grafo(vertices, aristas):
    """Arma la lista de adyacencia {u: {v: peso}} a partir de (u, v, peso)."""
    grafo = {v: {} for v in vertices}
    for u, v, w in aristas:
        grafo[u][v] = w
    return grafo


def generar_grafo_aleatorio(n, densidad=0.35, peso_max=9, semilla=None):
    """Genera un grafo dirigido acíclico (DAG) de n vértices.

    Las aristas solo van de una letra anterior a una posterior (por ejemplo
    B -> E, nunca E -> B), por lo que es imposible cerrar un ciclo. Cada
    vértice, salvo A, recibe al menos una arista de alguno de los tres
    vértices anteriores; así todo el grafo es alcanzable desde A.
    """
    rng = random.Random(semilla)
    vertices = nombres_vertices(n)
    aristas = {}
    for i in range(1, n):
        # arista obligatoria para que el grafo no quede desconectado
        j = rng.randrange(max(0, i - 3), i)
        aristas[(vertices[j], vertices[i])] = rng.randint(1, peso_max)
        # aristas adicionales hacia vértices cercanos según la densidad
        for j in range(max(0, i - 4), i):
            par = (vertices[j], vertices[i])
            if par not in aristas and rng.random() < densidad:
                aristas[par] = rng.randint(1, peso_max)
    lista = [(u, v, w) for (u, v), w in sorted(aristas.items())]
    return crear_grafo(vertices, lista), lista


def validar_aristas(vertices, filas):
    """Revisa las aristas ingresadas a mano.

    Devuelve (aristas_validas, errores). Se rechazan filas incompletas,
    lazos, aristas repetidas y pesos que no sean enteros positivos.
    """
    aristas, errores, vistas = [], [], set()
    for k, (u, v, w) in enumerate(filas, start=1):
        if not u or not v or w is None or w != w:  # w != w detecta NaN
            errores.append(f"Fila {k}: faltan datos (origen, destino o peso).")
            continue
        if u not in vertices or v not in vertices:
            errores.append(f"Fila {k}: el vértice {u if u not in vertices else v} no existe.")
            continue
        if u == v:
            errores.append(f"Fila {k}: ({u}, {v}) es un lazo; no está permitido.")
            continue
        if (u, v) in vistas:
            errores.append(f"Fila {k}: la arista ({u}, {v}) está repetida.")
            continue
        if float(w) != int(w) or int(w) <= 0:
            errores.append(f"Fila {k}: el peso de ({u}, {v}) debe ser un entero positivo.")
            continue
        vistas.add((u, v))
        aristas.append((u, v, int(w)))
    return aristas, errores


def orden_topologico(grafo):
    """Algoritmo de Kahn: devuelve un orden topológico o None si hay ciclo."""
    grado_entrada = {v: 0 for v in grafo}
    for u in grafo:
        for v in grafo[u]:
            grado_entrada[v] += 1
    cola = sorted(v for v in grafo if grado_entrada[v] == 0)
    orden = []
    while cola:
        u = cola.pop(0)
        orden.append(u)
        for v in sorted(grafo[u]):
            grado_entrada[v] -= 1
            if grado_entrada[v] == 0:
                cola.append(v)
    return orden if len(orden) == len(grafo) else None


def encontrar_ciclo(grafo):
    """Busca un ciclo con DFS para mostrárselo al usuario (A -> B -> C -> A)."""
    estado = {v: "nuevo" for v in grafo}
    camino = []

    def dfs(u):
        estado[u] = "en_camino"
        camino.append(u)
        for v in sorted(grafo[u]):
            if estado[v] == "en_camino":
                return camino[camino.index(v):] + [v]
            if estado[v] == "nuevo":
                ciclo = dfs(v)
                if ciclo:
                    return ciclo
        camino.pop()
        estado[u] = "terminado"
        return None

    for v in sorted(grafo):
        if estado[v] == "nuevo":
            ciclo = dfs(v)
            if ciclo:
                return ciclo
    return None


def niveles(grafo, orden):
    """Nivel de cada vértice (camino más largo desde una fuente); sirve para dibujar."""
    nivel = {v: 0 for v in grafo}
    for u in orden:
        for v in grafo[u]:
            nivel[v] = max(nivel[v], nivel[u] + 1)
    return nivel


def matriz_pesos(grafo):
    """Matriz de pesos: w(u, v) si existe la arista y '—' si no existe."""
    vertices = list(grafo)
    return [[grafo[u][v] if v in grafo[u] else "—" for v in vertices] for u in vertices]
