#!/bin/bash

# Cores para output
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para obter o nome real do container
get_container_name() {
    local router_num=$1
    docker ps --filter "name=router$router_num" --format "{{.Names}}" | head -n 1
}

# Função para executar comando em um container
run_in_container() {
    local container=$1
    local command=$2
    docker exec $container $command
}

# Função para mostrar a tabela de roteamento de um container
show_routing_table() {
    local container=$1
    local router_num=$2
    
    echo -e "${YELLOW}=== Tabela de Roteamento: $container (Router $router_num) ===${NC}"
    run_in_container $container "ip route"
    echo ""
}

# Verifica se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "Erro: Docker não está rodando"
    exit 1
fi

# Conta quantos roteadores existem
num_routers=$(docker ps --filter "name=router" --format "{{.Names}}" | wc -l)

if [ $num_routers -eq 0 ]; then
    echo "Erro: Nenhum roteador está rodando. Execute 'make up' primeiro."
    exit 1
fi

echo "Encontrados $num_routers roteadores. Mostrando tabelas de roteamento..."
echo ""

# Mostra a tabela de roteamento de cada roteador
for i in $(seq 1 $num_routers); do
    container_name=$(get_container_name $i)
    if [ -n "$container_name" ]; then
        show_routing_table $container_name $i
    fi
done 