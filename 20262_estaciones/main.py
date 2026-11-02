"""Punto de entrada del proyecto desde la linea de comandos.

Ejemplos
--------
    python main.py parte1                  # las tres instancias
    python main.py parte1 pequena          # solo una
    python main.py parte1 ciudad --todos-los-ids
    python main.py parte1 sustentacion --instancias ../otra_carpeta

En la sustentacion entregan una instancia nueva con el mismo formato de
archivos. Basta con ponerla como una carpeta mas dentro de `instancias/` y
pasar su nombre; no hay valores de las instancias actuales fijos en el codigo.
"""

import argparse
import sys

from estaciones.informe import informe_parte1
from estaciones.instancia import NOMBRES_INSTANCIAS


def construir_parser():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Proyecto ADA: estaciones para una alcaldia nueva.",
    )
    subcomandos = parser.add_subparsers(dest="parte", required=True)

    p1 = subcomandos.add_parser(
        "parte1", help="alcance y costo de cada estacion posible (lote, tipo)"
    )
    p1.add_argument(
        "instancias",
        nargs="*",
        help=f"nombres de instancia; por defecto {', '.join(NOMBRES_INSTANCIAS)}",
    )
    p1.add_argument(
        "--instancias",
        dest="carpeta",
        default=None,
        metavar="CARPETA",
        help="carpeta que contiene las instancias (por defecto instancias/)",
    )
    p1.add_argument(
        "--todos-los-ids",
        action="store_true",
        help="imprime las listas de incidentes completas, sin recortar",
    )
    p1.add_argument(
        "--sin-tabla",
        action="store_true",
        help="omite la tabla y deja solo el resumen y los tiempos",
    )
    return parser


def main(argv=None):
    args = construir_parser().parse_args(argv)

    if args.parte == "parte1":
        nombres = args.instancias or list(NOMBRES_INSTANCIAS)
        for nombre in nombres:
            try:
                informe_parte1(
                    nombre,
                    carpeta_instancias=args.carpeta,
                    max_ids=None if args.todos_los_ids else 10,
                    mostrar_tabla=not args.sin_tabla,
                )
            except FileNotFoundError as error:
                print(f"error: {error}", file=sys.stderr)
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
