# Entrega del curso — estaciones para una alcaldía

No requiere instalar paquetes: usa únicamente la biblioteca estándar de Python.
Los datos se leen de `../instancias/`; para entregar una carpeta autocontenida,
se puede copiar allí la carpeta `instancias/` sin modificar el código.

```bash
cd 20262_estaciones/Curso
python main.py parte1 pequena
python main.py parte2 comuna
python main.py parte3 pequena
python main.py parte4 ciudad
python main.py parte4 comuna --exacta
python test_parte1.py
python servidor.py
python interfaz.py
```

## Interfaz web (recomendada para la demostración)

`python servidor.py` abre en el navegador un mapa interactivo en
`http://127.0.0.1:8000`. Usa solo `http.server` de la biblioteca estándar y no
necesita internet: los cálculos los hacen los mismos módulos de `estaciones/`
y la página (carpeta `web/`) únicamente dibuja. Opciones: `--puerto 9000` y
`--sin-navegador`.

- **Mapa:** red vial completa con zoom (rueda o botones) y arrastre. Las vías
  iluminadas son las que cada estación alcanza a recorrer dentro de su radio,
  es decir, el resultado de Dijkstra; no son círculos. Cada vez que aparece
  una estación, su alcance se expande desde el lote en el mismo orden en que
  Dijkstra recorre las vías (de la más cercana a la más lejana) y los
  incidentes se encienden cuando la onda llega a ellos. Al pasar el cursor por
  una estación se resalta solo su alcance. En la leyenda se puede ocultar la
  cobertura de cada tipo.
- **Propuestas:** compara las tres heurísticas, el óptimo y una propuesta
  hecha a mano. «Ver cómo decide» reproduce las voraces paso a paso (en la
  búsqueda local muestra la propuesta final estación por estación).
- **Óptimo exacto:** corre en segundo plano y muestra en vivo las ramas
  exploradas y podadas (solo `pequena` y `comuna`).
- **Tu propuesta:** el visitante pone estaciones con clic en los lotes y ve
  si iguala a las heurísticas o al óptimo.
- **Presupuesto:** el deslizador recalcula todo con otro presupuesto.

`interfaz.py` es el visor anterior en Tkinter. Muestra la red, lotes
(cuadrados), estaciones por tipo y los incidentes cubiertos (círculos llenos)
o no cubiertos (círculos blancos).

## Zonas adicionales (no oficiales)

`python generar_zonas.py` crea en `instancias/` cuatro zonas más de Medellín
recortadas de `ciudad`: `zona_centro`, `zona_poblado`, `zona_belen` y
`zona_aranjuez`. Tienen el mismo formato que una instancia oficial, así que
funcionan con `main.py` (por ejemplo `python main.py parte3 zona_centro`) y
aparecen solas en la interfaz web.

No son instancias del curso y sus resultados no se comparan con los oficiales:

- La red vial y los incidentes son los de `ciudad` que caen en cada zona; se
  conserva la mayor componente fuertemente conexa, igual que en las oficiales.
- `ciudad` solo trae de 5 a 7 lotes por zona. Cada zona se completa hasta 14
  con lotes **hipotéticos** (código `H..`): intersecciones repartidas por la
  zona desde las que se alcanza algún incidente, con el factor del lote real más cercano. Los reales conservan su
  código `L..`. En el mapa los hipotéticos se dibujan con borde punteado.
- El presupuesto (12.000 millones) es el de `comuna`.
- Los límites son rectángulos aproximados, no límites administrativos.

## Organización

- `estaciones/instancia.py`: lectura de datos.
- `estaciones/grafo.py`: Dijkstra dirigido con `heapq`.
- `estaciones/parte1.py`: costo y alcance.
- `estaciones/parte2.py`: heurística base y dos propias (voraz por valor/costo y búsqueda local).
- `estaciones/parte3.py`: búsqueda exacta con poda para pequeña y comuna.
- `estaciones/parte4.py`: propuesta, tabla y justificación.
- `main.py`: ejecución por terminal.
- `servidor.py` y `web/`: interfaz web local (mapa interactivo).
- `generar_zonas.py`: crea las zonas adicionales no oficiales.
- `interfaz.py`: visor gráfico sencillo en Tkinter.

## Técnicas algorítmicas usadas

- **Dijkstra con `heapq` y corte por radio:** calcula caminos mínimos dirigidos
  desde cada lote solo hasta el radio máximo necesario. Se corre una vez por
  lote y el resultado se reutiliza para los tres tipos de estación.
- **Greedy:** la heurística base elige la estación con mayor valor marginal;
  la propia `densidad` elige la de mayor valor marginal por millón invertido.
- **Búsqueda local (`local`):** parte de las dos propuestas voraces y las
  mejora quitando una, dos o tres estaciones y volviendo a llenar el
  presupuesto vorazmente; acepta el cambio solo si el valor sube (o si vale
  igual y cuesta menos) y para cuando nada mejora, así que nunca queda por
  debajo de las voraces. Las coberturas se guardan como máscaras de bits para
  evaluar cada intento con un `|` y un `bit_count`. Resultados: iguala el
  óptimo en `comuna` (1.574) y sube `ciudad` de 7.706 a 7.827 en unos 2 s; en
  `pequena` queda en 19 (el óptimo es 20).
- **Búsqueda exacta con poda (branch and bound):** para `pequena` y `comuna`
  explora propuestas y descarta ramas que no pueden superar la mejor solución
  conocida, por cobertura o presupuesto. No se usa en `ciudad` porque hay
  `4^80` asignaciones posibles.

La interfaz de Tkinter conserva en memoria las propuestas calculadas. Para `ciudad`
dibuja una muestra de la red vial, pero todos los lotes e incidentes se siguen
mostrando; así la visualización no ralentiza el algoritmo.
