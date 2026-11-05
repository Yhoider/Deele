"""Caminos minimos sobre la red vial dirigida.

Unica dependencia: `heapq`, que el enunciado permite expresamente. No se usa
ninguna libreria que calcule rutas o distancias en grafos.
"""

from heapq import heappop, heappush


def dijkstra(grafo, origen, corte):
    """Distancias minimas desde `origen`, respetando el sentido de los tramos.

    Devuelve solo los nodos que quedan a distancia menor o igual que `corte`.

    El sentido importa: la regla 4 del enunciado mide la distancia *desde la
    estacion hasta el incidente*, porque es el vehiculo de la estacion el que se
    desplaza. Por eso se recorren las aristas tal como estan escritas, de
    `origen` a `destino`. Recorrerlas al reves daria coberturas distintas en
    todas las calles de un solo sentido.

    El `corte` es lo que hace rapido el calculo: Dijkstra se detiene en el
    vecindario util del lote en lugar de recorrer la red completa. En `ciudad`
    eso es la diferencia entre mirar unos miles de nodos y mirar los 27.568.

    Implementacion clasica con monticulo binario: se extrae siempre el nodo
    pendiente mas cercano y se relajan sus aristas de salida. En lugar de
    actualizar prioridades dentro del monticulo (que `heapq` no permite), se
    insertan entradas nuevas y las obsoletas se descartan al extraerlas.

    Parametros
    ----------
    grafo : dict
        Lista de adyacencia `{nodo: [(destino, peso), ...]}`.
    origen : int
        Nodo desde donde se mide.
    corte : int
        Distancia maxima a explorar, en las mismas unidades que los pesos.

    Devuelve
    --------
    dict `{nodo: distancia}` con los nodos alcanzables a distancia <= corte.
    """
    if origen not in grafo:
        return {}

    dist = {origen: 0}
    monticulo = [(0, origen)]
    while monticulo:
        d, u = heappop(monticulo)
        # Entrada obsoleta: este nodo ya salio del monticulo con una distancia
        # menor, asi que no hay nada que relajar.
        if d > dist.get(u, d + 1):
            continue
        for v, peso in grafo[u]:
            nueva = d + peso
            if nueva <= corte and nueva < dist.get(v, nueva + 1):
                dist[v] = nueva
                heappush(monticulo, (nueva, v))
    return dist
