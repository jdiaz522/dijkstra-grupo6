"""Archivos y tablas de resultados: carga del grafo desde CSV, libro Excel y conteo de operaciones."""
import io
import string
import unicodedata

import pandas as pd
from openpyxl.styles import Font

from grafo import INF

TIPOS = {"mejora": "Mejora", "empate": "Empate", "sin_cambio": "Sin cambio",
         "permanente": "Ya era permanente"}


def _normalizar(texto):
    """Minúsculas y sin tildes, para reconocer 'Orígen', 'DESTINO', 'peso', etc."""
    sin_tildes = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return sin_tildes.strip().lower()


def leer_csv_grafo(datos):
    """Lee un CSV con columnas Origen, Destino y Peso (separador ; o ,).

    Devuelve (filas, error): filas es una lista de (origen, destino, peso) lista para
    validar_aristas y error es un texto si el archivo no se puede leer.
    """
    try:
        texto = datos.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = datos.decode("latin-1")
    lineas = [linea for linea in texto.splitlines() if linea.strip()]
    if not lineas:
        return [], "El archivo está vacío."
    sep = ";" if ";" in lineas[0] else ","
    try:
        df = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str, skipinitialspace=True)
    except (pd.errors.ParserError, pd.errors.EmptyDataError):
        return [], "No se pudo leer el archivo como CSV."
    columnas = {_normalizar(c): c for c in df.columns}
    faltan = [c.capitalize() for c in ("origen", "destino", "peso") if c not in columnas]
    if faltan:
        return [], ("El archivo debe tener las columnas Origen, Destino y Peso "
                    f"(falta: {', '.join(faltan)}).")
    df = df[[columnas["origen"], columnas["destino"], columnas["peso"]]].dropna(how="all")
    filas = []
    for u, v, w in df.itertuples(index=False):
        u = "" if pd.isna(u) else str(u).strip().upper()
        v = "" if pd.isna(v) else str(v).strip().upper()
        if pd.isna(w):
            peso = None
        else:
            # con separador ; se acepta coma decimal (2,5); validar_aristas la rechaza igual
            peso = pd.to_numeric(str(w).strip().replace(",", "."), errors="coerce")
            peso = None if pd.isna(peso) else float(peso)
        filas.append((u, v, peso))
    return filas, None


def n_necesario(filas):
    """Menor n que contiene todas las letras del archivo (0 si no hay letras A..Z)."""
    letras = [x for u, v, _ in filas for x in (u, v)
              if len(x) == 1 and x in string.ascii_uppercase]
    return max((string.ascii_uppercase.index(x) + 1 for x in letras), default=0)


def tabla_etiquetas_larga(pasos):
    """Una fila por iteración y vértice: L numérico (vacío si es ∞), predecesores, estado y cambio."""
    filas = []
    for p in pasos:
        cambios = {d["x"]: TIPOS[d["tipo"]] for d in p["decisiones"]}
        for v in p["L"]:
            if v == p["seleccionado"]:
                estado = "Seleccionado (pasa a permanente)"
            else:
                estado = "Temporal" if v in p["temporales"] else "Permanente"
            filas.append({"Iteración": p["iteracion"], "Vértice": v,
                          "L": None if p["L"][v] == INF else p["L"][v],
                          "Predecesores": ", ".join(p["pred"][v]), "Estado": estado,
                          "Tipo de cambio": cambios.get(v, "—")})
    df = pd.DataFrame(filas)
    df["L"] = df["L"].astype("Int64")
    return df


def tabla_operaciones(pasos):
    """Por iteración: comparaciones para elegir el mínimo (|T| − 1) y aristas revisadas."""
    filas = []
    for anterior, p in zip(pasos, pasos[1:]):
        t = len(anterior["temporales"])          # |T| antes de elegir el vértice
        comparaciones, revisadas = t - 1, len(p["decisiones"])
        filas.append({"Iteración": p["iteracion"], "Seleccionado": p["seleccionado"],
                      "|T|": t, "Comparaciones (|T| − 1)": comparaciones,
                      "Aristas revisadas": revisadas, "Operaciones": comparaciones + revisadas})
    return pd.DataFrame(filas, columns=["Iteración", "Seleccionado", "|T|",
                                        "Comparaciones (|T| − 1)", "Aristas revisadas",
                                        "Operaciones"])


def libro_excel(hojas):
    """Arma un .xlsx con una hoja por DataFrame: encabezados en negrita y anchos ajustados."""
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        for nombre, df in hojas.items():
            df.to_excel(writer, sheet_name=nombre, index=False)
            hoja = writer.sheets[nombre]
            for celda in hoja[1]:
                celda.font = Font(bold=True)
            for columna in hoja.columns:
                largo = max(len(str(c.value)) for c in columna if c.value is not None)
                hoja.column_dimensions[columna[0].column_letter].width = min(largo + 3, 70)
    return salida.getvalue()
