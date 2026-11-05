"""Presentacion en consola de los resultados de la Parte 1."""

from pathlib import Path

from .instancia import leer_instancia
from .parte1 import alcance_de_estaciones


def tabla_alcance(alcance: dict[tuple[str, str], dict[str, int | list[int]]]) -> list[str]:
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


def informe_parte1(nombre: str,carpeta_instancias: str | Path | None = None,max_ids: int | None = None,mostrar_tabla: bool = True,) -> dict[tuple[str, str], dict[str, int | list[int]]]:
    """Calcula e imprime solo la salida exigida para la Parte 1."""
    instancia = leer_instancia(nombre, carpeta_instancias)
    alcance = alcance_de_estaciones(instancia)
    if mostrar_tabla:
        for linea in tabla_alcance(alcance):
            print(linea)
    return alcance
