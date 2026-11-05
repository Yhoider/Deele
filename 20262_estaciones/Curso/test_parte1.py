"""Verificacion de la Parte 1 contra los casos del enunciado.

Se puede correr de dos formas:

    python test_parte1.py      # sin dependencias, imprime el resultado
    pytest test_parte1.py      # si se tiene pytest instalado
"""

import time

from estaciones import resolver_parte1
from estaciones.parte1 import costo_estacion

# Casos `casos_ej_001_parte1` del enunciado, tal como estan en el notebook.
CASOS_ENUNCIADO = [
    {
        "entrada": {"instancia": "pequena", "lote": "L3", "tipo": "accidente"},
        "salida": {"costo": 2800, "incidentes_cubiertos": [1, 2, 4, 6]},
    },
    {
        "entrada": {"instancia": "pequena", "lote": "L2", "tipo": "hurto"},
        "salida": {"costo": 1500, "incidentes_cubiertos": [9, 10, 11, 12, 13]},
    },
]

# Limite de tiempo que exige el enunciado para la instancia grande.
SEGUNDOS_MAXIMOS_CIUDAD = 60


def test_casos_del_enunciado():
    cache = {}
    for caso in CASOS_ENUNCIADO:
        entrada, esperado = caso["entrada"], caso["salida"]
        nombre = entrada["instancia"]
        if nombre not in cache:
            cache[nombre] = resolver_parte1(nombre)
        obtenido = cache[nombre][(entrada["lote"], entrada["tipo"])]
        assert obtenido == esperado, (
            f"{nombre} {entrada['lote']} {entrada['tipo']}: "
            f"se obtuvo {obtenido}, se esperaba {esperado}"
        )


def test_costo_redondea_al_millon_mas_cercano():
    # El ejemplo del enunciado: un CAI en L1 de pequena cuesta 1.000 x 1.1.
    assert costo_estacion(1000, 1.1) == 1100
    # Casos donde el producto en flotantes no es exacto.
    assert costo_estacion(2000, 1.4) == 2800
    assert costo_estacion(5000, 1.15) == 5750
    assert costo_estacion(1000, 0.85) == 850


def test_un_lote_sin_cobertura_devuelve_lista_vacia():
    # L58 de ciudad esta en un nodo desde el que las vias casi no salen y no
    # alcanza ningun incidente de ningun tipo. La salida debe ser una lista
    # vacia, no un error.
    alcance = resolver_parte1("ciudad")
    for tipo in ("hurto", "accidente", "incendio"):
        assert alcance[("L58", tipo)]["incidentes_cubiertos"] == []
        assert alcance[("L58", tipo)]["costo"] > 0


def test_ciudad_termina_en_menos_de_un_minuto():
    inicio = time.perf_counter()
    alcance = resolver_parte1("ciudad")
    segundos = time.perf_counter() - inicio
    assert len(alcance) == 240, f"se esperaban 240 pares, hay {len(alcance)}"
    assert segundos < SEGUNDOS_MAXIMOS_CIUDAD, (
        f"ciudad tardo {segundos:.2f} s, el limite es {SEGUNDOS_MAXIMOS_CIUDAD} s"
    )


def _correr_sin_pytest():
    pruebas = [
        ("casos del enunciado", test_casos_del_enunciado),
        ("redondeo del costo", test_costo_redondea_al_millon_mas_cercano),
        ("lote sin cobertura", test_un_lote_sin_cobertura_devuelve_lista_vacia),
        ("ciudad en menos de un minuto", test_ciudad_termina_en_menos_de_un_minuto),
    ]
    fallos = 0
    for etiqueta, prueba in pruebas:
        try:
            prueba()
        except AssertionError as error:
            fallos += 1
            print(f"FALLA  {etiqueta}")
            print(f"       {error}")
        else:
            print(f"OK     {etiqueta}")
    print()
    if fallos:
        print(f"{fallos} de {len(pruebas)} pruebas fallan.")
    else:
        print(f"Las {len(pruebas)} pruebas pasan.")
    return fallos


if __name__ == "__main__":
    import sys

    sys.exit(1 if _correr_sin_pytest() else 0)
