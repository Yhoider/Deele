"""Visor grafico ligero de las propuestas, sin dependencias externas."""

import tkinter as tk
from tkinter import ttk

from estaciones.parte4 import informe_propuesta


COLORES = {"hurto": "#2563eb", "accidente": "#d97706", "incendio": "#dc2626"}
FONDO = "#f8fafc"
MAX_TRAMOS_DIBUJADOS = 3000


class Aplicacion(tk.Tk):
    """Ventana para explorar una propuesta sin recalcular innecesariamente."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Estaciones para una alcaldia")
        self.geometry("1120x720")
        self.minsize(900, 600)
        self.cache = {}
        self.instancia = tk.StringVar(value="pequena")
        self.metodo = tk.StringVar(value="heuristica")
        self.estado = tk.StringVar(value="Listo para calcular.")
        self._crear_estilos()
        self._crear_controles()
        self._crear_contenido()
        self.mostrar()

    def _crear_estilos(self) -> None:
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("Titulo.TLabel", font=("TkDefaultFont", 15, "bold"))
        estilo.configure("Estado.TLabel", foreground="#475569")
        estilo.configure("Treeview", rowheight=26)

    def _crear_controles(self) -> None:
        superior = ttk.Frame(self, padding=(18, 14, 18, 8))
        superior.pack(fill="x")
        ttk.Label(superior, text="Estaciones para una alcaldía", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(superior, text="Seleccione una instancia y compare una propuesta construida por el algoritmo.").pack(anchor="w", pady=(2, 10))

        filtros = ttk.Frame(superior)
        filtros.pack(fill="x")
        ttk.Label(filtros, text="Instancia").pack(side="left")
        self.selector_instancia = ttk.Combobox(filtros, textvariable=self.instancia,
                                                values=("pequena", "comuna", "ciudad"), width=13,
                                                state="readonly")
        self.selector_instancia.pack(side="left", padx=(6, 18))
        ttk.Label(filtros, text="Método").pack(side="left")
        self.selector_metodo = ttk.Combobox(filtros, textvariable=self.metodo,
                                             values=("heuristica", "exacta"), width=13,
                                             state="readonly")
        self.selector_metodo.pack(side="left", padx=6)
        self.boton = ttk.Button(filtros, text="Calcular propuesta", command=self.mostrar)
        self.boton.pack(side="left", padx=12)
        ttk.Label(filtros, textvariable=self.estado, style="Estado.TLabel").pack(side="right")
        self.selector_instancia.bind("<<ComboboxSelected>>", lambda _evento: self._validar_metodo())

    def _crear_contenido(self) -> None:
        self.resumen = ttk.Label(self, padding=(18, 0, 18, 10), justify="left", wraplength=1050)
        self.resumen.pack(fill="x")
        cuerpo = ttk.PanedWindow(self, orient="horizontal")
        cuerpo.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        mapa = ttk.LabelFrame(cuerpo, text="Mapa de la propuesta", padding=6)
        self.canvas = tk.Canvas(mapa, background=FONDO, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        cuerpo.add(mapa, weight=3)

        lateral = ttk.LabelFrame(cuerpo, text="Estaciones construidas", padding=6)
        self.tabla = ttk.Treeview(lateral, columns=("lote", "tipo", "costo", "casos"), show="headings")
        for columna, texto, ancho in (("lote", "Lote", 75), ("tipo", "Tipo", 105),
                                      ("costo", "Costo", 85), ("casos", "Casos", 65)):
            self.tabla.heading(columna, text=texto)
            self.tabla.column(columna, width=ancho, anchor="center", stretch=True)
        self.tabla.pack(fill="both", expand=True)
        cuerpo.add(lateral, weight=2)

    def _validar_metodo(self) -> None:
        if self.instancia.get() == "ciudad" and self.metodo.get() == "exacta":
            self.metodo.set("heuristica")
            self.estado.set("En ciudad se usa heurística: el óptimo exacto no es viable.")

    def mostrar(self) -> None:
        self._validar_metodo()
        clave = (self.instancia.get(), self.metodo.get())
        self.boton.state(["disabled"])
        self.estado.set("Calculando propuesta…")
        self.update_idletasks()
        try:
            datos = self.cache.get(clave)
            if datos is None:
                datos = informe_propuesta(*clave)
                self.cache[clave] = datos
                mensaje = "Propuesta calculada."
            else:
                mensaje = "Propuesta recuperada de la memoria."
            self._actualizar_panel(datos)
            self.dibujar(datos)
            self.estado.set(mensaje)
        except (FileNotFoundError, ValueError) as error:
            self.estado.set(f"Error: {error}")
        finally:
            self.boton.state(["!disabled"])

    def _actualizar_panel(self, datos: dict[str, object]) -> None:
        propuesta = datos["propuesta"]
        parametros = datos["instancia"]["parametros"]
        self.resumen.config(
            text=(f"Valor de la propuesta: {propuesta['valor']}   |   "
                  f"Costo: {propuesta['costo_total']} de {parametros['presupuesto_millones']} millones\n"
                  f"{datos['justificacion']}")
        )
        for item in self.tabla.get_children():
            self.tabla.delete(item)
        for fila in datos["filas"]:
            self.tabla.insert("", "end", values=(fila["lote"], fila["tipo"],
                                                    f"{fila['costo']:,}", fila["casos"]))

    def dibujar(self, datos: dict[str, object]) -> None:
        """Dibuja una muestra representativa de la red para no bloquear ciudad."""
        self.canvas.delete("all")
        ins, propuesta = datos["instancia"], datos["propuesta"]
        self.update_idletasks()
        ancho = max(self.canvas.winfo_width(), 500)
        alto = max(self.canvas.winfo_height(), 450)
        margen = 34
        coordenadas = list(ins["nodos"].values())
        min_lat = min(lat for lat, _ in coordenadas); max_lat = max(lat for lat, _ in coordenadas)
        min_lon = min(lon for _, lon in coordenadas); max_lon = max(lon for _, lon in coordenadas)

        def punto(nodo: int) -> tuple[float, float]:
            lat, lon = ins["nodos"][nodo]
            x = margen + (lon - min_lon) * (ancho - 2 * margen) / (max_lon - min_lon or 1)
            y = alto - margen - (lat - min_lat) * (alto - 2 * margen) / (max_lat - min_lat or 1)
            return x, y

        total_tramos = sum(len(aristas) for aristas in ins["grafo"].values())
        paso = max(1, total_tramos // MAX_TRAMOS_DIBUJADOS)
        contador = 0
        for origen, aristas in ins["grafo"].items():
            for destino, _ in aristas:
                if contador % paso == 0:
                    self.canvas.create_line(*punto(origen), *punto(destino), fill="#d7dee8")
                contador += 1

        usados = dict(propuesta["estaciones"])
        cubiertos = {tipo: set() for tipo in ins["parametros"]["tipos"]}
        for lote, tipo in propuesta["estaciones"]:
            cubiertos[tipo].update(datos["alcance"][(lote, tipo)]["incidentes_cubiertos"])
        for iid, incidente in ins["incidentes"].items():
            x, y = punto(incidente["nodo"])
            color = COLORES[incidente["tipo"]]
            lleno = iid in cubiertos[incidente["tipo"]]
            radio = 3 if len(ins["incidentes"]) < 1500 else 2
            self.canvas.create_oval(x-radio, y-radio, x+radio, y+radio,
                                    fill=color if lleno else FONDO, outline=color)
        for lote, dato in ins["lotes"].items():
            x, y = punto(dato["nodo"])
            color = COLORES.get(usados.get(lote), "#64748b")
            self.canvas.create_rectangle(x-6, y-6, x+6, y+6, fill=color, outline="#0f172a")
            if len(ins["lotes"]) <= 20:
                self.canvas.create_text(x, y-14, text=lote, font=("TkDefaultFont", 8))
        self._leyenda(ancho)

    def _leyenda(self, ancho: int) -> None:
        elementos = (("■", "Lote libre", "#64748b"), ("■", "CAI / hurto", COLORES["hurto"]),
                     ("■", "Tránsito", COLORES["accidente"]), ("■", "Bomberos", COLORES["incendio"]))
        x = 15
        for simbolo, texto, color in elementos:
            self.canvas.create_text(x, 14, text=simbolo, fill=color, anchor="w", font=("TkDefaultFont", 10, "bold"))
            x += 13
            self.canvas.create_text(x, 14, text=texto, fill="#334155", anchor="w", font=("TkDefaultFont", 8))
            x += len(texto) * 6 + 18


if __name__ == "__main__":
    Aplicacion().mainloop()
