import subprocess
import sys
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

def get_routing_table(container):
    """Obtém a tabela de roteamento de um container."""
    cmd = f"docker exec {container} ip route"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def main():
    # Verifica se o Docker está rodando
    try:
        subprocess.run("docker info", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print(f"{Colors.RED}Erro: Docker não está rodando{Colors.NC}")
        sys.exit(1)
    
    # Obtém os roteadores
    routers = get_router_containers()
    if not routers:
        print(f"{Colors.RED}Erro: Nenhum roteador está rodando. Execute 'make up' primeiro.{Colors.NC}")
        sys.exit(1)
    
    print(f"{Colors.BLUE}Encontrados {len(routers)} roteadores. Mostrando tabelas de roteamento...{Colors.NC}")
    print()
    
    for router in sorted(routers, key=lambda x: extract_router_number(x)):
        router_num = extract_router_number(router)
        print(f"{Colors.BOLD}{Colors.CYAN}=== Tabela de Roteamento do Router {router_num} ==={Colors.NC}")
        
        routing_table = get_routing_table(router)
        
        if routing_table:
            lines = routing_table.split('\n')
            for line in lines:
                if 'default' in line:
                    print(f"{Colors.YELLOW}{line}{Colors.NC}")
                else:
                    print(line)
        else:
            print(f"{Colors.RED}Nenhuma rota encontrada.{Colors.NC}")
        
        print()

if __name__ == "__main__":
    main() 