# Camino mínimo con Dijkstra paso a paso

Aplicación web en Python (Streamlit) que resuelve el **problema del camino mínimo** en grafos dirigidos, acíclicos y ponderados con el **algoritmo de Dijkstra**, mostrando cada iteración y **todos** los caminos mínimos entre un origen y un destino.

Proyecto del curso **Matemática Computacional (1AMA0726)**, Universidad Peruana de Ciencias Aplicadas (UPC), Grupo 6.

**App en línea:** https://dijkstra-grupo6.streamlit.app

## Qué hace

1. Pide el número de vértices **n ∈ [7, 16]**.
2. Construye el grafo:
   - **Aleatorio:** con semilla y densidad. Las aristas solo van de una letra a otra posterior, así que nunca hay ciclos.
   - **Manual:** tabla editable de aristas y pesos. Se rechazan lazos, aristas repetidas, pesos no positivos y ciclos (el ciclo encontrado se le muestra al usuario).
3. Dibuja el grafo etiquetado y su matriz de pesos.
4. Ejecuta Dijkstra **paso a paso**: vértice seleccionado, actualización de etiquetas `L(x) = mín{L(x), L(v) + w(v, x)}`, conjunto T de temporales y tabla de etiquetas.
5. **Modo práctica:** antes de cada iteración, el usuario predice qué vértice se fija y qué etiquetas cambian, y la app le indica si acertó.
6. Muestra la **distancia mínima**, la **cantidad de caminos mínimos** y cada camino, resaltados en rojo.
7. Permite **descargar** los caminos y la tabla de iteraciones (CSV) y la imagen del grafo (PNG).

## Estructura

| Archivo | Contenido |
|---|---|
| `app.py` | Interfaz web (Streamlit) y modo práctica |
| `grafo.py` | Generación y validación del grafo (DFS para ciclos, algoritmo de Kahn) |
| `dijkstra.py` | Dijkstra paso a paso, conteo y reconstrucción de todos los caminos mínimos |
| `visualizacion.py` | Dibujo del grafo con NetworkX y Matplotlib |
| `pruebas/validacion.py` | Comparación de resultados con NetworkX (500 grafos, 65 418 pares) |
| `.streamlit/config.toml` | Tema de la app |
| `iniciar.bat` / `iniciar.command` | Abren la app en Windows / Mac con doble clic |

## Ejecutar en la computadora

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

Se abre en el navegador en `http://localhost:8501`. En Windows también se puede usar `iniciar.bat`.

## Validar el algoritmo

```bash
python pruebas/validacion.py
```

## Base teórica

- Johnsonbaugh, R. (2005). *Matemáticas discretas* (6.ª ed.). Pearson Educación. Sección 8.4, algoritmo 8.4.1.
- Dijkstra, E. W. (1959). A note on two problems in connexion with graphs. *Numerische Mathematik, 1*, 269-271.
