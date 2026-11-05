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
python interfaz.py
```

La interfaz muestra la red, lotes (cuadrados), estaciones por tipo y los
incidentes cubiertos (círculos llenos) o no cubiertos (círculos blancos).

## Organización

- `estaciones/instancia.py`: lectura de datos.
- `estaciones/grafo.py`: Dijkstra dirigido con `heapq`.
- `estaciones/parte1.py`: costo y alcance.
- `estaciones/parte2.py`: heurística base y dos propias.
- `estaciones/parte3.py`: búsqueda exacta con poda para pequeña y comuna.
- `estaciones/parte4.py`: propuesta, tabla y justificación.
- `main.py`: ejecución por terminal; `interfaz.py`: visor gráfico sencillo.

## Técnicas algorítmicas usadas

- **Dijkstra con `heapq` y corte por radio:** calcula caminos mínimos dirigidos
  desde cada lote solo hasta el radio máximo necesario. Se corre una vez por
  lote y el resultado se reutiliza para los tres tipos de estación.
- **Greedy:** la heurística base elige la estación con mayor valor marginal;
  las propias comparan valor/costo y prioridades para construir propuestas
  factibles rápidamente.
- **Búsqueda exacta con poda (branch and bound):** para `pequena` y `comuna`
  explora propuestas y descarta ramas que no pueden superar la mejor solución
  conocida, por cobertura o presupuesto. No se usa en `ciudad` porque hay
  `4^80` asignaciones posibles.

La interfaz conserva en memoria las propuestas calculadas. Para `ciudad`
dibuja una muestra de la red vial, pero todos los lotes e incidentes se siguen
mostrando; así la visualización no ralentiza el algoritmo.
