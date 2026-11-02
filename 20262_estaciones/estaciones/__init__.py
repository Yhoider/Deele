"""Proyecto ADA: estaciones para una alcaldia nueva.

Solucion del proyecto, separada por responsabilidades:

- `instancia`: lectura de los cinco archivos de una instancia.
- `grafo`: Dijkstra sobre la red vial dirigida.
- `parte1`: costo y alcance de cada estacion posible (lote, tipo).
- `informe`: presentacion de los resultados en consola.

Uso tipico:

    from estaciones import resolver_parte1
    alcance = resolver_parte1("pequena")
    print(alcance[("L3", "accidente")])
"""

from .grafo import dijkstra
from .informe import informe_parte1
from .instancia import (
    CARPETA_INSTANCIAS,
    ESCALA,
    indexar_incidentes,
    leer_instancia,
)
from .parte1 import alcance_de_estaciones, costo_estacion, resolver_parte1

__all__ = [
    "CARPETA_INSTANCIAS",
    "ESCALA",
    "alcance_de_estaciones",
    "costo_estacion",
    "dijkstra",
    "indexar_incidentes",
    "informe_parte1",
    "leer_instancia",
    "resolver_parte1",
]
