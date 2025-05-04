"""
Teste de Conectividade Entre Hosts e Roteadores
---------------------------------------------
Este script testa a conectividade entre hosts e roteadores na rede
através de pings em paralelo, verificando se os hosts conseguem
alcançar roteadores que não estão diretamente conectados.
"""

import os
import threading
import time

# Cores para output
class Colors:
    """Classe para definição de cores no terminal."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[0;33m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'

CPU_COUNT = os.cpu_count() or 1
MAX_WORKERS = CPU_COUNT * 4

def get_users():
    """
    Obtém a lista de todos os hosts em execução no ambiente Docker.
    
    Returns:
        list: Lista ordenada com os nomes dos containers de hosts
    """
    out = os.popen("docker ps --filter 'name=host' --format '{{.Names}}'").read()
    return sorted(out.splitlines())

def get_routers():
    """
    Obtém a lista de todos os roteadores em execução no ambiente Docker.
    
    Returns:
        list: Lista ordenada com os nomes dos containers de roteadores
    """
    out = os.popen("docker ps --filter 'name=router' --format '{{.Names}}'").read()
    return sorted(out.splitlines())

def extract_num_router(name):
    """
    Extrai o número identificador do roteador a partir do nome do container.
    
    Args:
        name (str): Nome do container do roteador
        
    Returns:
        str: Número do roteador
    """
    pre = name.split('-')[1]
    result = pre.split('router')[1]
    return result
  
def extract_num_host(name):
    """
    Extrai o número identificador do host a partir do nome do container.
    
    Args:
        name (str): Nome do container do host
        
    Returns:
        str: Número do host
    """
    pre = name.split('-')[1]
    result = pre.split('host')[1]
    return result

def ping_task(frm, to, ip, results, lock_thread):
    """
    Executa um ping de um host para um roteador e registra o resultado.
    
    Args:
        frm (str): Nome do container do host de origem
        to (str): Nome do container do roteador de destino
        ip (str): Endereço IP do roteador para o ping
        results (list): Lista compartilhada para armazenar resultados
        lock_thread (threading.Lock): Lock para controle de acesso à lista de resultados
    """
    start = time.time()
    cmd = f"docker exec {frm} ping -c 1 -W 0.1 {ip} > /dev/null 2>&1"
    print(f"{Colors.YELLOW}{cmd}{Colors.NC}")
    code = os.system(cmd)
    elapsed = time.time() - start
    success = (code == 0)
    
    with lock_thread:
        results.append((frm, to, success, elapsed))

def main():
    """
    Função principal que coordena o teste de conectividade entre hosts e roteadores.
    Executa pings dos hosts para todos os roteadores e apresenta resultados.
    """
    routers = get_routers()
    if not routers:
        print(f"{Colors.RED}Erro: nenhum roteador rodando. Execute 'make up'.{Colors.NC}")
        return

    users = get_users()
    if not users:
        print(f"{Colors.RED}Erro: nenhum host rodando. Execute 'make up'.{Colors.NC}")
        return
    
    tasks = [(f, t, f"172.20.{extract_num_router(t)}.3") for f in users for t in routers if f != t]
    
    results = []
    threads = []
    lock_thread = threading.Lock()
    
    for frm, to, ip in tasks:
        while len(threads) >= MAX_WORKERS:
            threads = [thr for thr in threads if thr.is_alive()]

        thread = threading.Thread(target=ping_task, args=(frm, to, ip, results, lock_thread))
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()
    
    summary = {}
    
    for frm, to, ok, tempo in results:
        summary.setdefault(frm, []).append((to, ok, tempo))
    
    total_ok = 0
    total = len(results)
    
    for frm in sorted(summary):
        print(f"\n{Colors.CYAN}=== Host {frm} ==={Colors.NC}")
        
        for to, ok, tempo in summary[frm]:
            status_color = Colors.GREEN if ok else Colors.RED
            status = "OK" if ok else "Falha"
            
            print(f"{status_color}{frm} -> {to}: {status} ({tempo:.2f}s){Colors.NC}")
            if ok:
                total_ok += 1
            
    print(f"\n{Colors.MAGENTA}Total de pings: {total}, Sucessos: {total_ok}, Falhas: {total - total_ok}{Colors.NC}")

if __name__ == "__main__":
    main()
