"""Presentacion en consola de los resultados de la Parte 1."""

import time

from .instancia import contar_por_tipo, leer_instancia
from .parte1 import alcance_de_estaciones, incidentes_alcanzables, valor_maximo_posible


def _lista_recortada(ids, maximo):
    """Texto de una lista de ids, recortada si es muy larga para la pantalla."""
    if not ids:
        return "-"
    if maximo is None or len(ids) <= maximo:
        return ", ".join(str(i) for i in ids)
    visibles = ", ".join(str(i) for i in ids[:maximo])
    return f"{visibles}, ... (+{len(ids) - maximo})"


def tabla_alcance(alcance, max_ids=10):
    """Lineas de la tabla (lote, tipo) -> costo e incidentes cubiertos."""
    lineas = [
        f"{'lote':<6}{'tipo':<11}{'costo':>8}{'casos':>7}   incidentes cubiertos",
        "-" * 78,
    ]
    for clave in sorted(alcance):
        lote, tipo = clave
        datos = alcance[clave]
        ids = datos["incidentes_cubiertos"]
        lineas.append(
            f"{lote:<6}{tipo:<11}{datos['costo']:>8}{len(ids):>7}   "
            f"[{_lista_recortada(ids, max_ids)}]"
        )
    return lineas


def informe_parte1(nombre, carpeta_instancias=None, max_ids=10, mostrar_tabla=True):
    """Calcula e imprime la Parte 1 para una instancia. Devuelve el alcance.

    `max_ids` recorta en pantalla las listas de incidentes para que la tabla se
    pueda leer; el diccionario devuelto las trae completas. Con `max_ids=None`
    se imprimen enteras.
    """
    inicio = time.perf_counter()
    instancia = leer_instancia(nombre, carpeta_instancias)
    alcance = alcance_de_estaciones(instancia)
    segundos = time.perf_counter() - inicio

    parametros = instancia["parametros"]
    tipos = parametros["tipos"]

    print(f"=== Instancia {nombre} ===")
    print(
        f"{len(instancia['nodos'])} nodos, {len(instancia['incidentes'])} incidentes, "
        f"{len(instancia['lotes'])} lotes, "
        f"presupuesto {parametros['presupuesto_millones']} millones"
    )
    print(f"{len(alcance)} pares (lote, tipo) calculados en {segundos:.2f} s")
    print()

    if mostrar_tabla:
        for linea in tabla_alcance(alcance, max_ids):
            print(linea)
        print()

    historico = contar_por_tipo(instancia["incidentes"])
    alcanzables = incidentes_alcanzables(instancia, alcance)
    print("Techo de cobertura de la instancia, sin mirar el presupuesto:")
    for tipo, datos_tipo in tipos.items():
        print(
            f"  {tipo:<10} {historico.get(tipo, 0):>5} en el historico, "
            f"{len(alcanzables[tipo]):>5} alcanzables por algun lote "
            f"(peso {datos_tipo['peso']})"
        )
    print(f"  valor maximo alcanzable: {valor_maximo_posible(instancia, alcance)}")
    print()

    return alcance
