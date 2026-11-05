"""Parte 1. Alcance y costo de cada estacion posible.

Para una instancia cualquiera, calcula para cada lote y cada tipo de estacion:

- el costo de construir esa estacion en ese lote, y
- la lista ordenada de `id` de los incidentes que esa estacion cubriria por si
  sola, segun la regla 4 del enunciado.

La idea que hace rapido el calculo es que **un solo Dijkstra por lote alcanza
para los tres tipos**: se corre una vez desde el nodo del lote cortando en el
radio mas grande de todos los tipos, y de ese mismo resultado se filtra el radio
de cada tipo. En `ciudad` son 80 ejecuciones de Dijkstra y no 240.
"""

import math

from .grafo import dijkstra
from .instancia import ESCALA, indexar_incidentes, leer_instancia


def costo_estacion(costo_base, factor_zona):
    """`costo_base x factor_zona`, redondeado al millon mas cercano.

    El producto se redondea antes a seis decimales para limpiar el ruido
    binario: `2000 * 1.4` da 2800.0000000000005 en flotantes. Luego se usa
    `floor(x + 0.5)` para redondear medio arriba, que es la lectura natural de
    "al millon mas cercano" (`round` de Python redondea los empates al par).
    """
    producto = round(costo_base * factor_zona, 6)
    return int(math.floor(producto + 0.5))


def alcance_de_estaciones(instancia):
    """Costo e incidentes cubiertos de cada par (lote, tipo).

    Parametros
    ----------
    instancia : dict
        Lo que devuelve `leer_instancia`.

    Devuelve
    --------
    dict `{(lote, tipo): {"costo": int, "incidentes_cubiertos": [ids]}}`,
    con las listas de ids ordenadas.
    """
    tipos = instancia["parametros"]["tipos"]
    grafo = instancia["grafo"]
    inc_por_nodo = indexar_incidentes(instancia["incidentes"])

    # Radios en decimetros, en las mismas unidades que los pesos del grafo.
    radio = {tipo: datos["radio_m"] * ESCALA for tipo, datos in tipos.items()}
    corte = max(radio.values())

    resultado = {}
    for lote, datos_lote in instancia["lotes"].items():
        # Un unico Dijkstra por lote, cortado en el radio mas grande.
        dist = dijkstra(grafo, datos_lote["nodo"], corte)

        # De esas distancias se filtran los tres radios en un solo recorrido.
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


def resolver_parte1(nombre_instancia, carpeta_instancias=None):
    """Punto de entrada de la Parte 1: nombre de instancia -> alcance y costos."""
    instancia = leer_instancia(nombre_instancia, carpeta_instancias)
    return alcance_de_estaciones(instancia)


def incidentes_alcanzables(instancia, alcance):
    """Incidentes que alguna estacion posible podria cubrir, por tipo.

    Es el techo de cobertura de la instancia si no hubiera presupuesto, util
    como limite superior contra el cual comparar las heuristicas de la Parte 2
    y el optimo de la Parte 3.

    Devuelve `{tipo: conjunto_de_ids}`.
    """
    por_tipo = {tipo: set() for tipo in instancia["parametros"]["tipos"]}
    for (_, tipo), datos in alcance.items():
        por_tipo[tipo].update(datos["incidentes_cubiertos"])
    return por_tipo


def valor_maximo_posible(instancia, alcance):
    """Suma de pesos de todos los incidentes alcanzables, sin mirar presupuesto."""
    tipos = instancia["parametros"]["tipos"]
    alcanzables = incidentes_alcanzables(instancia, alcance)
    return sum(tipos[tipo]["peso"] * len(ids) for tipo, ids in alcanzables.items())
