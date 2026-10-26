# Camino mínimo con Dijkstra paso a paso

Aplicación web en Python (Streamlit) que resuelve el **problema del camino mínimo** en grafos dirigidos, acíclicos y ponderados con el **algoritmo de Dijkstra**, mostrando cada iteración y **todos** los caminos mínimos entre un origen y un destino.

Proyecto del curso **Matemática Computacional (1AMA0726)**, Universidad Peruana de Ciencias Aplicadas (UPC), Grupo 6.

**App en línea:** https://dijkstra-grupo6.streamlit.app

## Qué hace

1. Pide el número de vértices **n ∈ [7, 16]**.
2. Construye el grafo:
   - **Aleatorio:** con semilla y densidad. Las aristas solo van de una letra a otra posterior, así que nunca hay ciclos.
   - **Manual:** tabla editable de aristas y pesos. Se rechazan lazos, aristas repetidas, pesos no positivos y ciclos (el ciclo encontrado se le muestra al usuario).
   - **Desde CSV:** en el modo Manual se puede cargar un archivo con columnas Origen, Destino y Peso (separadas por `;` o `,`), que se valida igual que la tabla. Si usa vértices fuera de A..n, la app indica qué n se necesita.
   - El grafo construido se puede **descargar en CSV** (`Origen;Destino;Peso`) para volver a cargarlo después.
3. Dibuja el grafo etiquetado en un **gráfico interactivo** (Plotly) y muestra su matriz de pesos:
   - al pasar el cursor por un vértice se ven sus aristas de salida y de llegada (o, durante la ejecución, L(v), su estado y sus predecesores);
   - al pasar el cursor por un peso se ve w(u, x) y, si la arista se revisó en esa iteración, el cálculo de la etiqueta;
   - con un **clic en un vértice** se elige el origen y luego el destino (los marca con borde grueso);
   - se puede acercar, desplazar y guardar la imagen desde la barra del gráfico.
4. Ejecuta Dijkstra **paso a paso**: vértice seleccionado, actualización de etiquetas `L(x) = mín{L(x), L(v) + w(v, x)}`, conjunto T de temporales y tabla de etiquetas.
5. **Animación:** la pestaña "▶ Animación" recorre todas las iteraciones con Play/Pausa o con un deslizador y termina en un cuadro con el camino mínimo en rojo.
6. **Modo práctica:** antes de cada iteración, el usuario predice qué vértice se fija y qué etiquetas cambian, y la app le indica si acertó (mientras está activo, la animación se oculta).
7. Muestra la **distancia mínima**, la **cantidad de caminos mínimos** y cada camino, resaltados en rojo.
8. Permite **descargar** los caminos y la tabla de iteraciones (CSV), la imagen del grafo (PNG, hecha con Matplotlib para el informe y siempre en tema claro) y **todo en un Excel** con las hojas Resumen, Aristas, Matriz de pesos, Iteraciones, Etiquetas y Caminos. Los nombres de archivo llevan el origen, el destino y, si el grafo es aleatorio, la semilla.
9. **Complejidad:** cuenta, por iteración, las comparaciones para elegir el mínimo (|T| − 1) y las aristas revisadas, y compara el total con n² (teorema 8.4.5 de Johnsonbaugh, Θ(n²)).
10. **Modo oscuro:** en el menú ⋮ (arriba a la derecha) se elige el tema claro, el oscuro o el del sistema; los gráficos interactivos cambian de paleta en unos 2 segundos.

## Estructura

| Archivo | Contenido |
|---|---|
| `app.py` | Interfaz web (Streamlit) y modo práctica |
| `grafo.py` | Generación y validación del grafo (DFS para ciclos, algoritmo de Kahn) |
| `dijkstra.py` | Dijkstra paso a paso, conteo y reconstrucción de todos los caminos mínimos |
| `grafico_interactivo.py` | Gráficos interactivos con Plotly: hover, clic en los vértices, animación de Dijkstra y paletas clara y oscura |
| `reportes.py` | Carga del grafo desde CSV, libro Excel de la solución y conteo de operaciones |
| `visualizacion.py` | Colores, posiciones y curvatura de las aristas; dibujo con NetworkX y Matplotlib para la imagen PNG |
| `pruebas/validacion.py` | Comparación de resultados con NetworkX (500 grafos, 65 418 pares) |
| `.streamlit/config.toml` | Temas claro y oscuro de la app |
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
