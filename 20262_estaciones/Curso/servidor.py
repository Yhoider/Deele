"""Interfaz web local del proyecto: mapa interactivo servido con la biblioteca estandar.

Uso:
    python servidor.py              # abre http://127.0.0.1:8000 en el navegador
    python servidor.py --puerto 9000 --sin-navegador

Los calculos se hacen aqui, con los mismos modulos de `estaciones/`; la pagina
(carpeta `web/`) solo dibuja. No requiere internet ni paquetes externos.
"""

import argparse
import json
import threading
import time
import webbrowser
from bisect import bisect_right
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from estaciones.grafo import dijkstra
from estaciones.instancia import CARPETA_INSTANCIAS, ESCALA, NOMBRES_INSTANCIAS, indexar_incidentes, leer_instancia
from estaciones.parte1 import alcance_de_estaciones, valor_maximo_posible
from estaciones.parte2 import HEURISTICAS, ORDEN_TIPOS, busqueda_local, evaluar_propuesta, orden_heuristica
from estaciones.parte3 import resolver_exacto

CARPETA_WEB = Path(__file__).resolve().parent / "web"
ESTATICOS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/estilos.css": ("estilos.css", "text/css; charset=utf-8"),
}
TITULOS = {"pequena": "Barrio", "comuna": "Laureles", "ciudad": "Medellín"}
MAX_LOTES_EXACTO = 20       # con mas lotes, 4^n propuestas hacen inviable el optimo
LIMITE_OPTIMO_SEGUNDOS = 120

_cerrojo_datos = threading.Lock()
_datos: dict[str, dict] = {}
_cerrojo_trabajos = threading.Lock()
_trabajos: dict[tuple[str, int], "_Trabajo"] = {}


class _Trabajo:
    """Estado de una busqueda exacta que corre en segundo plano."""

    def __init__(self) -> None:
        self.estado = "corriendo"
        self.nodos = self.podas = self.mejor = 0
        self.inicio = time.perf_counter()
        self.cancelar = False
        self.propuesta: dict | None = None
        self.info: dict | None = None
        self.error = ""


def _instancias() -> list[dict]:
    """Instancias oficiales y, entre `comuna` y `ciudad`, las zonas de `generar_zonas.py`."""
    carpetas = sorted(p.name for p in CARPETA_INSTANCIAS.iterdir() if (p / "parametros.json").is_file())
    orden = [n for n in ("pequena", "comuna") if n in carpetas]
    orden += [n for n in carpetas if n not in NOMBRES_INSTANCIAS]
    orden += [n for n in ("ciudad",) if n in carpetas]
    lista = []
    for nombre in orden:
        with open(CARPETA_INSTANCIAS / nombre / "parametros.json", encoding="utf-8") as f:
            parametros = json.load(f)
        lista.append({"id": nombre, "titulo": parametros.get("titulo") or TITULOS.get(nombre, nombre),
                      "oficial": nombre in NOMBRES_INSTANCIAS})
    return lista


def _cargar(nombre: str) -> dict:
    """Lee la instancia una sola vez y deja listo lo que la pagina necesita."""
    if nombre not in _datos and nombre not in {i["id"] for i in _instancias()}:
        raise ValueError(f"instancia desconocida: {nombre}")
    with _cerrojo_datos:
        if nombre in _datos:
            return _datos[nombre]
        instancia = leer_instancia(nombre)
        alcance = alcance_de_estaciones(instancia)
        parametros = instancia["parametros"]
        tipos = [t for t in ORDEN_TIPOS if t in parametros["tipos"]]
        tipos += [t for t in parametros["tipos"] if t not in tipos]

        # La pagina trabaja con posiciones (0..n-1) en vez de identificadores.
        pos_nodo = {nodo: i for i, nodo in enumerate(instancia["nodos"])}
        pos_incidente = {iid: i for i, iid in enumerate(instancia["incidentes"])}
        indice_tramo: dict[tuple[int, int], int] = {}
        for origen, aristas in instancia["grafo"].items():
            for destino, _ in aristas:
                a, b = pos_nodo[origen], pos_nodo[destino]
                if a != b:
                    indice_tramo.setdefault((min(a, b), max(a, b)), len(indice_tramo))

        carga = {
            "nombre": nombre,
            "titulo": parametros.get("titulo") or TITULOS.get(nombre, nombre),
            "oficial": nombre in NOMBRES_INSTANCIAS,
            "descripcion": parametros.get("descripcion", ""),
            "presupuesto": parametros["presupuesto_millones"],
            "tipos": [{"id": t, **parametros["tipos"][t]} for t in tipos],
            "nodos": [c for latlon in instancia["nodos"].values() for c in latlon],
            "tramos": [p for par in indice_tramo for p in par],
            "lotes": [
                {
                    "id": lote,
                    "nodo": pos_nodo[dato["nodo"]],
                    "factor": dato["factor_zona"],
                    "hipotetico": lote in parametros.get("lotes_hipoteticos", ()),
                    "opciones": {
                        t: {
                            "costo": alcance[(lote, t)]["costo"],
                            "incidentes": [pos_incidente[i] for i in alcance[(lote, t)]["incidentes_cubiertos"]],
                        }
                        for t in tipos
                    },
                }
                for lote, dato in instancia["lotes"].items()
            ],
            "incidentes": {
                "nodo": [pos_nodo[inc["nodo"]] for inc in instancia["incidentes"].values()],
                "tipo": [tipos.index(inc["tipo"]) for inc in instancia["incidentes"].values()],
            },
            "valor_alcanzable": valor_maximo_posible(instancia, alcance),
            "exacto_viable": len(instancia["lotes"]) <= MAX_LOTES_EXACTO,
        }
        _datos[nombre] = {
            "instancia": instancia,
            "alcance": alcance,
            "pos_nodo": pos_nodo,
            "pos_incidente": pos_incidente,
            "incidentes_por_nodo": indexar_incidentes(instancia["incidentes"]),
            "indice_tramo": indice_tramo,
            "calles": {},
            "heuristicas": {},
            "json": json.dumps(carga, separators=(",", ":")).encode("utf-8"),
        }
        return _datos[nombre]


def _con_presupuesto(instancia: dict, presupuesto: int) -> dict:
    """Copia superficial de la instancia con otro presupuesto (para el deslizador)."""
    parametros = {**instancia["parametros"], "presupuesto_millones": presupuesto}
    return {**instancia, "parametros": parametros}


def _presupuesto(datos: dict, consulta: dict[str, list[str]]) -> int:
    original = datos["instancia"]["parametros"]["presupuesto_millones"]
    valor = int(float(consulta.get("presupuesto", [original])[0]))
    if not 0 <= valor <= 10 * original:
        raise ValueError("presupuesto fuera de rango")
    return valor


def _heuristicas(nombre: str, consulta: dict[str, list[str]]) -> dict:
    datos = _cargar(nombre)
    presupuesto = _presupuesto(datos, consulta)
    if presupuesto in datos["heuristicas"]:  # el deslizador vuelve a menudo al mismo valor
        return datos["heuristicas"][presupuesto]
    instancia = _con_presupuesto(datos["instancia"], presupuesto)
    respuesta = {}
    for metodo in HEURISTICAS:
        extra = {}
        if metodo == "local":
            orden, extra = busqueda_local(instancia, datos["alcance"])
        else:
            orden = orden_heuristica(instancia, datos["alcance"], metodo)
        propuesta = evaluar_propuesta(instancia, datos["alcance"], orden)
        respuesta[metodo] = {
            "estaciones": orden,  # en el orden en que la heuristica las eligio
            "valor": propuesta["valor"],
            "costo_total": propuesta["costo_total"],
            **extra,
        }
    datos["heuristicas"][presupuesto] = respuesta
    return respuesta


def _calles(nombre: str, lote: str) -> dict:
    """Tramos de via que una estacion en `lote` alcanza a recorrer completos.

    Van ordenados por la distancia a la que Dijkstra termina de recorrerlos,
    para que la pagina pueda mostrar como se expande el alcance:
    - `tramos` y `metros`: cada tramo y la distancia a la que queda recorrido.
    - `hasta`: cuantos de esos tramos (los primeros) caben en el radio de cada tipo.
    - `casos`: incidentes dentro del radio mayor, con la distancia a cada uno.
    """
    datos = _cargar(nombre)
    if lote in datos["calles"]:
        return datos["calles"][lote]
    instancia = datos["instancia"]
    if lote not in instancia["lotes"]:
        raise ValueError(f"lote desconocido: {lote}")
    radios = {t: d["radio_m"] * ESCALA for t, d in instancia["parametros"]["tipos"].items()}
    corte = max(radios.values())
    distancia = dijkstra(instancia["grafo"], instancia["lotes"][lote]["nodo"], corte)
    pos_nodo, indice_tramo = datos["pos_nodo"], datos["indice_tramo"]
    recorrido: dict[int, int] = {}  # tramo -> distancia a su extremo mas lejano
    for origen, d in distancia.items():
        for destino, largo in instancia["grafo"][origen]:
            a, b = pos_nodo[origen], pos_nodo[destino]
            if a == b or d + largo > corte:
                continue
            tramo = indice_tramo[(min(a, b), max(a, b))]
            if d + largo < recorrido.get(tramo, corte + 1):
                recorrido[tramo] = d + largo
    orden = sorted(recorrido, key=lambda tramo: (recorrido[tramo], tramo))
    distancias = [recorrido[tramo] for tramo in orden]
    pos_incidente, por_nodo = datos["pos_incidente"], datos["incidentes_por_nodo"]
    datos["calles"][lote] = {
        "tramos": orden,
        "metros": [round(d / ESCALA) for d in distancias],
        "hasta": {t: bisect_right(distancias, radio) for t, radio in radios.items()},
        "casos": [[pos_incidente[iid], round(d / ESCALA)]
                  for nodo, d in distancia.items() for _, iid in por_nodo.get(nodo, ())],
    }
    return datos["calles"][lote]


def _buscar_optimo(clave: tuple[str, int], trabajo: _Trabajo) -> None:
    nombre, presupuesto = clave
    datos = _cargar(nombre)

    def avance(nodos: int, podas: int, mejor: int) -> bool:
        trabajo.nodos, trabajo.podas, trabajo.mejor = nodos, podas, mejor
        return trabajo.cancelar

    try:
        propuesta, info = resolver_exacto(
            _con_presupuesto(datos["instancia"], presupuesto), datos["alcance"],
            limite_segundos=LIMITE_OPTIMO_SEGUNDOS, al_avanzar=avance)
    except Exception as error:  # se informa a la pagina en vez de morir en silencio
        trabajo.error, trabajo.estado = str(error), "error"
        return
    if trabajo.cancelar:
        with _cerrojo_trabajos:
            if _trabajos.get(clave) is trabajo:
                del _trabajos[clave]
        return
    trabajo.propuesta, trabajo.info, trabajo.estado = propuesta, info, "listo"


def _optimo(nombre: str, consulta: dict[str, list[str]]) -> dict:
    datos = _cargar(nombre)
    if len(datos["instancia"]["lotes"]) > MAX_LOTES_EXACTO:
        raise ValueError("el optimo exacto no es viable para esta instancia")
    clave = (nombre, _presupuesto(datos, consulta))
    with _cerrojo_trabajos:
        trabajo = _trabajos.get(clave)
        if trabajo is not None and trabajo.estado == "error":
            trabajo = None
        if trabajo is None and consulta.get("iniciar", ["0"])[0] == "1":
            for otro in _trabajos.values():  # solo una busqueda a la vez
                if otro.estado == "corriendo":
                    otro.cancelar = True
            trabajo = _trabajos[clave] = _Trabajo()
            threading.Thread(target=_buscar_optimo, args=(clave, trabajo), daemon=True).start()
    if trabajo is None:
        return {"estado": "inexistente"}
    if trabajo.estado == "error":
        raise ValueError(trabajo.error)
    if trabajo.estado == "corriendo":
        return {"estado": "corriendo", "nodos": trabajo.nodos, "podas": trabajo.podas,
                "mejor_valor": trabajo.mejor, "segundos": time.perf_counter() - trabajo.inicio}
    return {"estado": "listo", "estaciones": trabajo.propuesta["estaciones"],
            "valor": trabajo.propuesta["valor"], "costo_total": trabajo.propuesta["costo_total"],
            "nodos": trabajo.info["nodos"], "podas": trabajo.podas,
            "segundos": trabajo.info["segundos"], "probado": trabajo.info["optimo_probado"]}


class Manejador(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        url = urlparse(self.path)
        consulta = parse_qs(url.query)
        nombre = consulta.get("nombre", [""])[0]
        try:
            if url.path in ESTATICOS:
                archivo, tipo = ESTATICOS[url.path]
                self._responder(200, (CARPETA_WEB / archivo).read_bytes(), tipo)
            elif url.path == "/api/instancias":
                self._json(_instancias())
            elif url.path == "/api/instancia":
                self._responder(200, _cargar(nombre)["json"])
            elif url.path == "/api/heuristicas":
                self._json(_heuristicas(nombre, consulta))
            elif url.path == "/api/calles":
                self._json(_calles(nombre, consulta.get("lote", [""])[0]))
            elif url.path == "/api/optimo":
                self._json(_optimo(nombre, consulta))
            else:
                self._json({"error": "no existe"}, 404)
        except (FileNotFoundError, ValueError, KeyError) as error:
            self._json({"error": str(error)}, 400)

    def _json(self, objeto: object, estado: int = 200) -> None:
        self._responder(estado, json.dumps(objeto, separators=(",", ":")).encode("utf-8"))

    def _responder(self, estado: int, cuerpo: bytes, tipo: str = "application/json; charset=utf-8") -> None:
        self.send_response(estado)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, formato: str, *args: object) -> None:
        pass  # sin ruido en la terminal durante la demostracion


def main() -> None:
    parser = argparse.ArgumentParser(description="Interfaz web local del proyecto de estaciones.")
    parser.add_argument("--puerto", type=int, default=8000)
    parser.add_argument("--sin-navegador", action="store_true", help="no abrir el navegador al iniciar")
    args = parser.parse_args()
    servidor = None
    for puerto in range(args.puerto, args.puerto + 10):
        try:
            servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
            break
        except OSError:
            continue
    if servidor is None:
        raise SystemExit(f"No hay un puerto libre entre {args.puerto} y {args.puerto + 9}.")
    direccion = f"http://127.0.0.1:{servidor.server_address[1]}"
    print(f"Interfaz lista en {direccion}  (Ctrl+C para salir)", flush=True)
    if not args.sin_navegador:
        threading.Timer(0.4, webbrowser.open, args=(direccion,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")


if __name__ == "__main__":
    main()
