"""Interfaz web del proyecto: problema del camino mínimo con el algoritmo de Dijkstra.

Ejecutar con:  streamlit run app.py
"""
import io
import string
from functools import partial

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from dijkstra import (contar_caminos, dijkstra_paso_a_paso, etiqueta,
                      reconstruir_caminos, texto_decision)
from grafico_interactivo import CONFIG, animacion, figura_grafo
from grafo import (INF, crear_grafo, encontrar_ciclo, generar_grafo_aleatorio,
                   matriz_pesos, niveles, nombres_vertices, orden_topologico,
                   validar_aristas)
from reportes import (leer_csv_grafo, libro_excel, n_necesario, tabla_etiquetas_larga,
                      tabla_operaciones)
from visualizacion import dibujar_grafo, posiciones

st.set_page_config(page_title="Camino mínimo con Dijkstra", layout="wide")
# tema elegido en el menú ⋮; los gráficos de Plotly usan la paleta que corresponde
tema = st.context.theme.type or "light"


@st.fragment(run_every=2)
def vigilar_tema():
    """El menú ⋮ cambia el tema sin volver a ejecutar la app; si cambió, se redibuja todo."""
    if (st.context.theme.type or "light") != tema:
        st.rerun()


vigilar_tema()

# Grafo del ejemplo 8.4.2 de Johnsonbaugh (2005, p. 348) con sus aristas orientadas
# para que no haya ciclos. Los vértices a, b, ..., g conservan su letra y z pasa a ser H.
EJEMPLO_LIBRO = [("A", "B", 2), ("A", "F", 1), ("B", "C", 2), ("B", "D", 2),
                 ("B", "E", 4), ("C", "E", 3), ("C", "H", 1), ("D", "E", 4),
                 ("E", "G", 7), ("F", "D", 3), ("F", "G", 5), ("G", "H", 6)]


# ---------------------------------------------------------------- utilidades
def mostrar(fig, key, **kwargs):
    st.plotly_chart(fig, key=key, theme=None, width="stretch", config=CONFIG, **kwargs)


def marcar_vertice(clave):
    """Clic en el gráfico de la sección 2: marca el vértice como origen o destino."""
    puntos = st.session_state[clave]["selection"]["points"]
    letras = [p["customdata"][1] for p in puntos if (p.get("customdata") or [None])[0] == "v"]
    if letras:
        if st.session_state.get("modo_clic", "Origen") == "Origen":
            st.session_state.sel_origen = letras[0]
            st.session_state.modo_clic = "Destino"
        else:
            st.session_state.sel_destino = letras[0]
    # con otro key el gráfico se vuelve a dibujar sin el punto seleccionado
    st.session_state.clics = st.session_state.get("clics", 0) + 1


@st.cache_data(show_spinner="Preparando la animación…", max_entries=20)
def animacion_cacheada(aristas, n, origen, destino, tema):
    """La animación tarda 1 a 2 s con 16 vértices; se guarda por grafo, origen, destino y tema."""
    grafo = crear_grafo(nombres_vertices(n), aristas)
    pos = posiciones(grafo, niveles(grafo, orden_topologico(grafo)))
    pasos, L, pred = dijkstra_paso_a_paso(grafo, origen, destino)
    caminos = reconstruir_caminos(pred, origen, destino) if L[destino] != INF else None
    return animacion(grafo, pos, pasos, origen, destino, caminos, tema=tema)


def reiniciar_ejecucion():
    for clave in ("pasos", "paso", "origen", "destino", "respuestas"):
        st.session_state.pop(clave, None)


def guardar_grafo(grafo, aristas, info=None):
    """info -> cómo se generó el grafo (modo y, si es aleatorio, semilla y densidad)."""
    orden = orden_topologico(grafo)
    st.session_state.grafo = grafo
    st.session_state.aristas = aristas
    st.session_state.pos = posiciones(grafo, niveles(grafo, orden))
    st.session_state.info_grafo = info or {"modo": "Manual"}
    reiniciar_ejecucion()


def descartar_grafo():
    for clave in ("grafo", "aristas", "pos", "info_grafo"):
        st.session_state.pop(clave, None)
    reiniciar_ejecucion()


def sufijo_archivo():
    """'_semilla7' si el grafo es aleatorio, para nombrar los archivos descargados."""
    info = st.session_state.get("info_grafo", {})
    return f"_semilla{info['semilla']}" if info.get("modo") == "Aleatoria" else ""


def cargar_en_editor(aristas):
    st.session_state.base_manual = pd.DataFrame(aristas, columns=["Origen", "Destino", "Peso"])
    st.session_state.version_editor = st.session_state.get("version_editor", 0) + 1


def mensaje_ciclo(ciclo):
    return ("El grafo tiene el ciclo " + " → ".join(ciclo) + ". El proyecto exige un grafo "
            "sin ciclos: elimine o invierta una de esas aristas y vuelva a construirlo.")


def cargar_csv(clave, n):
    """Lee el CSV subido, lo valida como la tabla manual y lo carga en el editor."""
    archivo = st.session_state.get(clave)
    if archivo is None:
        return
    avisos = st.session_state.avisos_csv = []
    filas, error = leer_csv_grafo(archivo.getvalue())
    if error:
        avisos.append(("error", error))
        return
    necesario = n_necesario(filas)
    if necesario > n:
        letra = string.ascii_uppercase[necesario - 1]
        if necesario <= 16:
            avisos.append(("error", f"El archivo usa vértices hasta {letra}: elija n = "
                                    f"{necesario} (o más) y vuelva a cargarlo."))
        else:
            avisos.append(("error", f"El archivo usa el vértice {letra}, pero la app admite "
                                    "como máximo 16 vértices (A a P)."))
    vertices = nombres_vertices(n)
    aristas, errores = validar_aristas(vertices, filas)
    if not errores and not aristas:
        errores = ["El archivo no tiene aristas."]
    if errores or necesario > n:
        avisos.extend(("error", e) for e in errores)
        return
    # con un ciclo también se carga, para poder corregirlo en la tabla
    cargar_en_editor(aristas)
    ciclo = encontrar_ciclo(crear_grafo(vertices, aristas))
    if ciclo:
        avisos.append(("error", mensaje_ciclo(ciclo)))
    else:
        avisos.append(("success", f"Se cargaron {len(aristas)} aristas en la tabla. "
                                  "Revíselas y pulse Construir grafo."))


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
st.caption("Modo oscuro: menú ⋮ (arriba a la derecha) → ícono de la luna; el de contraste "
           "sigue el tema del sistema.")

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
        for clave in ("base_manual", "sel_origen", "sel_destino"):
            st.session_state.pop(clave, None)
        descartar_grafo()
    vertices = nombres_vertices(n)
    modo = st.radio("Forma de generar el grafo", ["Aleatoria", "Manual"], horizontal=True)
    zona_csv = st.empty()   # el botón de descarga se llena al final, con el grafo ya construido

with col_datos:
    if modo == "Aleatoria":
        c1, c2 = st.columns(2)
        semilla = int(c1.number_input("Semilla", min_value=0, max_value=9999, value=7))
        densidad = c2.slider("Densidad de aristas", 0.10, 0.80, 0.35, 0.05)
        st.caption("Las aristas solo van de una letra a otra posterior, por eso el grafo "
                   "generado nunca tiene ciclos.")
        if st.button("Generar grafo aleatorio", type="primary"):
            guardar_grafo(*generar_grafo_aleatorio(n, densidad, semilla=semilla),
                          info={"modo": "Aleatoria", "semilla": semilla, "densidad": densidad})
    else:
        st.caption("Agregue una fila por cada arista dirigida (origen → destino) con su peso "
                   "entero positivo.")
        b1, b2 = st.columns(2)
        if b1.button("Cargar ejemplo del libro (n = 8)", disabled=(n != 8)):
            cargar_en_editor(EJEMPLO_LIBRO)
        if b2.button("Editar el grafo actual", disabled="aristas" not in st.session_state):
            cargar_en_editor(st.session_state.aristas)
        clave_csv = f"csv_{n}"
        st.file_uploader("Cargar grafo desde CSV", type="csv", key=clave_csv,
                         on_change=cargar_csv, args=(clave_csv, n),
                         help="Columnas Origen, Destino y Peso, separadas por ; o por ,. "
                              "Es el mismo formato de «Descargar grafo (CSV)».")
        for tipo, texto in st.session_state.pop("avisos_csv", []):
            getattr(st, tipo)(texto)
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
                    st.error(mensaje_ciclo(ciclo))
                else:
                    guardar_grafo(grafo, aristas)
                    st.success(f"Grafo válido: {n} vértices, {len(aristas)} aristas, sin ciclos.")

if "aristas" in st.session_state:
    zona_csv.download_button(
        "Descargar grafo (CSV)",
        a_csv(pd.DataFrame(st.session_state.aristas, columns=["Origen", "Destino", "Peso"])),
        file_name=f"grafo_n{n}{sufijo_archivo()}.csv", mime="text/csv", on_click="ignore",
        help="Origen;Destino;Peso. Se puede volver a cargar en el modo Manual.")

if "grafo" not in st.session_state:
    st.info("Genere o ingrese un grafo para continuar.")
    st.stop()

grafo, pos = st.session_state.grafo, st.session_state.pos

# ---------------------------------------------------------------- 2. grafo
st.header("2. Grafo dirigido ponderado")
m = sum(len(a) for a in grafo.values())
st.write(f"**{len(grafo)} vértices** y **{m} aristas**. El grafo es dirigido y no tiene ciclos.")
if st.session_state.get("sel_origen") not in vertices:
    st.session_state.sel_origen = vertices[0]
if st.session_state.get("sel_destino") not in vertices:
    st.session_state.sel_destino = vertices[-1]
st.radio("Al hacer clic en un vértice, marcarlo como:", ["Origen", "Destino"],
         horizontal=True, key="modo_clic",
         help="Pase el cursor por un vértice o un peso para ver sus datos.")
clave_grafo = f"grafo_{tema}_{st.session_state.get('clics', 0)}"
mostrar(figura_grafo(grafo, pos, origen=st.session_state.sel_origen,
                     destino=st.session_state.sel_destino,
                     titulo="Representación gráfica etiquetada", tema=tema),
        key=clave_grafo, on_select=partial(marcar_vertice, clave_grafo),
        selection_mode="points")
with st.expander("Ver matriz de pesos"):
    st.dataframe(pd.DataFrame(matriz_pesos(grafo), index=list(grafo),
                              columns=list(grafo)).astype(str))

# ---------------------------------------------------------------- 3. origen y destino
st.header("3. Selección de origen y destino")
c1, c2, c3 = st.columns([1, 1, 1])
origen = c1.selectbox("Vértice origen", vertices, key="sel_origen")
destino = c2.selectbox("Vértice destino", vertices, key="sel_destino")
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
tab_paso, tab_animacion = st.tabs(["Paso a paso", "▶ Animación"], key="pestana",
                                  on_change="rerun")
with tab_paso:
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
        titulo = ("Inicialización" if k == 0 else
                  f"Iteración {k}: se fija el vértice {paso['seleccionado']}")
        mostrar(figura_grafo(grafo, pos, paso=paso, origen=origen, destino=destino,
                             titulo=titulo, tema=tema), key=f"grafo_paso_{tema}")
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

    # ------------------------------------------------------------ modo práctica
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

with tab_animacion:
    if practica:
        st.info("La animación se oculta en el modo práctica porque revelaría las respuestas. "
                "Desactívalo para verla.")
    elif tab_animacion.open:
        st.caption("Use ▶ Play para recorrer las iteraciones o mueva el deslizador. "
                   "El último cuadro muestra la solución.")
        aristas = tuple(map(tuple, st.session_state.aristas))
        mostrar(animacion_cacheada(aristas, len(grafo), origen, destino, tema),
                key=f"animacion_{tema}")

# ---------------------------------------------------------------- 5. solución
if k == ultimo:
    st.header("5. Solución")
    L_final, pred_final = paso["L"], paso["pred"]
    nombre = f"{origen}_{destino}{sufijo_archivo()}"   # parte común de los archivos
    caminos, total = [], 0
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
        titulo = f"Camino(s) mínimo(s) de {origen} a {destino}"
        mostrar(figura_grafo(grafo, pos, origen=origen, destino=destino, caminos=marcados,
                             titulo=titulo, tema=tema), key=f"grafo_solucion_{tema}")
        # la imagen PNG para el informe se sigue haciendo con Matplotlib (siempre en claro)
        fig = dibujar_grafo(grafo, pos, origen=origen, destino=destino, caminos=marcados,
                            titulo=titulo)
        imagen = io.BytesIO()
        fig.savefig(imagen, format="png", dpi=200, bbox_inches="tight")
        plt.close(fig)
    df_caminos = pd.DataFrame([{
        "Camino": i, "Secuencia": " → ".join(c),
        "Pesos": " + ".join(str(grafo[a][b]) for a, b in zip(c, c[1:])),
        "Longitud": sum(grafo[a][b] for a, b in zip(c, c[1:])),
    } for i, c in enumerate(caminos, start=1)])
    if caminos:
        d1, d2 = st.columns(2)
        d1.download_button("Descargar caminos (CSV)", a_csv(df_caminos),
                           file_name=f"caminos_{nombre}.csv", mime="text/csv",
                           on_click="ignore", width="stretch")
        d2.download_button("Descargar imagen del grafo (PNG)", imagen.getvalue(),
                           file_name=f"grafo_{nombre}.png", mime="image/png",
                           on_click="ignore", width="stretch")

    tabla = tabla_iteraciones(pasos, origen)
    info = st.session_state.get("info_grafo", {"modo": "Manual"})
    resumen = [("Número de vértices (n)", len(grafo)), ("Número de aristas (m)", m),
               ("Origen", origen), ("Destino", destino),
               ("Distancia mínima", L_final[destino] if caminos else "No existe camino"),
               ("Cantidad de caminos mínimos", total), ("Forma de generar el grafo", info["modo"])]
    if info["modo"] == "Aleatoria":
        resumen += [("Semilla", info["semilla"]), ("Densidad de aristas", info["densidad"])]
    matriz = pd.DataFrame(matriz_pesos(grafo), index=list(grafo), columns=list(grafo))
    excel = libro_excel({
        "Resumen": pd.DataFrame(resumen, columns=["Dato", "Valor"]),
        "Aristas": pd.DataFrame(st.session_state.aristas, columns=["Origen", "Destino", "Peso"]),
        "Matriz de pesos": matriz.rename_axis("Vértice").reset_index(),
        "Iteraciones": tabla,
        "Etiquetas": tabla_etiquetas_larga(pasos),
        "Caminos": df_caminos if caminos else pd.DataFrame(
            {"Nota": [f"No existe ningún camino dirigido de {origen} a {destino}."]}),
    })
    st.download_button("Descargar todo (Excel)", excel, file_name=f"dijkstra_{nombre}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       on_click="ignore", type="primary",
                       help="Resumen, aristas, matriz de pesos, iteraciones, etiquetas y caminos.")

    with st.expander("Tabla resumen de iteraciones", expanded=True):
        st.caption("Cada celda muestra 'predecesor, L(v)'. El asterisco indica que en esa "
                   "iteración la etiqueta se volvió permanente; el guion, que ya lo era.")
        st.dataframe(tabla, hide_index=True, height=35 * (len(pasos) + 1) + 3)
        st.download_button("Descargar tabla de iteraciones (CSV)", a_csv(tabla),
                           file_name=f"iteraciones_{nombre}.csv", mime="text/csv",
                           on_click="ignore")

    with st.expander("Complejidad"):
        ops = tabla_operaciones(pasos)
        comparaciones = int(ops["Comparaciones (|T| − 1)"].sum())
        revisadas = int(ops["Aristas revisadas"].sum())
        total_ops, n2 = comparaciones + revisadas, len(grafo) ** 2
        fila_total = {"Iteración": "Total", "Seleccionado": "", "|T|": "",
                      "Comparaciones (|T| − 1)": comparaciones,
                      "Aristas revisadas": revisadas, "Operaciones": total_ops}
        st.dataframe(pd.concat([ops, pd.DataFrame([fila_total])]).astype(str),
                     hide_index=True, height=35 * (len(ops) + 2) + 3)
        st.markdown(
            f"En esta ejecución se hicieron **{total_ops} operaciones** ({comparaciones} "
            f"comparaciones para elegir el mínimo y {revisadas} aristas revisadas), el "
            f"{100 * total_ops / n2:.0f} % de n² = {len(grafo)}² = {n2}. Según el teorema 8.4.5 "
            "de Johnsonbaugh (2005), el algoritmo de Dijkstra es **Θ(n²)** en el peor caso: "
            "elegir el mínimo cuesta hasta n − 1 comparaciones en cada una de las hasta n "
            "iteraciones. Aquí el total es menor porque T se reduce en cada iteración, solo se "
            "revisan las aristas que salen del vértice elegido y el algoritmo se detiene cuando "
            "el destino recibe etiqueta permanente (o cuando no quedan vértices alcanzables).")
