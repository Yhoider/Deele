

from pathlib import Path

from .parte1 import alcance_de_estaciones

ORDEN_TIPOS = ("hurto", "accidente", "incendio")
HEURISTICAS = ("base", "densidad", "local")
MAX_COMBINACIONES = 300  # tope de grupos de estaciones que la busqueda local intenta quitar a la vez


def evaluar_propuesta(instancia: dict[str, object],alcance: dict[tuple[str, str], dict[str, int | list[int]]],estaciones: list[tuple[str, str]],) -> dict[str, int | list[tuple[str, str]] | dict[str, int]]:
    
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


def orden_heuristica(instancia: dict[str, object],alcance: dict[tuple[str, str], dict[str, int | list[int]]],metodo: str = "base",) -> list[tuple[str, str]]:
    """Estaciones elegidas por la heuristica, en el orden en que las fue tomando."""
    if metodo == "local":
        return busqueda_local(instancia, alcance)[0]
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
    return elegidas


def construir_heuristica(instancia: dict[str, object],alcance: dict[tuple[str, str], dict[str, int | list[int]]],metodo: str = "base",) -> dict[str, int | list[tuple[str, str]] | dict[str, int]]:

    elegidas = orden_heuristica(instancia, alcance, metodo)
    return evaluar_propuesta(instancia, alcance, elegidas)


def busqueda_local(instancia: dict[str, object],alcance: dict[tuple[str, str], dict[str, int | list[int]]],inicial: list[tuple[str, str]] | None = None,) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Mejora las propuestas voraces por busqueda local.

    Parte de cada heuristica voraz (o de `inicial`) y repite un movimiento:
    quitar una, dos o tres estaciones y volver a llenar el presupuesto
    vorazmente. Si la propuesta que resulta vale mas, o vale igual y cuesta
    menos, se queda con ella y empieza de nuevo. Termina cuando ningun
    movimiento mejora y devuelve la mejor de las partidas, asi que nunca es
    peor que las heuristicas voraces.

    Quitar dos o tres a la vez solo se intenta mientras los grupos posibles no
    pasen de `MAX_COMBINACIONES`; asi el tiempo queda acotado en `ciudad`.

    Las coberturas se guardan como enteros usados de mascara de bits (el bit i
    es el incidente i): unir coberturas es un `|` y contar casos nuevos es
    `bit_count`, mucho mas rapido que operar conjuntos en cada intento.

    Devuelve las estaciones y un resumen: el mejor valor voraz de partida y
    los movimientos de mejora que hizo.
    """
    tipos = instancia["parametros"]["tipos"]
    presupuesto = instancia["parametros"]["presupuesto_millones"]
    pesos = {tipo: datos["peso"] for tipo, datos in tipos.items()}
    orden_tipo = {tipo: i for i, tipo in enumerate(ORDEN_TIPOS)}
    posicion = {iid: i for i, iid in enumerate(instancia["incidentes"])}
    claves = sorted(alcance, key=lambda c: (c[0], orden_tipo.get(c[1], 99)))
    mascara, costo = {}, {}
    for clave in claves:
        bits = 0
        for iid in alcance[clave]["incidentes_cubiertos"]:
            bits |= 1 << posicion[iid]
        mascara[clave], costo[clave] = bits, alcance[clave]["costo"]

    def completar(estaciones: list[tuple[str, str]], por_costo: bool) -> tuple[int, int, list[tuple[str, str]]]:
        """Agrega estaciones vorazmente (por valor/costo o por valor) mientras quepan."""
        estaciones = list(estaciones)
        usados = {lote for lote, _ in estaciones}
        gasto = sum(costo[e] for e in estaciones)
        cubierto = {tipo: 0 for tipo in tipos}
        for e in estaciones:
            cubierto[e[1]] |= mascara[e]
        libres = [c for c in claves if c[0] not in usados and gasto + costo[c] <= presupuesto]
        while libres:
            mejor, quedan = None, []
            for clave in libres:
                if clave[0] in usados or gasto + costo[clave] > presupuesto:
                    continue
                ganancia = pesos[clave[1]] * (mascara[clave] & ~cubierto[clave[1]]).bit_count()
                if not ganancia:
                    continue  # la ganancia solo baja al agregar estaciones: no vuelve a servir
                quedan.append(clave)
                puntaje = (ganancia / costo[clave], ganancia) if por_costo else (ganancia, -costo[clave])
                if mejor is None or puntaje > mejor[0]:
                    mejor = (puntaje, clave)
            if mejor is None:
                break
            clave = mejor[1]
            estaciones.append(clave)
            usados.add(clave[0])
            gasto += costo[clave]
            cubierto[clave[1]] |= mascara[clave]
            libres = quedan
        valor = sum(pesos[tipo] * cubierto[tipo].bit_count() for tipo in tipos)
        return valor, gasto, estaciones

    def mejorar(partida: list[tuple[str, str]]) -> tuple[int, int, list[tuple[str, str]], int]:
        """Desciende desde una propuesta hasta que ningun movimiento la mejore."""
        valor, gasto, actual = completar(partida, True)
        movimientos, mejoro = 0, True
        while mejoro:
            mejoro = False
            for cuantas in (1, 2, 3):
                if cuantas > len(actual) or _total_combinaciones(len(actual), cuantas) > MAX_COMBINACIONES:
                    break
                for quitadas in _combinaciones(len(actual), cuantas):
                    resto = [e for k, e in enumerate(actual) if k not in quitadas]
                    for por_costo in (True, False):
                        v, g, nueva = completar(resto, por_costo)
                        if v > valor or (v == valor and g < gasto):
                            valor, gasto, actual = v, g, nueva
                            movimientos += 1
                            mejoro = True
                            break
                    if mejoro:
                        break
                if mejoro:
                    break
        return valor, gasto, actual, movimientos

    if inicial is None:
        partidas = [orden_heuristica(instancia, alcance, h) for h in ("base", "densidad")]
    else:
        partidas = [list(inicial)]
    valor_inicial = max(completar(p, True)[0] for p in partidas)
    _, _, mejor, movimientos = max((mejorar(p) for p in partidas), key=lambda r: (r[0], -r[1]))
    return mejor, {"valor_inicial": valor_inicial, "movimientos": movimientos}


def _total_combinaciones(n: int, k: int) -> int:
    """Cuantos grupos de k elementos se pueden formar con n."""
    total = 1
    for i in range(k):
        total = total * (n - i) // (i + 1)
    return total


def _combinaciones(n: int, k: int, desde: int = 0):
    """Grupos de k posiciones entre 0 y n-1, en orden (sin usar `itertools`)."""
    if k == 0:
        yield ()
        return
    for i in range(desde, n - k + 1):
        for resto in _combinaciones(n, k - 1, i + 1):
            yield (i,) + resto


def resolver_parte2(nombre: str, carpeta_instancias: str | Path | None = None) -> dict[str, dict[str, int | list[tuple[str, str]] | dict[str, int]]]:
    
    from .instancia import leer_instancia
    instancia = leer_instancia(nombre, carpeta_instancias)
    alcance = alcance_de_estaciones(instancia)
    return {metodo: construir_heuristica(instancia, alcance, metodo)
            for metodo in HEURISTICAS}
