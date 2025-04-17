#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Função para testar ping entre dois roteadores
test_ping() {
    local from_router=$1
    local to_router=$2
    local to_ip=$3
    local from_num=$4
    local to_num=$5
    local result_file=$6
    
    local result
    if run_in_container $from_router "ping -c 1 $to_ip" > /dev/null 2>&1; then
        result="success"
    else
        result="fail"
    fi
    
    # Salva o resultado em um arquivo temporário
    echo "$from_num $to_num $result" >> "$result_file"
}

# Função para mostrar o resumo dos testes
show_summary() {
    local result_file=$1
    local total_tests=$(wc -l < "$result_file")
    local successful_tests=$(grep "success" "$result_file" | wc -l)
    
    echo ""
    echo -e "${BLUE}=== Resultados dos Testes de Conectividade ===${NC}"
    echo ""
    
    # Mostra os resultados individuais
    while read -r from to result; do
        if [ "$result" = "success" ]; then
            echo -e "${GREEN}✓ Router $from → Router $to: Conectado${NC}"
        else
            echo -e "${RED}✗ Router $from → Router $to: Falhou${NC}"
        fi
    done < "$result_file"
    
    echo ""
    echo -e "${BLUE}=== Resumo ===${NC}"
    echo -e "Total de testes: $total_tests"
    echo -e "Testes bem-sucedidos: $successful_tests"
    echo -e "Testes falhados: $((total_tests - successful_tests))"
    
    if [ $successful_tests -eq $total_tests ]; then
        echo -e "${GREEN}✓ Todos os testes de conectividade foram bem-sucedidos!${NC}"
    else
        echo -e "${RED}✗ Alguns testes de conectividade falharam.${NC}"
    fi
}

# Verifica se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Erro: Docker não está rodando${NC}"
    exit 1
fi

# Conta quantos roteadores existem
num_routers=$(docker ps --filter "name=router" --format "{{.Names}}" | wc -l)

if [ $num_routers -eq 0 ]; then
    echo -e "${RED}Erro: Nenhum roteador está rodando. Execute 'make up' primeiro.${NC}"
    exit 1
fi

echo -e "${BLUE}Encontrados $num_routers roteadores. Iniciando testes de conectividade...${NC}"
echo -e "${YELLOW}Executando testes em paralelo...${NC}"

# Arquivo temporário para armazenar resultados
result_file=$(mktemp)
trap 'rm -f "$result_file"' EXIT

# Array para armazenar os PIDs dos processos em background
declare -a pids

# Testa conectividade de cada roteador para todos os outros
for i in $(seq 1 $num_routers); do
    current_container=$(get_container_name $i)
    
    if [ -z "$current_container" ]; then
        echo -e "${RED}Erro: Não foi possível encontrar o container para o roteador $i${NC}"
        continue
    fi
    
    # Testa ping para todos os outros roteadores
    for j in $(seq 1 $num_routers); do
        # Pula se for o mesmo roteador
        if [ $i -eq $j ]; then
            continue
        fi
        
        next_container=$(get_container_name $j)
        
        if [ -z "$next_container" ]; then
            echo -e "${RED}Erro: Não foi possível encontrar o container para o roteador $j${NC}"
            continue
        fi
        
        # IP para teste
        next_ip="172.20.$j.3"
        
        # Executa o teste em background
        test_ping $current_container $next_container $next_ip $i $j "$result_file" &
        pids+=($!)
    done
done

# Espera todos os processos terminarem
for pid in "${pids[@]}"; do
    wait $pid
done

# Mostra o resumo dos testes
show_summary "$result_file" 