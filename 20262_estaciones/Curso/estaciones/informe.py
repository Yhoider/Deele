"""Presentacion en consola de los resultados de la Parte 1."""

from .instancia import leer_instancia
from .parte1 import alcance_de_estaciones


def tabla_alcance(alcance):
    """Lineas en el formato pedido: par (lote, tipo) y su salida."""
    lineas = []
    for lote, tipo in sorted(alcance):
        datos = alcance[(lote, tipo)]
        lineas.append(
            f"({lote!r}, {tipo!r}): "
            f"{{'costo': {datos['costo']}, "
            f"'casos': {len(datos['incidentes_cubiertos'])}, "
            f"'incidentes_cubiertos': {datos['incidentes_cubiertos']}}}"
        )
    return lineas


def informe_parte1(nombre, carpeta_instancias=None, max_ids=None, mostrar_tabla=True):
    """Calcula e imprime solo la salida exigida para la Parte 1."""
    instancia = leer_instancia(nombre, carpeta_instancias)
    alcance = alcance_de_estaciones(instancia)
    if mostrar_tabla:
        for linea in tabla_alcance(alcance):
            print(linea)
    return alcance
