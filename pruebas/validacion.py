"""Validación del algoritmo propio contra NetworkX.

Para muchos grafos aleatorios y todos los pares (origen, destino) se compara:
  - la distancia mínima,
  - la cantidad de caminos mínimos,
  - el conjunto exacto de caminos mínimos.
NetworkX se usa solo como referencia externa; el programa no depende de él
para resolver el problema.
"""
import random
import sys
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dijkstra import contar_caminos, dijkstra_paso_a_paso, reconstruir_caminos  # noqa: E402
from grafo import INF, crear_grafo, generar_grafo_aleatorio, nombres_vertices  # noqa: E402


def dag_general(n, rng):
    """DAG con un orden topológico sorteado (no alfabético) para probar casos generales."""
    vertices = nombres_vertices(n)
    orden = vertices[:]
    rng.shuffle(orden)
    aristas = [(orden[i], orden[j], rng.randint(1, 6))
               for i in range(n) for j in range(i + 1, n) if rng.random() < 0.3]
    return crear_grafo(vertices, aristas)


def comparar(grafo):
    G = nx.DiGraph()
    G.add_nodes_from(grafo)
    G.add_weighted_edges_from((u, v, w) for u in grafo for v, w in grafo[u].items())
    pares = 0
    for s in grafo:
        for t in grafo:
            if s == t:
                continue
            _, L, pred = dijkstra_paso_a_paso(grafo, s, t)
            if nx.has_path(G, s, t):
                ref = sorted(nx.all_shortest_paths(G, s, t, weight="weight"))
                propios = sorted(reconstruir_caminos(pred, s, t))
                assert L[t] == nx.dijkstra_path_length(G, s, t), (s, t)
                assert contar_caminos(pred, s, t) == len(ref) == len(propios), (s, t)
                assert propios == ref, (s, t)
            else:
                assert L[t] == INF and reconstruir_caminos(pred, s, t) == [], (s, t)
            pares += 1
    return pares


if __name__ == "__main__":
    rng = random.Random(2026)
    grafos = pares = max_caminos = 0
    for prueba in range(300):
        n = rng.randint(7, 16)
        grafo, _ = generar_grafo_aleatorio(n, rng.choice([0.2, 0.35, 0.5, 0.7]),
                                           semilla=prueba)
        pares += comparar(grafo)
        grafos += 1
    for prueba in range(200):
        pares += comparar(dag_general(rng.randint(7, 16), rng))
        grafos += 1
    print(f"Grafos probados: {grafos}")
    print(f"Pares (origen, destino) comparados: {pares}")
    print("Resultado: todas las distancias, cantidades y caminos coinciden con NetworkX.")
