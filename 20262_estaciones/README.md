# Proyecto ADA: estaciones para una alcaldía nueva

Solución en Python del proyecto de ubicación de estaciones (CAI, tránsito y bomberos)
sobre la red vial de Medellín.

## Cómo correrlo

Requiere solo Python 3.8 o superior, sin instalar nada.

```bash
cd 20262_estaciones

python main.py parte1                    # las tres instancias
python main.py parte1 pequena            # una sola
python main.py parte1 ciudad --sin-tabla # solo el resumen y los tiempos
python main.py parte1 ciudad --todos-los-ids

python test_parte1.py                    # verificación contra el enunciado
```

Para la sustentación, donde entregan una instancia nueva con el mismo formato de
archivos: se pone como una carpeta más dentro de `instancias/` y se pasa su nombre.
No hay valores de las instancias actuales fijos en el código; presupuesto, costos,
radios y pesos salen todos de `parametros.json`.

```bash
python main.py parte1 sustentacion
python main.py parte1 otra --instancias ../ruta/a/las/instancias
```

## Estructura

| Archivo | Qué contiene |
|---|---|
| `main.py` | entrada por línea de comandos |
| `test_parte1.py` | verificación contra los casos del enunciado |
| `estaciones/instancia.py` | lectura de los cinco archivos de una instancia |
| `estaciones/grafo.py` | Dijkstra sobre la red vial dirigida |
| `estaciones/parte1.py` | costo y alcance de cada par (lote, tipo) |
| `estaciones/informe.py` | impresión de resultados en consola |
| `instancias/` | datos de entrada (`pequena`, `comuna`, `ciudad`) |
| `practica_estaciones.ipynb` | enunciado del proyecto |

Los archivos de `instancias/` son CSV de texto plano, no de Excel. Conviene no
abrirlos y guardarlos con Excel: con Windows en español, Excel puede cambiar el
separador decimal y partir las columnas.

## Decisiones de implementación

**Un solo Dijkstra por lote sirve para los tres tipos.** El radio más grande es el de
bomberos (3.000 m), así que se corre Dijkstra una vez desde el nodo del lote cortando en
ese radio máximo y del mismo resultado se filtran los tres radios. En `ciudad` son 80
ejecuciones y no 240.

**El corte en el radio máximo es lo que da la velocidad.** Sin él, cada lote recorrería
los 27.568 nodos de la red; con él, Dijkstra no sale del vecindario útil del lote.

**El grafo se recorre en el sentido estación → incidente.** La regla 4 mide la distancia
desde la estación hasta el incidente, porque es el vehículo de la estación el que se
desplaza. Recorrerlo al revés daría coberturas distintas en toda calle de un solo
sentido.

**Las distancias se manejan en decímetros con enteros.** Las longitudes de los tramos
traen un decimal, así que multiplicar por 10 da enteros exactos. Con flotantes, una suma
como `283.2 + 416.8 + ...` puede dar `1000.0000000001` y dejar fuera del radio de
1.000 m un incidente que sí debía contar.

## Estado

| Parte | Estado |
|---|---|
| 1. Alcance y costo de cada estación posible | lista y verificada |
| 2. Heurística base y heurísticas propias | pendiente |
| 3. La mejor propuesta posible | pendiente |
| 4. Propuesta para el concejo | pendiente |

### Resultados de la Parte 1

| Instancia | Pares (lote, tipo) | Tiempo | Valor máximo alcanzable |
|---|---|---|---|
| `pequena` | 15 | < 0,01 s | 42 |
| `comuna` | 45 | 0,05 s | 1.669 |
| `ciudad` | 240 | 0,42 s | 9.800 |

El límite del enunciado para `ciudad` es un minuto.

La última columna es la suma de pesos de todos los incidentes que alguna estación
posible podría cubrir, ignorando el presupuesto. Es el techo contra el cual comparar
las heurísticas de la Parte 2 y el óptimo de la Parte 3.
