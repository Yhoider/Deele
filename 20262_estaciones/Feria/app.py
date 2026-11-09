"""Servidor local de la muestra web para la feria del proyecto."""

import json
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socket import socket
from socketserver import BaseServer
from urllib.parse import parse_qs, urlparse


CARPETA_FERIA = Path(__file__).resolve().parent
CARPETA_CURSO = CARPETA_FERIA.parent / "Curso"
sys.path.insert(0, str(CARPETA_CURSO))

from estaciones.parte4 import informe_propuesta  # noqa: E402


class ManejadorFeria(SimpleHTTPRequestHandler):
    """Sirve la página y entrega la propuesta calculada por el código real."""

    def __init__(
        self, request: socket, client_address: tuple[str, int], server: BaseServer
    ) -> None:
        super().__init__(request, client_address, server, directory=str(CARPETA_FERIA))

    def do_GET(self) -> None:
        ruta = urlparse(self.path)
        if ruta.path == "/api/propuesta":
            self._propuesta(ruta.query)
            return
        super().do_GET()

    def _propuesta(self, consulta: str) -> None:
        parametros = parse_qs(consulta)
        instancia = parametros.get("instancia", ["pequena"])[0]
        metodo = parametros.get("metodo", ["heuristica"])[0]
        if instancia not in {"pequena", "comuna", "ciudad"}:
            self._json({"error": "Instancia no válida."}, HTTPStatus.BAD_REQUEST)
            return
        if metodo not in {"heuristica", "exacta"} or (instancia == "ciudad" and metodo == "exacta"):
            self._json({"error": "El método solicitado no está disponible."}, HTTPStatus.BAD_REQUEST)
            return
        try:
            datos = informe_propuesta(instancia, metodo)
            self._json(self._preparar_respuesta(datos))
        except (FileNotFoundError, ValueError) as error:
            self._json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _preparar_respuesta(self, datos: dict) -> dict:
        """Reduce las estructuras Python a datos pequeños y seguros para el navegador."""
        instancia = datos["instancia"]
        propuesta = datos["propuesta"]
        cubiertos = {tipo: set() for tipo in instancia["parametros"]["tipos"]}
        for lote, tipo in propuesta["estaciones"]:
            cubiertos[tipo].update(datos["alcance"][(lote, tipo)]["incidentes_cubiertos"])

        aristas = [(origen, destino) for origen, conexiones in instancia["grafo"].items() for destino, _ in conexiones]
        paso = max(1, len(aristas) // 3500)
        return {
            "instancia": instancia["nombre"],
            "parametros": instancia["parametros"],
            "propuesta": propuesta,
            "filas": datos["filas"],
            "justificacion": datos["justificacion"],
            "nodos": instancia["nodos"],
            "aristas": aristas[::paso],
            "lotes": instancia["lotes"],
            "incidentes": instancia["incidentes"],
            "cubiertos": {tipo: sorted(ids) for tipo, ids in cubiertos.items()},
        }

    def _json(self, contenido: dict, estado: HTTPStatus = HTTPStatus.OK) -> None:
        cuerpo = json.dumps(contenido, ensure_ascii=False).encode("utf-8")
        self.send_response(estado)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)


if __name__ == "__main__":
    servidor = ThreadingHTTPServer(("127.0.0.1", 8000), ManejadorFeria)
    print("Feria disponible en http://127.0.0.1:8000")
    print("Presioná Ctrl+C para detener el servidor.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
