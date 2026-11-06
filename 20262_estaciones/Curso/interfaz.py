"""Panel grafico para explorar las propuestas, sin dependencias externas."""

import tkinter as tk
from tkinter import ttk

from estaciones.parte4 import informe_propuesta


COLORES = {"hurto": "#3b82f6", "accidente": "#f59e0b", "incendio": "#ef4444"}
FONDO, PANEL, TINTA, MUTED, PRIMARIO = "#f1f5f9", "#ffffff", "#0f172a", "#64748b", "#2563eb"
MAX_TRAMOS_DIBUJADOS = 3000


class Aplicacion(tk.Tk):
    """Ventana para comparar propuestas y verlas sobre la red vial."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Estaciones · Panel de decisión")
        self.geometry("1240x780")
        self.minsize(980, 640)
        self.configure(background=FONDO)
        self.cache: dict[tuple[str, str], dict] = {}
        self.datos_actuales: dict | None = None
        self._redibujado_pendiente: str | None = None
        self.instancia, self.metodo = tk.StringVar(value="pequena"), tk.StringVar(value="heuristica")
        self.estado = tk.StringVar(value="Listo para calcular una propuesta.")
        self.metricas = {clave: tk.StringVar(value="—") for clave in ("valor", "costo", "cobertura")}
        self._crear_estilos()
        self._crear_encabezado()
        self._crear_contenido()
        # Al iniciar, el canvas todavía mide 1×1. Se espera al ciclo visual de
        # Tk para calcular las coordenadas con el tamaño real del panel.
        self.after_idle(self.mostrar)

    def _crear_estilos(self) -> None:
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("TCombobox", padding=6, font=("TkDefaultFont", 10))
        estilo.configure("Accion.TButton", background=PRIMARIO, foreground="white", borderwidth=0, padding=(15, 9), font=("TkDefaultFont", 10, "bold"))
        estilo.map("Accion.TButton", background=[("active", "#1d4ed8"), ("disabled", "#93c5fd")])
        estilo.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TINTA, rowheight=32, font=("TkDefaultFont", 10), borderwidth=0)
        estilo.configure("Treeview.Heading", background="#e2e8f0", foreground="#334155", font=("TkDefaultFont", 9, "bold"), relief="flat", padding=(8, 9))
        estilo.map("Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", TINTA)])

    def _crear_encabezado(self) -> None:
        encabezado = tk.Frame(self, background="#172554", padx=28, pady=20)
        encabezado.pack(fill="x")
        self._etiqueta(encabezado, "ESTACIONES PARA LA CIUDAD", "#93c5fd", 9, "bold").pack(anchor="w")
        self._etiqueta(encabezado, "Panel de decisión territorial", "white", 22, "bold").pack(anchor="w", pady=(3, 2))
        self._etiqueta(encabezado, "Compare alternativas de cobertura, presupuesto e incidentes atendidos.", "#cbd5e1", 10).pack(anchor="w")

        controles = tk.Frame(self, background=FONDO, padx=28, pady=16)
        controles.pack(fill="x")
        tarjeta = self._tarjeta(controles, 18, 14)
        tarjeta.pack(fill="x")
        self._etiqueta(tarjeta, "ESCENARIO", MUTED, 8, "bold").grid(row=0, column=0, sticky="w")
        self._etiqueta(tarjeta, "MÉTODO", MUTED, 8, "bold").grid(row=0, column=1, sticky="w", padx=(16, 0))
        self.selector_instancia = ttk.Combobox(tarjeta, textvariable=self.instancia, values=("pequena", "comuna", "ciudad"), width=16, state="readonly")
        self.selector_instancia.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.selector_metodo = ttk.Combobox(tarjeta, textvariable=self.metodo, values=("heuristica", "exacta"), width=16, state="readonly")
        self.selector_metodo.grid(row=1, column=1, sticky="w", padx=(16, 0), pady=(4, 0))
        self.boton = ttk.Button(tarjeta, text="Actualizar propuesta", style="Accion.TButton", command=self.mostrar)
        self.boton.grid(row=1, column=2, sticky="w", padx=(16, 0), pady=(4, 0))
        self._etiqueta(tarjeta, "", MUTED, 9, variable=self.estado).grid(row=1, column=3, sticky="e", padx=(22, 0))
        tarjeta.columnconfigure(3, weight=1)
        self.selector_instancia.bind("<<ComboboxSelected>>", lambda _evento: self._validar_metodo())

    def _crear_contenido(self) -> None:
        area = tk.Frame(self, background=FONDO, padx=28, pady=24)
        area.pack(fill="both", expand=True)
        self._crear_metricas(area)
        cuerpo = tk.Frame(area, background=FONDO)
        cuerpo.pack(fill="both", expand=True, pady=(16, 0))
        cuerpo.columnconfigure(0, weight=3)
        cuerpo.columnconfigure(1, weight=2)
        cuerpo.rowconfigure(0, weight=1)

        mapa = self._tarjeta(cuerpo, 14, 14)
        mapa.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._titulo_panel(mapa, "Mapa de cobertura", "Red vial, lotes e incidentes atendidos").pack(fill="x", pady=(0, 10))
        self.canvas = tk.Canvas(mapa, background="#f8fafc", highlightthickness=1, highlightbackground="#e2e8f0")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._programar_redibujado)

        lateral = self._tarjeta(cuerpo, 14, 14)
        lateral.grid(row=0, column=1, sticky="nsew")
        self._titulo_panel(lateral, "Estaciones seleccionadas", "Detalle de la propuesta recomendada").pack(fill="x", pady=(0, 10))
        tabla_contenedor = tk.Frame(lateral, background=PANEL)
        tabla_contenedor.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(tabla_contenedor, columns=("lote", "tipo", "costo", "casos"), show="headings")
        for columna, texto, ancho in (("lote", "Lote", 62), ("tipo", "Estación", 118), ("costo", "Costo", 80), ("casos", "Casos", 60)):
            self.tabla.heading(columna, text=texto)
            self.tabla.column(columna, width=ancho, anchor="center", stretch=columna == "tipo")
        scroll = ttk.Scrollbar(tabla_contenedor, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scroll.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.justificacion = tk.Label(lateral, justify="left", anchor="w", wraplength=360, background="#eff6ff", foreground="#1e3a8a", padx=12, pady=10, font=("TkDefaultFont", 9))
        self.justificacion.pack(fill="x", pady=(12, 0))

    def _crear_metricas(self, contenedor: tk.Frame) -> None:
        fila = tk.Frame(contenedor, background=FONDO)
        fila.pack(fill="x")
        for indice, (clave, titulo, subtitulo, color) in enumerate((("valor", "Valor generado", "prioridad de incidentes", "#2563eb"), ("costo", "Inversión", "millones de pesos", "#7c3aed"), ("cobertura", "Casos cubiertos", "incidentes únicos", "#059669"))):
            tarjeta = self._tarjeta(fila, 16, 12)
            tarjeta.grid(row=0, column=indice, sticky="ew", padx=(0 if indice == 0 else 10, 0))
            self._etiqueta(tarjeta, titulo.upper(), MUTED, 8, "bold").pack(anchor="w")
            self._etiqueta(tarjeta, "", color, 18, "bold", self.metricas[clave]).pack(anchor="w", pady=(3, 0))
            self._etiqueta(tarjeta, subtitulo, MUTED, 8).pack(anchor="w")
            fila.columnconfigure(indice, weight=1)

    def _tarjeta(self, padre: tk.Widget, padx: int, pady: int) -> tk.Frame:
        return tk.Frame(padre, background=PANEL, padx=padx, pady=pady, highlightbackground="#e2e8f0", highlightthickness=1)

    def _etiqueta(self, padre: tk.Widget, texto: str, color: str, tamano: int, peso: str = "normal", variable: tk.StringVar | None = None) -> tk.Label:
        return tk.Label(padre, text=texto, textvariable=variable, background=padre.cget("background"), foreground=color, font=("TkDefaultFont", tamano, peso))

    def _titulo_panel(self, padre: tk.Frame, titulo: str, subtitulo: str) -> tk.Frame:
        contenedor = tk.Frame(padre, background=PANEL)
        self._etiqueta(contenedor, titulo, TINTA, 12, "bold").pack(anchor="w")
        self._etiqueta(contenedor, subtitulo, MUTED, 9).pack(anchor="w", pady=(1, 0))
        return contenedor

    def _validar_metodo(self) -> None:
        if self.instancia.get() == "ciudad" and self.metodo.get() == "exacta":
            self.metodo.set("heuristica")
            self.estado.set("El óptimo exacto no es viable para la instancia ciudad.")

    def mostrar(self) -> None:
        self._validar_metodo()
        clave = (self.instancia.get(), self.metodo.get())
        self.boton.state(["disabled"])
        self.estado.set("Calculando la propuesta…")
        self.update_idletasks()
        try:
            datos = self.cache.get(clave)
            if datos is None:
                datos = informe_propuesta(*clave)
                self.cache[clave] = datos
                mensaje = "Propuesta actualizada con éxito."
            else:
                mensaje = "Propuesta recuperada de la memoria."
            self._actualizar_panel(datos)
            self.dibujar(datos)
            self.estado.set(mensaje)
        except (FileNotFoundError, ValueError) as error:
            self.estado.set(f"Error: {error}")
        finally:
            self.boton.state(["!disabled"])

    def _actualizar_panel(self, datos: dict) -> None:
        self.datos_actuales = datos
        propuesta, parametros = datos["propuesta"], datos["instancia"]["parametros"]
        casos = sum(propuesta["casos_cubiertos"].values())
        self.metricas["valor"].set(f"{propuesta['valor']:,}")
        self.metricas["costo"].set(f"{propuesta['costo_total']:,} / {parametros['presupuesto_millones']:,}")
        self.metricas["cobertura"].set(f"{casos:,}")
        self.justificacion.config(text=datos["justificacion"])
        for item in self.tabla.get_children():
            self.tabla.delete(item)
        for fila in datos["filas"]:
            self.tabla.insert("", "end", values=(fila["lote"], fila["tipo"].title(), f"{fila['costo']:,}", fila["casos"]), tags=(fila["tipo"],))
        for tipo, color in COLORES.items():
            self.tabla.tag_configure(tipo, foreground=color)

    def _programar_redibujado(self, _evento: tk.Event) -> None:
        """Redibuja tras estabilizarse el tamaño del canvas al abrir o cambiar la ventana."""
        if self.datos_actuales is None:
            return
        if self._redibujado_pendiente is not None:
            self.after_cancel(self._redibujado_pendiente)
        self._redibujado_pendiente = self.after(120, self._redibujar)

    def _redibujar(self) -> None:
        self._redibujado_pendiente = None
        if self.datos_actuales is not None:
            self.dibujar(self.datos_actuales)

    def dibujar(self, datos: dict) -> None:
        """Dibuja una muestra de la red para mantener fluida la vista de ciudad."""
        self.canvas.delete("all")
        ins, propuesta = datos["instancia"], datos["propuesta"]
        self.update_idletasks()
        ancho, alto, margen = max(self.canvas.winfo_width(), 500), max(self.canvas.winfo_height(), 420), 38
        coordenadas = list(ins["nodos"].values())
        min_lat, max_lat = min(lat for lat, _ in coordenadas), max(lat for lat, _ in coordenadas)
        min_lon, max_lon = min(lon for _, lon in coordenadas), max(lon for _, lon in coordenadas)

        def punto(nodo: int) -> tuple[float, float]:
            lat, lon = ins["nodos"][nodo]
            return (margen + (lon - min_lon) * (ancho - 2 * margen) / (max_lon - min_lon or 1), alto - margen - (lat - min_lat) * (alto - 2 * margen) / (max_lat - min_lat or 1))

        total_tramos = sum(len(aristas) for aristas in ins["grafo"].values())
        paso, contador = max(1, total_tramos // MAX_TRAMOS_DIBUJADOS), 0
        for origen, aristas in ins["grafo"].items():
            for destino, _ in aristas:
                if contador % paso == 0:
                    self.canvas.create_line(*punto(origen), *punto(destino), fill="#dbe4ee", width=1)
                contador += 1
        usados = dict(propuesta["estaciones"])
        cubiertos = {tipo: set() for tipo in ins["parametros"]["tipos"]}
        for lote, tipo in propuesta["estaciones"]:
            cubiertos[tipo].update(datos["alcance"][(lote, tipo)]["incidentes_cubiertos"])
        for iid, incidente in ins["incidentes"].items():
            x, y = punto(incidente["nodo"])
            color, lleno = COLORES[incidente["tipo"]], iid in cubiertos[incidente["tipo"]]
            radio = 3 if len(ins["incidentes"]) < 1500 else 2
            self.canvas.create_oval(x-radio, y-radio, x+radio, y+radio, fill=color if lleno else "#f8fafc", outline=color, width=1)
        for lote, dato in ins["lotes"].items():
            x, y = punto(dato["nodo"])
            color = COLORES.get(usados.get(lote), "#94a3b8")
            self.canvas.create_rectangle(x-6, y-6, x+6, y+6, fill=color, outline="white", width=2)
            if len(ins["lotes"]) <= 20:
                self.canvas.create_text(x, y-15, text=lote, fill="#334155", font=("TkDefaultFont", 8, "bold"))
        self._leyenda()

    def _leyenda(self) -> None:
        x = 14
        for simbolo, texto, color in (("●", "Hurto", COLORES["hurto"]), ("●", "Accidente", COLORES["accidente"]), ("●", "Incendio", COLORES["incendio"]), ("■", "Lote", "#64748b")):
            self.canvas.create_text(x, 15, text=simbolo, fill=color, anchor="w", font=("TkDefaultFont", 10, "bold"))
            x += 13
            self.canvas.create_text(x, 15, text=texto, fill="#475569", anchor="w", font=("TkDefaultFont", 8))
            x += len(texto) * 6 + 18


if __name__ == "__main__":
    Aplicacion().mainloop()
