"""Interfaz web del proyecto: problema del camino mínimo con el algoritmo de Dijkstra.

Ejecutar con:  streamlit run app.py
"""
import io

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from dijkstra import (contar_caminos, dijkstra_paso_a_paso, etiqueta,
                      reconstruir_caminos, texto_decision)
from grafo import (INF, crear_grafo, encontrar_ciclo, generar_grafo_aleatorio,
                   matriz_pesos, niveles, nombres_vertices, orden_topologico,
                   validar_aristas)
from visualizacion import dibujar_grafo, posiciones

st.set_page_config(page_title="Camino mínimo con Dijkstra", layout="wide")

# Grafo del ejemplo 8.4.2 de Johnsonbaugh (2005, p. 348) con sus aristas orientadas
# para que no haya ciclos. Los vértices a, b, ..., g conservan su letra y z pasa a ser H.
EJEMPLO_LIBRO = [("A", "B", 2), ("A", "F", 1), ("B", "C", 2), ("B", "D", 2),
                 ("B", "E", 4), ("C", "E", 3), ("C", "H", 1), ("D", "E", 4),
                 ("E", "G", 7), ("F", "D", 3), ("F", "G", 5), ("G", "H", 6)]


# ---------------------------------------------------------------- utilidades
def mostrar(fig):
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def reiniciar_ejecucion():
    for clave in ("pasos", "paso", "origen", "destino", "respuestas"):
        st.session_state.pop(clave, None)


def guardar_grafo(grafo, aristas):
    orden = orden_topologico(grafo)
    st.session_state.grafo = grafo
    st.session_state.aristas = aristas
    st.session_state.pos = posiciones(grafo, niveles(grafo, orden))
    reiniciar_ejecucion()


def descartar_grafo():
    for clave in ("grafo", "aristas", "pos"):
        st.session_state.pop(clave, None)
    reiniciar_ejecucion()


def cargar_en_editor(aristas):
    st.session_state.base_manual = pd.DataFrame(aristas, columns=["Origen", "Destino", "Peso"])
    st.session_state.version_editor = st.session_state.get("version_editor", 0) + 1


def tabla_etiquetas(paso, origen):
    filas = []
    for v in paso["L"]:
        filas.append({
            "Vértice": v,
            "L(v)": "∞" if paso["L"][v] == INF else paso["L"][v],
            "Predecesor(es)": ", ".join(paso["pred"][v]) or "—",
            "Estado": "Temporal" if v in paso["temporales"] else "Permanente",
        })
    return pd.DataFrame(filas).astype(str)


def tabla_iteraciones(pasos, origen):
    """Tabla resumen: una fila por iteración y una columna por vértice."""
    filas, fijados = [], set()
    for p in pasos:
        fila = {"Iter.": p["iteracion"], "Selecc.": p["seleccionado"] or "—"}
        for v in p["L"]:
            if v in fijados:
                fila[v] = "—"
            else:
                texto = etiqueta(p["L"], p["pred"], v, origen)
                fila[v] = texto + " *" if v == p["seleccionado"] else texto
        if p["seleccionado"]:
            fijados.add(p["seleccionado"])
        filas.append(fila)
    return pd.DataFrame(filas).astype(str)


def ir_a(indice):
    st.session_state.paso = max(0, min(indice, len(st.session_state.pasos) - 1))


def comprobar(k, correcto_v, correctos_a):
    """Modo práctica: guarda la respuesta del usuario para la iteración k + 1."""
    eleccion = st.session_state.get(f"pv_{k}")
    if eleccion is None:
        st.session_state.aviso_practica = "Elige un vértice antes de comprobar."
        return
    st.session_state.pop("aviso_practica", None)
    actualizados = sorted(st.session_state.get(f"pa_{k}", []))
    st.session_state.respuestas[k] = {
        "vertice": eleccion, "ok_v": eleccion == correcto_v,
        "actualizados": actualizados, "ok_a": actualizados == correctos_a,
    }


def a_csv(df):
    """CSV con ; y BOM para que Excel en español muestre bien tildes y flechas."""
    return df.to_csv(index=False, sep=";").encode("utf-8-sig")


# ---------------------------------------------------------------- encabezado
st.title("Problema del camino mínimo: algoritmo de Dijkstra paso a paso")
st.caption("Matemática Computacional (1AMA0726) · UPC · Grupo 6")

with st.expander("¿Cómo funciona el algoritmo?"):
    st.markdown(
        "Cada vértice *v* tiene una etiqueta **L(v)**. Al inicio L(origen) = 0 y las demás "
        "valen ∞; todas son **temporales**. En cada iteración se elige el vértice temporal "
        "con la menor etiqueta, se vuelve **permanente** y, para cada arista (v, x) que sale "
        "de él, se actualiza  L(x) = mín{L(x), L(v) + w(v, x)}. Cuando el destino recibe "
        "etiqueta permanente, L(destino) es la distancia mínima (Johnsonbaugh, 2005)."
    )
    st.code(
        "dijkstra(w, a, z):\n"
        "    L(a) = 0;  L(x) = ∞ para x ≠ a\n"
        "    T = conjunto de todos los vértices\n"
        "    mientras z ∈ T:\n"
        "        elegir v ∈ T con L(v) mínimo;  T = T − {v}\n"
        "        para cada arista (v, x) con x ∈ T:\n"
        "            si L(v) + w(v, x) < L(x):  L(x) = L(v) + w(v, x);  pred(x) = [v]\n"
        "            si L(v) + w(v, x) = L(x):  agregar v a pred(x)",
        language="text",
    )

# ---------------------------------------------------------------- 1. construcción
st.header("1. Construcción del grafo")
col_conf, col_datos = st.columns([1, 2])

with col_conf:
    n = int(st.number_input("Número de vértices (n ∈ [7, 16])", min_value=7,
                            max_value=16, value=8, step=1))
    if st.session_state.get("n") != n:
        st.session_state.n = n
        st.session_state.pop("base_manual", None)
        descartar_grafo()
    vertices = nombres_vertices(n)
    modo = st.radio("Forma de generar el grafo", ["Aleatoria", "Manual"], horizontal=True)

with col_datos:
    if modo == "Aleatoria":
        c1, c2 = st.columns(2)
        semilla = int(c1.number_input("Semilla", min_value=0, max_value=9999, value=7))
        densidad = c2.slider("Densidad de aristas", 0.10, 0.80, 0.35, 0.05)
        st.caption("Las aristas solo van de una letra a otra posterior, por eso el grafo "
                   "generado nunca tiene ciclos.")
        if st.button("Generar grafo aleatorio", type="primary"):
            guardar_grafo(*generar_grafo_aleatorio(n, densidad, semilla=semilla))
    else:
        st.caption("Agregue una fila por cada arista dirigida (origen → destino) con su peso "
                   "entero positivo.")
        b1, b2 = st.columns(2)
        if b1.button("Cargar ejemplo del libro (n = 8)", disabled=(n != 8)):
            cargar_en_editor(EJEMPLO_LIBRO)
        if b2.button("Editar el grafo actual", disabled="aristas" not in st.session_state):
            cargar_en_editor(st.session_state.aristas)
        base = st.session_state.get(
            "base_manual", pd.DataFrame({"Origen": pd.Series(dtype="str"),
                                         "Destino": pd.Series(dtype="str"),
                                         "Peso": pd.Series(dtype="float")}))
        tabla = st.data_editor(
            base, num_rows="dynamic", hide_index=True, height=470,
            key=f"editor_{n}_{st.session_state.get('version_editor', 0)}",
            column_config={
                "Origen": st.column_config.SelectboxColumn(options=vertices, required=True),
                "Destino": st.column_config.SelectboxColumn(options=vertices, required=True),
                "Peso": st.column_config.NumberColumn(min_value=1, step=1, required=True),
            })
        if st.button("Construir grafo", type="primary"):
            filas = list(tabla.itertuples(index=False, name=None))
            aristas, errores = validar_aristas(vertices, filas)
            if not errores and not aristas:
                errores = ["Ingrese al menos una arista."]
            if errores:
                descartar_grafo()
                for error in errores:
                    st.error(error)
            else:
                grafo = crear_grafo(vertices, aristas)
                ciclo = encontrar_ciclo(grafo)
                if ciclo:
                    descartar_grafo()
                    st.error("El grafo tiene el ciclo " + " → ".join(ciclo) +
                             ". El proyecto exige un grafo sin ciclos: elimine o invierta "
                             "una de esas aristas y vuelva a construirlo.")
                else:
                    guardar_grafo(grafo, aristas)
                    st.success(f"Grafo válido: {n} vértices, {len(aristas)} aristas, sin ciclos.")

if "grafo" not in st.session_state:
    st.info("Genere o ingrese un grafo para continuar.")
    st.stop()

grafo, pos = st.session_state.grafo, st.session_state.pos

# ---------------------------------------------------------------- 2. grafo
st.header("2. Grafo dirigido ponderado")
m = sum(len(a) for a in grafo.values())
st.write(f"**{len(grafo)} vértices** y **{m} aristas**. El grafo es dirigido y no tiene ciclos.")
mostrar(dibujar_grafo(grafo, pos, titulo="Representación gráfica etiquetada"))
with st.expander("Ver matriz de pesos"):
    st.dataframe(pd.DataFrame(matriz_pesos(grafo), index=list(grafo),
                              columns=list(grafo)).astype(str))

# ---------------------------------------------------------------- 3. origen y destino
st.header("3. Selección de origen y destino")
c1, c2, c3 = st.columns([1, 1, 1])
origen = c1.selectbox("Vértice origen", vertices, index=0)
destino = c2.selectbox("Vértice destino", vertices, index=len(vertices) - 1)
c3.write("")
if c3.button("Ejecutar Dijkstra", type="primary", disabled=(origen == destino)):
    pasos, _, _ = dijkstra_paso_a_paso(grafo, origen, destino)
    st.session_state.update(pasos=pasos, paso=0, origen=origen, destino=destino, respuestas={})
if origen == destino:
    st.warning("El origen y el destino deben ser distintos.")

if "pasos" not in st.session_state:
    st.stop()

pasos = st.session_state.pasos
origen, destino = st.session_state.origen, st.session_state.destino
k = st.session_state.paso
paso = pasos[k]
ultimo = len(pasos) - 1

# ---------------------------------------------------------------- 4. paso a paso
st.header("4. Ejecución paso a paso")
respuestas = st.session_state.setdefault("respuestas", {})
practica = st.toggle("Modo práctica: predice cada iteración antes de verla", key="practica",
                     help="Antes de avanzar, elige qué vértice se fija y qué etiquetas cambian. "
                          "El botón Siguiente se habilita cuando compruebas tu respuesta.")
bloqueado = practica and k < ultimo and k not in respuestas
b1, b2, b3, b4 = st.columns(4)
b1.button("⏮ Reiniciar", on_click=ir_a, args=(0,), width="stretch")
b2.button("◀ Anterior", on_click=ir_a, args=(k - 1,), disabled=k == 0, width="stretch")
b3.button("Siguiente ▶", on_click=ir_a, args=(k + 1,), disabled=k == ultimo or bloqueado,
          width="stretch")
b4.button("Ver solución ⏭", on_click=ir_a, args=(ultimo,), disabled=k == ultimo or practica,
          width="stretch")
st.progress(k / ultimo if ultimo else 1.0, text=f"Iteración {k} de {ultimo}")

col_fig, col_txt = st.columns([3, 2])
with col_fig:
    titulo = "Inicialización" if k == 0 else f"Iteración {k}: se fija el vértice {paso['seleccionado']}"
    mostrar(dibujar_grafo(grafo, pos, paso=paso, origen=origen, destino=destino, titulo=titulo))
with col_txt:
    if k == 0:
        st.markdown(f"**Inicialización.** L({origen}) = 0 y L(x) = ∞ para los demás vértices. "
                    "Todas las etiquetas son temporales.")
    else:
        v = paso["seleccionado"]
        L_v = paso["L"][v]
        st.markdown(f"**Selección.** Entre los vértices temporales, **{v}** tiene la menor "
                    f"etiqueta (L({v}) = {L_v}); su etiqueta pasa a ser **permanente**.")
        if paso["decisiones"]:
            st.markdown("**Actualización de etiquetas:**")
            for d in paso["decisiones"]:
                st.markdown("- " + texto_decision(v, L_v, d))
        else:
            st.markdown(f"No salen aristas de {v}; no se actualiza ninguna etiqueta.")
    temporales = ", ".join(sorted(paso["temporales"])) or "∅"
    st.markdown(f"**T (temporales)** = {{{temporales}}}")
    if k == ultimo:
        if paso["L"][destino] == INF or destino in paso["temporales"]:
            st.error(f"No quedan vértices alcanzables: no existe camino de {origen} a {destino}.")
        else:
            st.success(f"{destino} recibió etiqueta permanente: el algoritmo termina.")
    st.dataframe(tabla_etiquetas(paso, origen), hide_index=True,
                 height=35 * (len(grafo) + 1) + 3)

# ---------------------------------------------------------------- modo práctica
if practica and k < ultimo:
    sig = pasos[k + 1]
    candidatos = sorted(paso["temporales"])
    correcto_v = sig["seleccionado"]
    correctos_a = sorted(d["x"] for d in sig["decisiones"] if d["tipo"] in ("mejora", "empate"))
    st.subheader(f"Desafío: ¿qué pasará en la iteración {k + 1}?")
    with st.form(f"desafio_{k}"):
        st.radio("1. ¿Qué vértice se vuelve permanente?", candidatos, index=None,
                 horizontal=True, key=f"pv_{k}")
        st.multiselect("2. ¿Qué vértices cambian su etiqueta (mejora o empate)? "
                       "Déjalo vacío si crees que ninguno.", candidatos, key=f"pa_{k}",
                       placeholder="Elige uno o más vértices")
        st.form_submit_button("Comprobar", type="primary", on_click=comprobar,
                              args=(k, correcto_v, correctos_a))
    if "aviso_practica" in st.session_state and k not in respuestas:
        st.warning(st.session_state.aviso_practica)
    if k in respuestas:
        r = respuestas[k]
        L_min = paso["L"][correcto_v]
        empatados = [x for x in candidatos if paso["L"][x] == L_min]
        nota_empate = (f" Empata con {', '.join(e for e in empatados if e != correcto_v)}; "
                       "se elige la letra menor." if len(empatados) > 1 else "")
        if r["ok_v"]:
            st.success(f"Correcto: {correcto_v} tiene la menor etiqueta temporal "
                       f"(L = {L_min}).{nota_empate}")
        else:
            st.error(f"Era {correcto_v}: tiene la menor etiqueta temporal (L = {L_min})."
                     f"{nota_empate}")
        cambian = ", ".join(correctos_a) or "ninguno"
        if r["ok_a"]:
            st.success(f"Correcto: cambian {cambian}.")
        else:
            st.error(f"Cambian: {cambian}. Pulsa Siguiente para ver cada cálculo.")
if practica and respuestas:
    aciertos = sum(r["ok_v"] + r["ok_a"] for r in respuestas.values())
    st.caption(f"Puntaje del modo práctica: {aciertos} de {2 * len(respuestas)} respuestas correctas.")

# ---------------------------------------------------------------- 5. solución
if k == ultimo:
    st.header("5. Solución")
    L_final, pred_final = paso["L"], paso["pred"]
    if L_final[destino] == INF:
        st.error(f"No existe ningún camino dirigido de {origen} a {destino}.")
    else:
        caminos = reconstruir_caminos(pred_final, origen, destino)
        total = contar_caminos(pred_final, origen, destino)
        c1, c2 = st.columns(2)
        c1.metric(f"Distancia mínima de {origen} a {destino}", L_final[destino])
        c2.metric("Cantidad de caminos mínimos", total)
        for i, c in enumerate(caminos, start=1):
            pesos = [grafo[a][b] for a, b in zip(c, c[1:])]
            st.markdown(f"**Camino {i}:** {' → '.join(c)}  "
                        f"({' + '.join(map(str, pesos))} = {sum(pesos)})")
        opciones = ["Todos"] + [f"Camino {i}" for i in range(1, len(caminos) + 1)]
        elegido = st.selectbox("Resaltar sobre el grafo", opciones)
        marcados = caminos if elegido == "Todos" else [caminos[opciones.index(elegido) - 1]]
        fig = dibujar_grafo(grafo, pos, origen=origen, destino=destino, caminos=marcados,
                            titulo=f"Camino(s) mínimo(s) de {origen} a {destino}")
        imagen = io.BytesIO()
        fig.savefig(imagen, format="png", dpi=200, bbox_inches="tight")
        mostrar(fig)
        df_caminos = pd.DataFrame([{
            "Camino": i, "Secuencia": " → ".join(c),
            "Pesos": " + ".join(str(grafo[a][b]) for a, b in zip(c, c[1:])),
            "Longitud": sum(grafo[a][b] for a, b in zip(c, c[1:])),
        } for i, c in enumerate(caminos, start=1)])
        d1, d2 = st.columns(2)
        d1.download_button("Descargar caminos (CSV)", a_csv(df_caminos),
                           file_name=f"caminos_{origen}_{destino}.csv", mime="text/csv",
                           on_click="ignore", width="stretch")
        d2.download_button("Descargar imagen del grafo (PNG)", imagen.getvalue(),
                           file_name=f"grafo_{origen}_{destino}.png", mime="image/png",
                           on_click="ignore", width="stretch")
    with st.expander("Tabla resumen de iteraciones", expanded=True):
        st.caption("Cada celda muestra 'predecesor, L(v)'. El asterisco indica que en esa "
                   "iteración la etiqueta se volvió permanente; el guion, que ya lo era.")
        tabla = tabla_iteraciones(pasos, origen)
        st.dataframe(tabla, hide_index=True, height=35 * (len(pasos) + 1) + 3)
        st.download_button("Descargar tabla de iteraciones (CSV)", a_csv(tabla),
                           file_name=f"iteraciones_{origen}_{destino}.csv", mime="text/csv",
                           on_click="ignore")
