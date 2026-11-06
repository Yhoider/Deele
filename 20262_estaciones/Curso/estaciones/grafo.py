from heapq import heappop, heappush


def dijkstra(grafo: dict[int, list[tuple[int, int]]], origen: int, corte: int) -> dict[int, int]:
   
    if origen not in grafo:
        return {}

    dist = {origen: 0}
    monticulo = [(0, origen)]
    while monticulo:
        d, u = heappop(monticulo)
        
        if d > dist.get(u, d + 1):
            continue
        for v, peso in grafo[u]:
            nueva = d + peso
            if nueva <= corte and nueva < dist.get(v, nueva + 1):
                dist[v] = nueva
                heappush(monticulo, (nueva, v))
    return dist
