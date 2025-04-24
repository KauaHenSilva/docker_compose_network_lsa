import json

def dijkstra(origem, lsdb: dict[str, dict[str, dict[str, int]]]) -> dict[str, str]:
    # 1. Construir grafo ignorando roteadores inativos e seus vizinhos
    grafo = {}
    for router_id, lsa in lsdb.items():
        vizinhos = {}
        for _, vizinho_info in lsa["vizinhos"].items():
            vizinhos[vizinho_info[0]] = vizinho_info[1]
        grafo[router_id] = vizinhos
        
    # 2. Inicializar estruturas
    distancias = {router: float('inf') for router in grafo}
    distancias[origem] = 0
    anteriores = {router: None for router in grafo}
    visitados = set()

    while len(visitados) < len(grafo):
        atual = min((router for router in grafo if router not in visitados), key=lambda r: distancias[r])
        for vizinho, custo in grafo[atual].items():
            if vizinho not in visitados:
                if distancias[atual] == float('inf'):
                    nova_distancia = custo
                else:
                    nova_distancia = distancias[atual] + custo
                    
                if vizinho in distancias.keys() and nova_distancia < distancias[vizinho]:
                    distancias[vizinho] = nova_distancia
                    anteriores[vizinho] = atual
        
        visitados.add(atual)

    # 4. Construir tabela de rotas (descobrir próximo salto)
    tabela_rotas = {}
    for destino in grafo:
        if destino == origem:
            continue
        atual = destino
        anterior = anteriores[atual]
        if anterior is None:
            continue
        while anteriores[anterior] is not None and anteriores[anterior] != origem:
            anterior = anteriores[anterior]
        if anteriores[anterior] == origem:
            tabela_rotas[destino] = anterior
        else:
            tabela_rotas[destino] = anterior if anterior != destino else atual

    tabela_rotas = {destino: prox for destino, prox in tabela_rotas.items() if prox != origem}
    return tabela_rotas

if __name__ == "__main__":
    lsdb = {
        '172.20.2.3': {
            'id': '172.20.2.3',
            'vizinhos': {
                'router1': ['172.20.1.3', 1],
                'router3': ['172.20.3.3', 1]
            },
            'seq': 2
        },
        '172.20.3.3': {
            'id': '172.20.3.3',
            'vizinhos': {
                'router2': ['172.20.2.3', 1],
                'router4': ['172.20.4.3', 1]
            },
            'seq': 2
        },
        '172.20.4.3': {
            'id': '172.20.4.3',
            'vizinhos': {
                'router3': ['172.20.3.3', 1],
                'router5': ['172.20.5.3', 1]
            },
            'seq': 2
        },
        '172.20.5.3': {
            'id': '172.20.5.3',
            'vizinhos': {
                'router4': ['172.20.4.3', 1]
            },
            'seq': 2
        },
        '172.20.1.3': {
            'id': '172.20.1.3',
            'vizinhos': {
                'router2': ['172.20.2.3', 1]
            },
            'seq': 2
        }
    }

    print("LSDB:", json.dumps(lsdb, indent=2))
    print(dijkstra("router1", lsdb))