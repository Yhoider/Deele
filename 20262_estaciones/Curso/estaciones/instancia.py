
import csv
import json
from pathlib import Path

ESCALA = 10


CARPETA_CURSO = Path(__file__).resolve().parents[1]
CARPETA_INSTANCIAS = CARPETA_CURSO / "instancias"
if not CARPETA_INSTANCIAS.is_dir():
    CARPETA_INSTANCIAS = CARPETA_CURSO.parent / "instancias"

NOMBRES_INSTANCIAS = ("pequena", "comuna", "ciudad")


def _a_decimetros(texto: str) -> int:
    
    return int(round(float(texto) * ESCALA))


def leer_instancia(nombre: str, carpeta_instancias: str | Path | None = None) -> dict[str, object]:

    ruta = Path(carpeta_instancias or CARPETA_INSTANCIAS) / nombre
    if not ruta.is_dir():
        raise FileNotFoundError(f"No existe la carpeta de la instancia: {ruta}")

    with open(ruta / "parametros.json", encoding="utf-8") as f:
        parametros = json.load(f)

    nodos = {}
    with open(ruta / "nodos.csv", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            nodos[int(fila["id"])] = (float(fila["lat"]), float(fila["lon"]))


    grafo = {nodo: [] for nodo in nodos}
    with open(ruta / "aristas.csv", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            origen = int(fila["origen"])
            destino = int(fila["destino"])
            grafo.setdefault(origen, []).append(
                (destino, _a_decimetros(fila["longitud_m"]))
            )

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


def indexar_incidentes(incidentes: dict[int, dict[str, int | str]]) -> dict[int, list[tuple[str, int]]]:
   
    por_nodo = {}
    for iid, inc in incidentes.items():
        por_nodo.setdefault(inc["nodo"], []).append((inc["tipo"], iid))
    return por_nodo


def contar_por_tipo(incidentes: dict[int, dict[str, int | str]]) -> dict[str, int]:

    conteo = {}
    for inc in incidentes.values():
        conteo[inc["tipo"]] = conteo.get(inc["tipo"], 0) + 1
    return conteo
