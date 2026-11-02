"""Lectura de una instancia: los cinco archivos de su carpeta.

Nada de lo que define el problema queda fijo en el codigo. El presupuesto, los
tipos de estacion, sus costos base, sus radios y sus pesos salen todos de
`parametros.json`, de modo que la solucion corre sobre cualquier instancia con
el formato descrito en el enunciado, incluida la que entreguen en la
sustentacion.
"""

import csv
import json
from pathlib import Path

# Las longitudes de los tramos vienen con un decimal. Se trabaja en decimetros
# (metros x 10) con aritmetica entera para que las sumas de distancias y la
# comparacion `distancia <= radio` sean exactas.
#
# Con flotantes, una suma como 283.2 + 416.8 + ... puede dar 1000.0000000001 y
# dejar fuera del radio de 1.000 m un incidente que si debia contar.
ESCALA = 10

# La carpeta de instancias se resuelve respecto a este archivo y no respecto al
# directorio de trabajo, para que los scripts corran desde donde sea.
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_INSTANCIAS = RAIZ_PROYECTO / "instancias"

NOMBRES_INSTANCIAS = ("pequena", "comuna", "ciudad")


def _a_decimetros(texto):
    """Convierte una longitud en metros del CSV a decimetros enteros."""
    return int(round(float(texto) * ESCALA))


def leer_instancia(nombre, carpeta_instancias=None):
    """Lee los cinco archivos de una instancia y devuelve sus estructuras.

    Parametros
    ----------
    nombre : str
        Nombre de la carpeta de la instancia (`pequena`, `comuna`, `ciudad` o
        la que se entregue en la sustentacion).
    carpeta_instancias : str o Path, opcional
        Carpeta que contiene las instancias. Por defecto, `instancias/` al lado
        del paquete.

    Devuelve
    --------
    dict con las claves:
        `nombre`      : str
        `parametros`  : dict leido de parametros.json
        `nodos`       : {id_nodo: (lat, lon)}
        `grafo`       : {id_nodo: [(destino, longitud_en_decimetros), ...]}
        `lotes`       : {codigo_lote: {"nodo": int, "factor_zona": float}}
        `incidentes`  : {id_incidente: {"nodo": int, "tipo": str}}
    """
    ruta = Path(carpeta_instancias or CARPETA_INSTANCIAS) / nombre
    if not ruta.is_dir():
        raise FileNotFoundError(f"No existe la carpeta de la instancia: {ruta}")

    with open(ruta / "parametros.json", encoding="utf-8") as f:
        parametros = json.load(f)

    nodos = {}
    with open(ruta / "nodos.csv", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            nodos[int(fila["id"])] = (float(fila["lat"]), float(fila["lon"]))

    # Grafo dirigido como lista de adyacencia. Cada fila de aristas.csv es un
    # tramo que solo se puede recorrer de `origen` a `destino`; una calle de
    # doble sentido aparece dos veces, una por cada direccion.
    grafo = {nodo: [] for nodo in nodos}
    with open(ruta / "aristas.csv", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            origen = int(fila["origen"])
            destino = int(fila["destino"])
            grafo.setdefault(origen, []).append(
                (destino, _a_decimetros(fila["longitud_m"]))
            )
            # Un nodo que solo aparece como destino tambien debe existir en el
            # grafo, aunque no tenga aristas de salida.
            grafo.setdefault(destino, [])

    lotes = {}
    with open(ruta / "lotes.csv", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            lotes[fila["lote"]] = {
                "nodo": int(fila["nodo"]),
                "factor_zona": float(fila["factor_zona"]),
            }

    incidentes = {}
    with open(ruta / "incidentes.csv", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            incidentes[int(fila["id"])] = {
                "nodo": int(fila["nodo"]),
                "tipo": fila["tipo"],
            }

    return {
        "nombre": nombre,
        "parametros": parametros,
        "nodos": nodos,
        "grafo": grafo,
        "lotes": lotes,
        "incidentes": incidentes,
    }


def indexar_incidentes(incidentes):
    """Agrupa los incidentes por nodo: `nodo -> [(tipo, id), ...]`.

    Con este indice, al recorrer las distancias que devuelve Dijkstra solo se
    hace trabajo en los nodos que de verdad tienen incidentes.
    """
    por_nodo = {}
    for iid, inc in incidentes.items():
        por_nodo.setdefault(inc["nodo"], []).append((inc["tipo"], iid))
    return por_nodo


def contar_por_tipo(incidentes):
    """Cuantos incidentes hay de cada tipo en el historico."""
    conteo = {}
    for inc in incidentes.values():
        conteo[inc["tipo"]] = conteo.get(inc["tipo"], 0) + 1
    return conteo
