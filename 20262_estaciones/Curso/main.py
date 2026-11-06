

import argparse
import sys

from estaciones.informe import informe_parte1
from estaciones.instancia import leer_instancia
from estaciones.parte1 import alcance_de_estaciones
from estaciones.parte2 import construir_heuristica
from estaciones.parte3 import resolver_exacto
from estaciones.parte4 import informe_propuesta


def _imprimir_propuesta(etiqueta: str, propuesta: dict[str, object]) -> None:
    
    print(f"{etiqueta}: {propuesta}")


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Proyecto ADA: estaciones para una alcaldia nueva.")
    sub = parser.add_subparsers(dest="parte")
    for parte, ayuda in (("parte1", "alcance y costo"), ("parte2", "heuristicas"), ("parte3", "optimo probado"), ("parte4", "propuesta para el concejo")):
        p = sub.add_parser(parte, help=ayuda)
        p.add_argument("instancias", nargs="*", help="instancia(s); por defecto: pequena")
        p.add_argument("--instancias", dest="carpeta", default=None, metavar="CARPETA")
    sub.choices["parte1"].add_argument("--todos-los-ids", action="store_true")
    sub.choices["parte1"].add_argument("--sin-tabla", action="store_true")
    sub.choices["parte4"].add_argument("--exacta", action="store_true", help="usar el optimo (solo pequena o comuna)")
    return parser


def main(argv: list[str] | None = None) -> int:
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
           
            opcion = "1"
        partes = {"1": "parte1", "2": "parte2", "3": "parte3", "4": "parte4"}
        if opcion not in partes:
            print("Opcion no valida. Use un numero entre 1 y 4.", file=sys.stderr)
            return 2
        print("Instancia: 1. pequena  2. comuna  3. ciudad")
        try:
            eleccion_instancia = input("Instancia [1-3] (Enter = pequena): ").strip() or "1"
        except EOFError:
            eleccion_instancia = "1"
        instancias = {"1": "pequena", "2": "comuna", "3": "ciudad"}
        if eleccion_instancia not in instancias:
            print("Instancia no valida. Use un numero entre 1 y 3.", file=sys.stderr)
            return 2
        return main([partes[opcion], instancias[eleccion_instancia]])
  
    nombres = args.instancias or ["pequena"]
    for nombre in nombres:
        try:
            if args.parte == "parte1":
                informe_parte1(nombre, args.carpeta, None, not args.sin_tabla)
                continue
            instancia = leer_instancia(nombre, args.carpeta)
            alcance = alcance_de_estaciones(instancia)
            if args.parte == "parte2":
                for h in ("base", "densidad", "ajustada"):
                    _imprimir_propuesta(h, construir_heuristica(instancia, alcance, h))
            elif args.parte == "parte3":
                for h in ("base", "densidad", "ajustada"):
                    propuesta_h = construir_heuristica(instancia, alcance, h)
                    _imprimir_propuesta(h, propuesta_h)
                if nombre == "ciudad":
                    print("  optimo      no se calcula: con 80 lotes y 4 decisiones por lote hay 4^80 = 1.46e48 propuestas.")
                else:
                    propuesta, info = resolver_exacto(instancia, alcance)
                    _imprimir_propuesta("optimo", propuesta)
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
