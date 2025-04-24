import subprocess
import sys
import re
import time
import concurrent.futures
import os
import multiprocessing
from typing import List, Tuple, Dict, Any

# Cores para output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[0;33m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'  # No Color

# Configurações extremas para uso máximo de CPU
CPU_COUNT = os.cpu_count() or 4
MAX_WORKERS = CPU_COUNT * 4  # Multiplicador agressivo para garantir uso total da CPU
BATCH_SIZE = 20  # Tamanhos menores de batch para distribuir melhor o trabalho

def get_routers():
    """Obtém todos os roteadores em execução."""
    cmd = "docker ps --filter 'name=router' --format '{{.Names}}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    routers = [r for r in result.stdout.strip().split('\n') if r]
    return sorted(routers, key=lambda x: int(extract_router_number(x)))

def extract_router_number(container_name):
    """Extrai o número do roteador do nome do container."""
    # Tenta encontrar um número após 'router' no nome
    match = re.search(r'router(\d+)', container_name)
    if match:
        return match.group(1)
    
    # Se não encontrar, tenta extrair o último número do nome
    match = re.search(r'(\d+)(?:-\d+)?$', container_name)
    if match:
        return match.group(1)
    
    # Se não conseguir extrair, retorna o nome completo
    return container_name

def parallel_ping(args):
    """Executa um ping em paralelo (função compatível com multiprocessing)."""
    from_router, to_router, to_ip = args
    from_num = extract_router_number(from_router)
    to_num = extract_router_number(to_router)
    
    # Executa o ping com timeout mínimo para rapidez
    cmd = f"docker exec {from_router} ping -c 1 -W 0.1 -q {to_ip} > /dev/null 2>&1"
    
    start_time = time.time()
    result = subprocess.run(cmd, shell=True)
    elapsed = time.time() - start_time
    success = 1 if result.returncode == 0 else 0
    
    return from_num, to_num, success, elapsed

def batch_ping_parallel(tasks_chunk):
    """Executa um conjunto de pings em paralelo usando processos."""
    with multiprocessing.Pool(processes=CPU_COUNT) as pool:
        return pool.map(parallel_ping, tasks_chunk)

def run_ultra_parallel_tests(routers):
    """Executa todos os testes em paralelo com uso máximo de CPU."""
    print(f"{Colors.MAGENTA}Testando com {MAX_WORKERS} workers e {CPU_COUNT} processos por worker para uso máximo da CPU{Colors.NC}")
    
    # Prepara todas as tarefas
    all_tasks = []
    for from_router in routers:
        for to_router in routers:
            if from_router == to_router:
                continue
            
            to_num = extract_router_number(to_router)
            to_ip = f"172.20.{to_num}.3"
            all_tasks.append((from_router, to_router, to_ip))
    
    # Divide as tarefas em blocos para processamento paralelo
    total_tasks = len(all_tasks)
    chunk_size = max(1, total_tasks // MAX_WORKERS)
    task_chunks = [all_tasks[i:i+chunk_size] for i in range(0, total_tasks, chunk_size)]
    
    print(f"{Colors.YELLOW}Total: {total_tasks} testes divididos em {len(task_chunks)} chunks{Colors.NC}")
    
    results = []
    completed = 0
    
    # Usar ThreadPoolExecutor para distribuir os chunks entre threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_chunk = {executor.submit(batch_ping_parallel, chunk): i for i, chunk in enumerate(task_chunks)}
        
        # Processar resultados à medida que chegam
        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk_idx = future_to_chunk[future]
            try:
                chunk_results = future.result()
                results.extend(chunk_results)
                
                # Atualiza contador de progresso
                completed += len(chunk_results)
                progress = int(completed * 100 / total_tasks)
                print(f"{Colors.YELLOW}Progresso: {completed}/{total_tasks} testes ({progress}%){Colors.NC}", end='\r')
                
            except Exception as e:
                print(f"{Colors.RED}Erro no chunk {chunk_idx}: {e}{Colors.NC}")
    
    print("\n")  # Nova linha após barra de progresso
    
    # Organiza resultados por roteador
    results_by_router = {}
    for result in results:
        from_num, to_num, success, elapsed = result
        if from_num not in results_by_router:
            results_by_router[from_num] = []
        results_by_router[from_num].append((from_num, to_num, success, elapsed))
    
    # Exibe resultados por roteador
    total_success = 0
    total_tests = 0
    
    for from_num, router_results in sorted(results_by_router.items()):
        print(f"\n{Colors.CYAN}=== Resultados Router {from_num} ==={Colors.NC}")
        
        successful = 0
        
        # Ordena por número do roteador destino
        router_results.sort(key=lambda x: x[1])
        
        for _, to_num, success, _ in router_results:
            if success > 0:
                print(f"{Colors.GREEN}✓ Router {from_num} → Router {to_num}: Conectado{Colors.NC}")
                successful += 1
            else:
                print(f"{Colors.RED}✗ Router {from_num} → Router {to_num}: Falhou{Colors.NC}")
        
        total = len(router_results)
        print(f"{Colors.BLUE}Resumo Router {from_num}: {successful}/{total} conexões{Colors.NC}")
        
        total_success += successful
        total_tests += total
    
    return results, total_success, total_tests

def main():
    # Pressiona a CPU para garantir que esteja no máximo desempenho
    print(f"{Colors.MAGENTA}Iniciando teste de carga máxima com {CPU_COUNT} CPUs e {MAX_WORKERS} workers{Colors.NC}")
    
    start_time = time.time()
    
    # Verifica se o Docker está rodando
    try:
        subprocess.run("docker info", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print(f"{Colors.RED}Erro: Docker não está rodando{Colors.NC}")
        sys.exit(1)
    
    # Obtém os roteadores
    routers = get_routers()
    if not routers:
        print(f"{Colors.RED}Erro: Nenhum roteador está rodando. Execute 'make up' primeiro.{Colors.NC}")
        sys.exit(1)
    
    print(f"{Colors.BLUE}Encontrados {len(routers)} roteadores. Usando {MAX_WORKERS} threads e {CPU_COUNT} processos.{Colors.NC}")
    
    # Executa os testes extremamente paralelizados
    all_results, total_success, total_tests = run_ultra_parallel_tests(routers)
    
    # Resumo geral
    total_time = time.time() - start_time
    print(f"\n{Colors.BLUE}=== Resumo Geral ==={Colors.NC}")
    print(f"Total de conexões: {total_tests}")
    print(f"Conexões bem-sucedidas: {total_success}")
    print(f"Conexões falhadas: {total_tests - total_success}")
    print(f"{Colors.YELLOW}Tempo total de execução: {total_time:.2f} segundos{Colors.NC}")
    
    if total_success == total_tests:
        print(f"{Colors.GREEN}✓ Todas as conexões estão funcionando!{Colors.NC}")
    else:
        print(f"{Colors.RED}✗ Algumas conexões falharam.{Colors.NC}")

if __name__ == "__main__":
    # Definir a política de início para spawn para evitar problemas com fork em alguns sistemas
    multiprocessing.set_start_method('spawn', force=True)
    main() 