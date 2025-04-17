
import subprocess
import threading
import queue
import sys
import re

# Cores para output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def get_routers():
    """Obtém todos os roteadores em execução."""
    cmd = "docker ps --filter 'name=router' --format '{{.Names}}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return [r for r in result.stdout.strip().split('\n') if r]

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

def ping_test(from_router, to_router, to_ip, results):
    """Testa a conectividade entre dois roteadores."""
    # Extrai os números dos roteadores
    from_num = extract_router_number(from_router)
    to_num = extract_router_number(to_router)
    
    # Executa o ping
    cmd = f"docker exec {from_router} ping -c 3 -W 1 {to_ip}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    # Conta pings bem-sucedidos
    success_count = result.stdout.count("bytes from")
    
    # Adiciona o resultado à fila
    results.put((from_num, to_num, success_count))

def main():
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
    
    print(f"{Colors.BLUE}Encontrados {len(routers)} roteadores. Testando conexões...{Colors.NC}")
    
    # Fila para resultados
    results = queue.Queue()
    threads = []
    
    # Testa todas as conexões possíveis
    for from_router in routers:
        for to_router in routers:
            # Pula se for o mesmo roteador
            if from_router == to_router:
                continue
            
            # IP para teste
            to_num = extract_router_number(to_router)
            to_ip = f"172.20.{to_num}.3"
            
            # Inicia thread para o teste
            thread = threading.Thread(
                target=ping_test,
                args=(from_router, to_router, to_ip, results)
            )
            threads.append(thread)
            thread.start()
    
    # Espera todas as threads terminarem
    for thread in threads:
        thread.join()
    
    # Coleta resultados
    test_results = []
    while not results.empty():
        test_results.append(results.get())
    
    # Ordena resultados (usando strings para evitar erros de conversão)
    test_results.sort(key=lambda x: (x[0], x[1]))
    
    # Exibe resultados
    print(f"\n{Colors.BLUE}=== Resultados dos Testes ==={Colors.NC}")
    
    successful = 0
    for from_num, to_num, success_count in test_results:
        if success_count > 0:
            print(f"{Colors.GREEN}✓ Router {from_num} → Router {to_num}: Conectado ({success_count}/3 pings){Colors.NC}")
            successful += 1
        else:
            print(f"{Colors.RED}✗ Router {from_num} → Router {to_num}: Falhou (0/3 pings){Colors.NC}")
    
    # Resumo
    total = len(test_results)
    print(f"\n{Colors.BLUE}=== Resumo ==={Colors.NC}")
    print(f"Total de conexões: {total}")
    print(f"Conexões bem-sucedidas: {successful}")
    print(f"Conexões falhadas: {total - successful}")
    
    if successful == total:
        print(f"{Colors.GREEN}✓ Todas as conexões estão funcionando!{Colors.NC}")
    else:
        print(f"{Colors.RED}✗ Algumas conexões falharam.{Colors.NC}")

if __name__ == "__main__":
    main() 