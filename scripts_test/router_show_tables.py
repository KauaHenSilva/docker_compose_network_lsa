import sys
import os

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

def extract_router_number(container_name):
    """Extrai o número do roteador do nome do container."""
    # Tenta encontrar um número após 'router' no nome
    pre = container_name.split('-')[1]
    result = pre.split('router')[1]
    return result

def get_routing_table(container):
    """Obtém a tabela de roteamento de um container."""
    cmd = f"docker exec {container} ip route"
    print(f"{Colors.YELLOW}{cmd}{Colors.NC}")
    result = os.popen(cmd).read()
    return result.strip()

def main():
    # Obtém os roteadores
    routers = get_router_containers()
    if not routers:
        print(f"{Colors.RED}Erro: Nenhum roteador está rodando. Execute 'make up' primeiro.{Colors.NC}")
        sys.exit(1)
    
    print(f"{Colors.BLUE}Encontrados {len(routers)} roteadores. Mostrando tabelas de roteamento...{Colors.NC}", end='\n\n')
    
    for router in sorted(routers, key=lambda x: extract_router_number(x)):
        router_num = extract_router_number(router)
        print(f"{Colors.BOLD}{Colors.CYAN}=== Tabela de Roteamento do Router {router_num} ==={Colors.NC}")
        
        routing_table = get_routing_table(router)
        
        if routing_table:
            lines = routing_table.split('\n')
            print(f"{Colors.YELLOW}{lines[0]}{Colors.NC}")
            for line in lines[1:]:
                print(line)
        else:
            print(f"{Colors.RED}Nenhuma rota encontrada.{Colors.NC}")
        
        print(f"{Colors.BOLD}{Colors.CYAN}========================================{Colors.NC}", end='\n\n')

if __name__ == "__main__":
    main() 