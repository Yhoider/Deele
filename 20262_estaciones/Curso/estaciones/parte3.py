"""Parte 3: busqueda exacta con poda, sin librerias de combinaciones."""

import time
from pathlib import Path

from .parte1 import alcance_de_estaciones
from .parte2 import construir_heuristica, evaluar_propuesta


def resolver_exacto(instancia: dict[str, object],alcance: dict[tuple[str, str], dict[str, int | list[int]]] | None = None,limite_segundos: float | None = None,) -> tuple[dict[str, int | list[tuple[str, str]] | dict[str, int]],dict[str, float | int | bool],]:
   
    alcance = alcance or alcance_de_estaciones(instancia)
    tipos = instancia["parametros"]["tipos"]
    presupuesto = instancia["parametros"]["presupuesto_millones"]
    lotes = sorted(instancia["lotes"])
    opciones = {lote: [(tipo, alcance[(lote, tipo)]) for tipo in tipos] for lote in lotes}
   
    lotes.sort(key=lambda lote: max(len(opcion["incidentes_cubiertos"]) * tipos[tipo]["peso"]
                                    for tipo, opcion in opciones[lote]), reverse=True)
    mejor = max((construir_heuristica(instancia, alcance, h)
                 for h in ("base", "densidad", "ajustada")), key=lambda r: r["valor"])
    inicio, nodos, agotado = time.perf_counter(), 0, False
    restantes = [{tipo: set() for tipo in tipos} for _ in range(len(lotes) + 1)]
    for i in range(len(lotes) - 1, -1, -1):
        for tipo in tipos:
            restantes[i][tipo] = set(restantes[i + 1][tipo])
        for tipo, opcion in opciones[lotes[i]]:
            restantes[i][tipo].update(opcion["incidentes_cubiertos"])

    def buscar(i: int,costo: int,cubiertos: dict[str, set[int]],valor: int,estaciones: list[tuple[str, str]],) -> None:
        nonlocal mejor, nodos, agotado
        nodos += 1
        if limite_segundos is not None and time.perf_counter() - inicio > limite_segundos:
            agotado = True
            return
        techo = valor + sum(len(restantes[i][tipo] - cubiertos[tipo]) * tipos[tipo]["peso"]
                            for tipo in tipos)
        if techo <= mejor["valor"]:
            return
        
        capacidad = presupuesto - costo
        ganancias = []
        for j in range(i, len(lotes)):
            for tipo, opcion in opciones[lotes[j]]:
                if opcion["costo"] <= capacidad:
                    ganancia = len(set(opcion["incidentes_cubiertos"]) - cubiertos[tipo]) * tipos[tipo]["peso"]
                    if ganancia:
                        ganancias.append((ganancia / opcion["costo"], ganancia, opcion["costo"]))
        ganancias.sort(reverse=True)
        cota_presupuesto = valor
        disponible = capacidad
        for _, ganancia, precio in ganancias:
            toma = min(disponible, precio)
            cota_presupuesto += ganancia * toma / precio
            disponible -= toma
            if not disponible:
                break
        if cota_presupuesto <= mejor["valor"]:
            return
        if i == len(lotes):
            candidato = evaluar_propuesta(instancia, alcance, estaciones)
            if candidato["valor"] > mejor["valor"]:
                mejor = candidato
            return
        lote = lotes[i]
        candidatas = []
        for tipo, opcion in opciones[lote]:
            if costo + opcion["costo"] <= presupuesto:
                nuevos = set(opcion["incidentes_cubiertos"]) - cubiertos[tipo]
                candidatas.append((len(nuevos) * tipos[tipo]["peso"], tipo, opcion, nuevos))
        candidatas.sort(reverse=True, key=lambda x: x[0])
        for ganancia, tipo, opcion, nuevos in candidatas:
            siguiente = dict(cubiertos)
            siguiente[tipo] = cubiertos[tipo] | nuevos
            buscar(i + 1, costo + opcion["costo"], siguiente, valor + ganancia,
                   estaciones + [(lote, tipo)])
        buscar(i + 1, costo, cubiertos, valor, estaciones)

    buscar(0, 0, {tipo: set() for tipo in tipos}, 0, [])
    return mejor, {"segundos": time.perf_counter() - inicio, "nodos": nodos,
                   "optimo_probado": not agotado}


def resolver_parte3(nombre: str,carpeta_instancias: str | Path | None = None,limite_segundos: float | None = None,) -> tuple[dict[str, int | list[tuple[str, str]] | dict[str, int]],dict[str, float | int | bool],]:
    from .instancia import leer_instancia
    instancia = leer_instancia(nombre, carpeta_instancias)
    return resolver_exacto(instancia, limite_segundos=limite_segundos)
