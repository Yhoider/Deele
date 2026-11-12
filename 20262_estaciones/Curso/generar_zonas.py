"""Genera zonas adicionales de Medellin recortando la instancia `ciudad`.

    python generar_zonas.py

Crea una carpeta por zona en `instancias/` (zona_centro, zona_poblado, ...)
con los mismos cinco archivos de una instancia oficial, de modo que `main.py`
y `servidor.py` las usan sin cambios. Las instancias oficiales no se tocan.

IMPORTANTE: estas zonas NO son instancias oficiales del curso.
- La red vial y los incidentes salen tal cual de `ciudad` (los que caen en la
  zona).
- `ciudad` solo trae entre 5 y 8 lotes por zona, asi que se completan hasta
  LOTES_POR_ZONA con lotes HIPOTETICOS (codigo `H..`): intersecciones elegidas
  para quedar repartidas por la zona, con el factor de zona del lote real mas
  cercano. Se descartan las intersecciones desde las que ninguna estacion
  alcanzaria un incidente. Los lotes reales conservan su codigo `L..`.
- El presupuesto es el mismo de `comuna`, para poder comparar.
- Los limites son rectangulos aproximados, no los limites administrativos.

Solo usa la biblioteca estandar. El generador es determinista: volver a
ejecutarlo produce exactamente los mismos archivos.
"""

import csv
import json
import math
from pathlib import Path

from estaciones.grafo import dijkstra
from estaciones.instancia import CARPETA_INSTANCIAS, ESCALA

# nombre de carpeta -> titulo, lugar (con su preposicion) y caja (lat_min, lat_max, lon_min, lon_max).
# Todas miden lo mismo que la caja de `comuna` (unos 3,0 km x 3,3 km).
ZONAS = {
    "zona_centro": ("Centro", "del centro (La Candelaria)", (6.2350, 6.2620, -75.5750, -75.5450)),
    "zona_poblado": ("El Poblado", "de El Poblado", (6.1950, 6.2220, -75.5850, -75.5550)),
    "zona_belen": ("Belén", "de Belén", (6.2080, 6.2350, -75.6150, -75.5850)),
    "zona_aranjuez": ("Aranjuez", "de Aranjuez, Manrique y la Universidad de Antioquia", (6.2620, 6.2890, -75.5750, -75.5450)),
}
LOTES_POR_ZONA = 14
PRESUPUESTO_MILLONES = 12000
MARGEN_LOTES = 0.10  # los lotes hipoteticos no se ponen pegados al borde de la zona


def _leer(ruta: Path) -> list[dict[str, str]]:
    with open(ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _escribir(ruta: Path, columnas: list[str], filas: list[list[object]]) -> None:
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f, lineterminator="\n")
        escritor.writerow(columnas)
        escritor.writerows(filas)


def _metros(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distancia en linea recta entre dos (lat, lon); solo se usa para repartir lotes."""
    dy = (a[0] - b[0]) * 111320
    dx = (a[1] - b[1]) * 111320 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dx, dy)


def _mayor_componente_fuerte(nodos: set[int], aristas: list[tuple[int, int]]) -> set[int]:
    """Mayor componente fuertemente conexa (Kosaraju, sin recursion)."""
    salen = {n: [] for n in nodos}
    entran = {n: [] for n in nodos}
    for origen, destino in aristas:
        salen[origen].append(destino)
        entran[destino].append(origen)

    # Primera pasada: orden de salida de una busqueda en profundidad.
    orden, visto = [], set()
    for inicio in sorted(nodos):
        if inicio in visto:
            continue
        visto.add(inicio)
        pila = [(inicio, 0)]
        while pila:
            nodo, i = pila[-1]
            if i < len(salen[nodo]):
                pila[-1] = (nodo, i + 1)
                vecino = salen[nodo][i]
                if vecino not in visto:
                    visto.add(vecino)
                    pila.append((vecino, 0))
            else:
                orden.append(nodo)
                pila.pop()

    # Segunda pasada: sobre el grafo invertido, en orden inverso de salida.
    mejor, asignado = set(), set()
    for inicio in reversed(orden):
        if inicio in asignado:
            continue
        componente, pila = {inicio}, [inicio]
        asignado.add(inicio)
        while pila:
            nodo = pila.pop()
            for vecino in entran[nodo]:
                if vecino not in asignado:
                    asignado.add(vecino)
                    componente.add(vecino)
                    pila.append(vecino)
        if len(componente) > len(mejor):
            mejor = componente
    return mejor


def generar_zona(nombre: str, ciudad: dict[str, list[dict[str, str]]]) -> dict[str, object]:
    titulo, lugar, (lat0, lat1, lon0, lon1) = ZONAS[nombre]
    coordenada = {int(f["id"]): (float(f["lat"]), float(f["lon"])) for f in ciudad["nodos"]}
    en_caja = {n for n, (lat, lon) in coordenada.items() if lat0 <= lat <= lat1 and lon0 <= lon <= lon1}
    tramos = [f for f in ciudad["aristas"] if int(f["origen"]) in en_caja and int(f["destino"]) in en_caja]
    # Igual que en las instancias oficiales: se conserva la parte de la red en
    # la que se puede ir y volver entre cualquier par de intersecciones.
    nodos = _mayor_componente_fuerte(en_caja, [(int(f["origen"]), int(f["destino"])) for f in tramos])
    nuevo = {viejo: i for i, viejo in enumerate(sorted(nodos))}

    filas_nodos = [[nuevo[int(f["id"])], f["lat"], f["lon"]] for f in ciudad["nodos"] if int(f["id"]) in nodos]
    filas_aristas = [[nuevo[int(f["origen"])], nuevo[int(f["destino"])], f["longitud_m"], f["nombre"]]
                     for f in tramos if int(f["origen"]) in nodos and int(f["destino"]) in nodos]
    filas_incidentes = [[i + 1, nuevo[int(f["nodo"])], f["tipo"], f["fecha_hora"]]
                        for i, f in enumerate(f for f in ciudad["incidentes"] if int(f["nodo"]) in nodos)]

    # Lotes reales de `ciudad` que caen en la zona.
    lotes = [(f["lote"], int(f["nodo"]), f["factor_zona"]) for f in ciudad["lotes"] if int(f["nodo"]) in nodos]

    # Lotes hipoteticos: en cada paso, la interseccion mas lejana de los lotes ya puestos.
    vecinos = {n: set() for n in nodos}
    for f in tramos:
        if int(f["origen"]) in nodos and int(f["destino"]) in nodos:
            vecinos[int(f["origen"])].add(int(f["destino"]))
    alto, ancho = (lat1 - lat0) * MARGEN_LOTES, (lon1 - lon0) * MARGEN_LOTES
    ocupados = {nodo for _, nodo, _ in lotes}
    candidatos = sorted(n for n in nodos if n not in ocupados and len(vecinos[n]) >= 3
                        and lat0 + alto <= coordenada[n][0] <= lat1 - alto
                        and lon0 + ancho <= coordenada[n][1] <= lon1 - ancho)
    centro = ((lat0 + lat1) / 2, (lon0 + lon1) / 2)
    puestos = [coordenada[nodo] for _, nodo, _ in lotes] or [centro]
    lejania = {n: min(_metros(coordenada[n], p) for p in puestos) for n in candidatos}
    reales = [(coordenada[int(f["nodo"])], f["factor_zona"]) for f in ciudad["lotes"]]

    # Para descartar lotes inutiles se mide el alcance por la red, como en la parte 1.
    grafo = {n: [] for n in nodos}
    for f in tramos:
        if int(f["origen"]) in nodos and int(f["destino"]) in nodos:
            grafo[int(f["origen"])].append((int(f["destino"]), int(round(float(f["longitud_m"]) * ESCALA))))
    radio = {tipo: datos["radio_m"] * ESCALA for tipo, datos in ciudad["parametros"]["tipos"].items()}
    incidentes_en = {}
    for f in ciudad["incidentes"]:
        if int(f["nodo"]) in nodos:
            incidentes_en.setdefault(int(f["nodo"]), set()).add(f["tipo"])

    def alcanza_incidentes(nodo: int) -> bool:
        distancia = dijkstra(grafo, nodo, max(radio.values()))
        return any(d <= radio[tipo] for n, d in distancia.items() for tipo in incidentes_en.get(n, ()))

    hipoteticos = []
    while len(lotes) < LOTES_POR_ZONA and candidatos:
        elegido = max(candidatos, key=lambda n: (lejania[n], -n))
        candidatos.remove(elegido)
        if not alcanza_incidentes(elegido):
            continue
        factor = min(reales, key=lambda r: _metros(r[0], coordenada[elegido]))[1]
        codigo = f"H{len(hipoteticos) + 1:02d}"
        hipoteticos.append(codigo)
        lotes.append((codigo, elegido, factor))
        for n in candidatos:
            lejania[n] = min(lejania[n], _metros(coordenada[n], coordenada[elegido]))

    parametros = dict(ciudad["parametros"])
    parametros["descripcion"] = (f"Recorte aproximado {lugar} sobre la red vial real de Medellín. "
                                 f"Zona no oficial: {len(hipoteticos)} de sus {len(lotes)} lotes son hipotéticos.")
    parametros["presupuesto_millones"] = PRESUPUESTO_MILLONES
    parametros.update({"titulo": titulo, "no_oficial": True, "generada_por": "generar_zonas.py",
                       "caja_lat_lon": [lat0, lat1, lon0, lon1], "lotes_hipoteticos": hipoteticos})

    carpeta = CARPETA_INSTANCIAS / nombre
    carpeta.mkdir(exist_ok=True)
    _escribir(carpeta / "nodos.csv", ["id", "lat", "lon"], filas_nodos)
    _escribir(carpeta / "aristas.csv", ["origen", "destino", "longitud_m", "nombre"], filas_aristas)
    _escribir(carpeta / "incidentes.csv", ["id", "nodo", "tipo", "fecha_hora"], filas_incidentes)
    _escribir(carpeta / "lotes.csv", ["lote", "nodo", "factor_zona"], [[c, nuevo[n], f] for c, n, f in lotes])
    with open(carpeta / "parametros.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(parametros, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return {"nodos": len(filas_nodos), "tramos": len(filas_aristas), "incidentes": len(filas_incidentes),
            "lotes": len(lotes), "hipoteticos": len(hipoteticos), "fuera_de_la_componente": len(en_caja) - len(nodos)}


def main() -> None:
    origen = CARPETA_INSTANCIAS / "ciudad"
    ciudad = {nombre: _leer(origen / f"{nombre}.csv") for nombre in ("nodos", "aristas", "lotes", "incidentes")}
    with open(origen / "parametros.json", encoding="utf-8") as f:
        ciudad["parametros"] = json.load(f)
    for nombre in ZONAS:
        resumen = generar_zona(nombre, ciudad)
        print(f"{nombre:<14} " + "  ".join(f"{clave}={valor}" for clave, valor in resumen.items()))


if __name__ == "__main__":
    main()
