"""
Visualizador de Tabelas de Roteamento
------------------------------------
Este script exibe as tabelas de roteamento de todos os roteadores
em execução no ambiente Docker, facilitando a depuração e validação
do estado da rede.
"""

import sys
import psutil
import os
import threading
import time
import re

# Cores para output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

def get_router_containers():
    """Obtém todos os containers de roteadores em execução."""
    out = os.popen("docker ps --filter 'name=router' --format '{{.Names}}'").read()
    return sorted(out.splitlines())

def get_routing_table(container, qtd_routers):
    """Obtém a tabela de roteamento de um container."""
    while True:
        cmd = f"docker exec {container} ip route"
        qtd_connexao = len(os.popen(cmd).read().splitlines())
        if qtd_connexao == qtd_routers + 1:
            break

def init_routers():
    """
    Inicializa os roteadores, derrubando e reiniciando os containers.
    """

def get_packet_stats(container, t_qtd_pacotes_recebidos, t_qtd_pacotes_enviados, lock_thread):
    cmd = f"docker exec {container} cat /proc/net/dev"
    output = os.popen(cmd).read()

    qtd_pacotes_recebidos = 0
    qtd_pacotes_enviados = 0

    for line in output.strip().splitlines()[2:]:
        if ":" not in line:
            continue

        iface, data = line.split(":", 1)
        fields = re.findall(r'\d+', data)
        if len(fields) >= 9:
            qtd_pacotes_recebidos += int(fields[1])
            qtd_pacotes_enviados += int(fields[9])

    with lock_thread:
        t_qtd_pacotes_recebidos.append(qtd_pacotes_recebidos)
        t_qtd_pacotes_enviados.append(qtd_pacotes_enviados)
        
        
def incluir_cabecalho(if_test):
    """
    Cria o arquivo CSV e inclui o cabeçalho.
    """
    if not os.path.exists(f"dados_convergencia/{if_test}.csv"):
        os.makedirs("dados_convergencia", exist_ok=True)
        with open(f"dados_convergencia/{if_test}.csv", "w") as file:
            file.write("qtd_roteadores,tempo_convergencia,soma_rx,mediana_rx,soma_tx,mediana_tx\n")

def incluir_resultados(qtd_roteadores, tempo_convergencia, soma_rx, mediana_rx, soma_tx, mediana_tx, if_test):
    with open(f"dados_convergencia/{if_test}.csv", "a") as file:
        file.write(f"{qtd_roteadores},{tempo_convergencia},{soma_rx},{mediana_rx},{soma_tx},{mediana_tx}\n")
    

def main():
    """
    Função principal que obtém e exibe as tabelas de roteamento de todos os roteadores.
    Cada tabela é exibida com formatação colorida para facilitar a leitura.
    """

    qtd_maxima_roteadores_para_test = 100
    qtd_inicial = 10
    qtd_pulo = 10
    
    total_cpus = os.cpu_count()
    total_memory = psutil.virtual_memory().total // (1024 * 1024)

    max_cpus = total_cpus * 0.8
    max_memory = total_memory * 0.8
    
    cpu_per_container = max_cpus / ( qtd_maxima_roteadores_para_test)
    mem_per_container = f"{int(max_memory / (qtd_maxima_roteadores_para_test))}M"
    
    if_test = f"{(cpu_per_container)}_{mem_per_container}_{qtd_maxima_roteadores_para_test}"
    incluir_cabecalho(if_test)
    
    for qtd in range(qtd_inicial, qtd_maxima_roteadores_para_test + 1, qtd_pulo):
        print(f"{Colors.YELLOW}Iniciando teste com {qtd} roteadores...{Colors.NC}", end='\n\n')
        os.system(f"make ger_cir qtd={qtd} with_host=0 qtd_max_test={qtd_maxima_roteadores_para_test} > /dev/null 2>&1")
        os.system("make down > /dev/null 2>&1")
        
        os.system("make up_background > /dev/null 2>&1")
        time_init = time.time()
        
        routers = get_router_containers()
        qtd_routers = len(routers)
        print(f"{Colors.BLUE}Encontrados {qtd_routers} roteadores. Calculando o tempo de convergência...{Colors.NC}")
        
        threads = []
        for router in routers:
            thread = threading.Thread(target=get_routing_table, args=(router, qtd_routers))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        time_end = time.time();

        tempo_convergencia = time_end - time_init
        print(f"{Colors.GREEN}Tempo de convergência para {qtd_routers} roteadores: {tempo_convergencia:.2f} segundos{Colors.NC}", end='\n')

        threads_2 = []
        thread_lock = threading.Lock()
        
        t_qtd_pacotes_recebidos = []
        t_qtd_pacotes_enviados = []
        
        for router in routers:
            thread = threading.Thread(target=get_packet_stats, args=(router, t_qtd_pacotes_recebidos, t_qtd_pacotes_enviados, thread_lock))
            thread.start()
            threads_2.append(thread)
        
        for thread in threads_2:
            thread.join()
            
        soma_rx = sum(t_qtd_pacotes_recebidos)
        soma_tx = sum(t_qtd_pacotes_enviados)

        mediana_rx = t_qtd_pacotes_recebidos[len(t_qtd_pacotes_recebidos) // 2]
        mediana_tx = t_qtd_pacotes_enviados[len(t_qtd_pacotes_enviados) // 2]
        
        print(f"{Colors.GREEN}Pacotes Recebidos (total): {soma_rx}, Mediana: {mediana_rx}{Colors.NC}")
        print(f"{Colors.GREEN}Pacotes Enviados  (total): {soma_tx}, Mediana: {mediana_tx}{Colors.NC}")
        print()

        incluir_resultados(qtd_routers, tempo_convergencia, soma_rx, mediana_rx, soma_tx, mediana_tx, if_test)


if __name__ == "__main__":
    main()