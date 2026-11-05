"""Parte 2: heuristicas que construyen una propuesta estacion por estacion."""

from .parte1 import alcance_de_estaciones

ORDEN_TIPOS = ("hurto", "accidente", "incendio")


def evaluar_propuesta(instancia, alcance, estaciones):
    """Calcula costo, casos unicos por tipo y valor de una propuesta valida."""
    tipos = instancia["parametros"]["tipos"]
    cubiertos = {tipo: set() for tipo in tipos}
    costo = 0
    for lote, tipo in estaciones:
        opcion = alcance[(lote, tipo)]
        costo += opcion["costo"]
        cubiertos[tipo].update(opcion["incidentes_cubiertos"])
    casos = {tipo: len(cubiertos[tipo]) for tipo in tipos}
    valor = sum(casos[tipo] * tipos[tipo]["peso"] for tipo in tipos)
    return {"estaciones": sorted(estaciones), "costo_total": costo,
            "casos_cubiertos": casos, "valor": valor}


def construir_heuristica(instancia, alcance, metodo="base"):
    """Aplica la base o dos heuristicas propias: densidad y ajustada."""
    tipos = instancia["parametros"]["tipos"]
    presupuesto = instancia["parametros"]["presupuesto_millones"]
    orden_tipo = {tipo: i for i, tipo in enumerate(ORDEN_TIPOS)}
    cubiertos = {tipo: set() for tipo in tipos}
    usados, elegidas, gastado = set(), [], 0
    while True:
        candidatos = []
        for (lote, tipo), opcion in alcance.items():
            if lote in usados or gastado + opcion["costo"] > presupuesto:
                continue
            nuevos = set(opcion["incidentes_cubiertos"]) - cubiertos[tipo]
            valor = len(nuevos) * tipos[tipo]["peso"]
            if not valor:
                continue
            if metodo == "base":
                clave = (valor, 0, 0)
            elif metodo == "densidad":
                clave = (valor / opcion["costo"], valor, 0)
            elif metodo == "ajustada":
                clave = (valor / opcion["costo"], tipos[tipo]["peso"], valor)
            else:
                raise ValueError("heuristica desconocida: " + metodo)
            candidatos.append((clave, lote, tipo, opcion, nuevos))
        if not candidatos:
            break
        candidatos.sort(key=lambda x: (-x[0][0], -x[0][1], -x[0][2], x[1],
                                        orden_tipo.get(x[2], 99)))
        _, lote, tipo, opcion, nuevos = candidatos[0]
        usados.add(lote)
        elegidas.append((lote, tipo)
        )
        gastado += opcion["costo"]
        cubiertos[tipo].update(nuevos)
    return evaluar_propuesta(instancia, alcance, elegidas)


def resolver_parte2(nombre, carpeta_instancias=None):
    """Devuelve las propuestas de las tres heuristicas para una instancia."""
    from .instancia import leer_instancia
    instancia = leer_instancia(nombre, carpeta_instancias)
    alcance = alcance_de_estaciones(instancia)
    return {metodo: construir_heuristica(instancia, alcance, metodo)
            for metodo in ("base", "densidad", "ajustada")}
