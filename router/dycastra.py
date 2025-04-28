import json

def dijkstra(origem, lsdb):
    # 1. Monta o grafo, mas só incluindo vizinhos com LSA presente
    grafo = {}
    for router_id, lsa in lsdb.items():
        vizinhos = {}
        for viz_entry in lsa["vizinhos"].values():
            ip_viz, custo = viz_entry
            # só adiciona se esse vizinho já tiver LSA no lsdb
            if ip_viz in lsdb:
                vizinhos[ip_viz] = custo
        grafo[router_id] = vizinhos

    # 2. Inicializa Dijkstra
    dist = {r: float('inf') for r in grafo}
    prev = {r: None for r in grafo}
    dist[origem] = 0
    visitados = set()

    while len(visitados) < len(grafo):
        u = min((r for r in grafo if r not in visitados), key=lambda r: dist[r])
        visitados.add(u)
        for v, custo in grafo[u].items():
            # agora v sempre estará em dist
            if dist[u] + custo < dist[v]:
                dist[v] = dist[u] + custo
                prev[v] = u

    # 3. Monta tabela de rotas
    tabela = {}
    for destino in grafo:
        if destino == origem or prev[destino] is None:
            continue
        next_hop = destino
        while prev[next_hop] != origem:
            next_hop = prev[next_hop]
        tabela[destino] = next_hop

    return tabela


if __name__ == "__main__":
    lsdb = {
        "172.20.2.3": {
            "id": "172.20.2.3",
            "vizinhos": {
                "router1": [
                    "172.20.1.3",
                    0.0034530162811279297
                ],
                "router3": [
                    "172.20.3.3",
                    0.0012178421020507812
                ]
            },
            "seq": 13701
        },
        "172.20.3.3": {
            "id": "172.20.3.3",
            "vizinhos": {
                "router2": [
                    "172.20.2.3",
                    0.003142833709716797
                ],
                "router4": [
                    "172.20.4.3",
                    0.0016400814056396484
                ]
            },
            "seq": 13351
        },
        "172.20.1.3": {
            "id": "172.20.1.3",
            "vizinhos": {
                "router5": [
                    "172.20.5.3",
                    0.012853384017944336
                ],
                "router2": [
                    "172.20.2.3",
                    0.00501561164855957
                ]
            },
            "seq": 13584
        },
        "172.20.5.3": {
            "id": "172.20.5.3",
            "vizinhos": {
                "router1": [
                    "172.20.1.3",
                    0.005136013031005859
                ],
                "router4": [
                    "172.20.4.3",
                    0.0030078887939453125
                ]
            },
            "seq": 13675
        },
        "172.20.4.3": {
            "id": "172.20.4.3",
            "vizinhos": {
                "router3": [
                    "172.20.3.3",
                    0.005071878433227539
                ],
                "router5": [
                    "172.20.5.3",
                    0.011375188827514648
                ]
            },
            "seq": 13770
        }
    }

    # print("LSDB:", json.dumps(lsdb, indent=2))
    print(dijkstra("172.20.1.3", lsdb))