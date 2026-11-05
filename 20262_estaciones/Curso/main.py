"""Punto de entrada de la entrega: ``python main.py parte1 pequena``."""

import argparse
import sys

from estaciones.informe import informe_parte1
from estaciones.instancia import NOMBRES_INSTANCIAS, leer_instancia
from estaciones.parte1 import alcance_de_estaciones
from estaciones.parte2 import construir_heuristica
from estaciones.parte3 import resolver_exacto
from estaciones.parte4 import informe_propuesta


def _imprimir_propuesta(etiqueta, propuesta):
    print(f"{etiqueta}: valor {propuesta['valor']}, costo {propuesta['costo_total']} millones")
    print("  estaciones:", ", ".join(f"{lote}/{tipo}" for lote, tipo in propuesta["estaciones"]) or "ninguna")
    print("  casos cubiertos:", ", ".join(f"{t}: {n}" for t, n in propuesta["casos_cubiertos"].items()))


def construir_parser():
    parser = argparse.ArgumentParser(description="Proyecto ADA: estaciones para una alcaldia nueva.")
    sub = parser.add_subparsers(dest="parte")
    for parte, ayuda in (("parte1", "alcance y costo"), ("parte2", "heuristicas"), ("parte3", "optimo probado"), ("parte4", "propuesta para el concejo")):
        p = sub.add_parser(parte, help=ayuda)
        p.add_argument("instancias", nargs="*", help="por defecto: pequena, comuna y ciudad")
        p.add_argument("--instancias", dest="carpeta", default=None, metavar="CARPETA")
    sub.choices["parte1"].add_argument("--todos-los-ids", action="store_true")
    sub.choices["parte1"].add_argument("--sin-tabla", action="store_true")
    sub.choices["parte4"].add_argument("--exacta", action="store_true", help="usar el optimo (solo pequena o comuna)")
    return parser


def main(argv=None):
    args = construir_parser().parse_args(argv)
    if args.parte is None:
        print("Proyecto: estaciones para una alcaldia nueva")
        print("Seleccione la entrega a ejecutar:")
        print("  1. Parte 1: alcance y costo")
        print("  2. Parte 2: heuristicas")
        print("  3. Parte 3: comparacion con el optimo")
        print("  4. Parte 4: propuesta para el concejo")
        try:
            opcion = input("Opcion [1-4] (Enter = 1): ").strip() or "1"
        except EOFError:
            # Algunos botones de VS Code ejecutan sin entrada interactiva.
            # En ese caso se muestra una salida util en vez de un error.
            opcion = "1"
        partes = {"1": "parte1", "2": "parte2", "3": "parte3", "4": "parte4"}
        if opcion not in partes:
            print("Opcion no valida. Use un numero entre 1 y 4.", file=sys.stderr)
            return 2
        return main([partes[opcion], "pequena"])
    nombres = args.instancias or list(NOMBRES_INSTANCIAS)
    for nombre in nombres:
        try:
            if args.parte == "parte1":
                informe_parte1(nombre, args.carpeta, None if args.todos_los_ids else 10, not args.sin_tabla)
                continue
            instancia = leer_instancia(nombre, args.carpeta)
            alcance = alcance_de_estaciones(instancia)
            if args.parte == "parte2":
                print(f"=== Parte 2 / {nombre} ===")
                for h in ("base", "densidad", "ajustada"):
                    _imprimir_propuesta(h, construir_heuristica(instancia, alcance, h))
            elif args.parte == "parte3":
                print(f"=== Parte 3 / {nombre}: comparacion ===")
                for h in ("base", "densidad", "ajustada"):
                    propuesta_h = construir_heuristica(instancia, alcance, h)
                    print(f"  {h:<10} valor {propuesta_h['valor']:>5} | costo {propuesta_h['costo_total']:>5}")
                if nombre == "ciudad":
                    print("  optimo      no se calcula: con 80 lotes y 4 decisiones por lote hay 4^80 = 1.46e48 propuestas.")
                else:
                    propuesta, info = resolver_exacto(instancia, alcance)
                    _imprimir_propuesta(f"optimo ({info['segundos']:.2f} s; {info['nodos']} ramas)", propuesta)
            else:
                metodo = "exacta" if args.exacta else "heuristica"
                if metodo == "exacta" and nombre == "ciudad": raise ValueError("la propuesta exacta se pide solo para pequena y comuna")
                datos = informe_propuesta(nombre, metodo, args.carpeta)
                _imprimir_propuesta("propuesta", datos["propuesta"])
                for fila in datos["filas"]: print(f"  {fila['lote']:<5} {fila['tipo']:<10} {fila['costo']:>5} millones, {fila['casos']} casos")
                print(datos["justificacion"])
        except (FileNotFoundError, ValueError) as error:
            print(f"error: {error}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
