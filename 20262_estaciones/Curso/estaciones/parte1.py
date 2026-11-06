

import math
from pathlib import Path

from .grafo import dijkstra
from .instancia import ESCALA, indexar_incidentes, leer_instancia


def costo_estacion(costo_base: int | float, factor_zona: float) -> int:
    
    producto = round(costo_base * factor_zona, 6)
    return int(math.floor(producto + 0.5))


def alcance_de_estaciones(instancia: dict[str, object]) -> dict[tuple[str, str], dict[str, int | list[int]]]:
    
    tipos = instancia["parametros"]["tipos"]
    grafo = instancia["grafo"]
    inc_por_nodo = indexar_incidentes(instancia["incidentes"])

    # Radios en decimetros, en las mismas unidades que los pesos del grafo.
    radio = {tipo: datos["radio_m"] * ESCALA for tipo, datos in tipos.items()}
    corte = max(radio.values())

    resultado = {}
    for lote, datos_lote in instancia["lotes"].items():
    
        dist = dijkstra(grafo, datos_lote["nodo"], corte)

    
        cubiertos = {tipo: [] for tipo in tipos}
        for nodo, d in dist.items():
            for tipo, iid in inc_por_nodo.get(nodo, ()):
                if d <= radio[tipo]:
                    cubiertos[tipo].append(iid)

        for tipo, datos_tipo in tipos.items():
            resultado[(lote, tipo)] = {
                "costo": costo_estacion(
                    datos_tipo["costo_base"], datos_lote["factor_zona"]
                ),
                "incidentes_cubiertos": sorted(cubiertos[tipo]),
            }
    return resultado


def resolver_parte1(nombre_instancia: str, carpeta_instancias: str | Path | None = None) -> dict[tuple[str, str], dict[str, int | list[int]]]:
  
    instancia = leer_instancia(nombre_instancia, carpeta_instancias)
    return alcance_de_estaciones(instancia)


def incidentes_alcanzables(instancia: dict[str, object],alcance: dict[tuple[str, str], dict[str, int | list[int]]],) -> dict[str, set[int]]:
  
    por_tipo = {tipo: set() for tipo in instancia["parametros"]["tipos"]}
    for (_, tipo), datos in alcance.items():
        por_tipo[tipo].update(datos["incidentes_cubiertos"])
    return por_tipo


def valor_maximo_posible(instancia: dict[str, object],alcance: dict[tuple[str, str], dict[str, int | list[int]]],) -> int:
   
    tipos = instancia["parametros"]["tipos"]
    alcanzables = incidentes_alcanzables(instancia, alcance)
    return sum(tipos[tipo]["peso"] * len(ids) for tipo, ids in alcanzables.items())
