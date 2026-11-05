"""Parte 4: datos y texto para presentar una propuesta al concejo."""

from pathlib import Path

from .parte1 import alcance_de_estaciones
from .parte2 import construir_heuristica
from .parte3 import resolver_exacto


def recomendar(
    instancia: dict[str, object],
    alcance: dict[tuple[str, str], dict[str, int | list[int]]] | None = None,
) -> tuple[
    str,
    dict[str, dict[str, int | list[tuple[str, str]] | dict[str, int]]],
    dict[tuple[str, str], dict[str, int | list[int]]],
]:
    """Escoge la mejor de las heuristicas; empate: menor costo y nombre."""
    alcance = alcance or alcance_de_estaciones(instancia)
    candidatas = {h: construir_heuristica(instancia, alcance, h)
                  for h in ("base", "densidad", "ajustada")}
    nombre = min(candidatas, key=lambda h: (-candidatas[h]["valor"],
                                             candidatas[h]["costo_total"], h))
    return nombre, candidatas, alcance


def tabla_propuesta(
    propuesta: dict[str, int | list[tuple[str, str]] | dict[str, int]],
    alcance: dict[tuple[str, str], dict[str, int | list[int]]],
) -> list[dict[str, str | int]]:
    """Filas solicitadas: lote, tipo, costo y casos que cubre la estacion."""
    return [{"lote": lote, "tipo": tipo, "costo": alcance[(lote, tipo)]["costo"],
             "casos": len(alcance[(lote, tipo)]["incidentes_cubiertos"])}
            for lote, tipo in propuesta["estaciones"]]


def informe_propuesta(
    nombre: str,
    metodo: str = "heuristica",
    carpeta_instancias: str | Path | None = None,
) -> dict[str, object]:
    """Prepara tabla, totales y justificacion, reutilizable por consola o GUI."""
    from .instancia import leer_instancia
    instancia = leer_instancia(nombre, carpeta_instancias)
    alcance = alcance_de_estaciones(instancia)
    if metodo == "exacta":
        propuesta, info = resolver_exacto(instancia, alcance)
        texto = ("La propuesta es optima: la busqueda con poda reviso "
                 f"{info['nodos']} ramas en {info['segundos']:.2f} s.")
    else:
        elegida, candidatas, _ = recomendar(instancia, alcance)
        propuesta, info = candidatas[elegida], {"heuristica": elegida}
        texto = (f"Se recomienda la heuristica {elegida}: obtuvo el mayor valor "
                 f"({propuesta['valor']}) entre las alternativas probadas y cuesta "
                 f"{propuesta['costo_total']} millones.")
    return {"instancia": instancia, "alcance": alcance, "propuesta": propuesta,
            "filas": tabla_propuesta(propuesta, alcance), "info": info,
            "justificacion": texto}
