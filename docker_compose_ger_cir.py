"""
Gerador de Docker Compose para Topologia em Anel
-----------------------------------------------
Este script gera um arquivo docker-compose.yml configurando uma rede
com topologia em anel (circular), onde cada roteador se conecta aos
roteadores adjacentes, fechando um círculo completo.
"""

import yaml
import sys
import os
import psutil

def generate_docker_compose(num_subnets, with_hosts=False, qtd_roteadores_test=0):
    """
    Gera a configuração do Docker Compose para a topologia em anel.

    Args:
        num_subnets (int): Número de subredes (e consequentemente, de roteadores)
        with_hosts (bool): Se deve incluir hosts nas subredes
        qtd_roteadores_test (int): Quantidade de roteadores para teste

    Returns:
        dict: Configuração completa para o docker-compose.yml
    """
    docker_compose = {
        'services': {},
        'networks': {}
    }

    # Detectar recursos do sistema
    total_cpus = os.cpu_count()
    total_memory = psutil.virtual_memory().total // (1024 * 1024)

    num_routers = num_subnets
    num_hosts = num_subnets * 2 if with_hosts else 0
    total_containers = num_routers + num_hosts
    
    max_cpus = total_cpus * 0.8
    max_memory = total_memory * 0.8
    
    if qtd_roteadores_test != 0:
        cpu_per_container = max_cpus /( qtd_roteadores_test + num_hosts)
        mem_per_container = f"{int(max_memory / (qtd_roteadores_test + num_hosts))}M"
    else:
        cpu_per_container = max_cpus / total_containers
        mem_per_container = f"{int(max_memory / total_containers)}M"

    # Criar todas as redes
    for i in range(1, num_subnets + 1):
        subnet_name = f"subnet_{i}"
        docker_compose['networks'][subnet_name] = {
            'driver': 'bridge',
            'ipam': {
                'config': [{
                    'subnet': f'172.20.{i}.0/24',
                    'gateway': f'172.20.{i}.1',
                }]
            }
        }

    # Criar roteadores
    for i in range(1, num_subnets + 1):
        router_name = f"router{i}"
        gateway = f'172.20.{i}.1'
        my_ip = f'172.20.{i}.3'

        vizinhos = []
        networks = {}

        if i == 1:
            vizinhos.append(f"[router{num_subnets}, 172.20.{num_subnets}.3, 1]")
            networks[f"subnet_{num_subnets}"] = {
                'ipv4_address': f'172.20.{num_subnets}.2'
            }
        elif i == num_subnets:
            vizinhos.append(f"[router1, 172.20.1.3, 1]")
            networks[f"subnet_1"] = {
                'ipv4_address': f'172.20.1.4'
            }

        if i > 1:
            vizinhos.append(f"[router{i-1}, 172.20.{i-1}.3, 1]")
            networks[f"subnet_{i-1}"] = {
                'ipv4_address': f'172.20.{i-1}.2'
            }

        if i < num_subnets:
            vizinhos.append(f"[router{i+1}, 172.20.{i+1}.3, 1]")
            networks[f"subnet_{i+1}"] = {
                'ipv4_address': f'172.20.{i+1}.4'
            }

        networks[f"subnet_{i}"] = {
            'ipv4_address': my_ip
        }

        docker_compose['services'][router_name] = {
            'build': {
                'context': './router',
                'dockerfile': 'Dockerfile'
            },
            'volumes': [
                './router:/app'
            ],
            'environment': [
                f"vizinhos={','.join(vizinhos)}",
                f"my_ip={my_ip}",
                f"my_name={router_name}"
            ],
            'networks': networks,
            'cap_add': ['NET_ADMIN'],
            'command': f'/bin/bash -c "ip route del default && ip route add default via {my_ip} && python router.py"',
            'cpus': str(cpu_per_container),
            'mem_limit': mem_per_container
        }

        if with_hosts:
            for host, ip_suffix in [(0, 10), (1, 11)]:
                host_name = f"host{i}{host}"
                docker_compose['services'][host_name] = {
                    'build': {
                        'context': './host',
                        'dockerfile': 'Dockerfile'
                    },
                    'networks': {
                        f"subnet_{i}": {
                            'ipv4_address': f'172.20.{i}.{ip_suffix}'
                        }
                    },
                    'depends_on': [f'router{i}'],
                    'command': f'/bin/bash -c "ip route del default && ip route add default via {my_ip} dev eth0 && sleep infinity"',
                    'cap_add': ['NET_ADMIN'],
                    'cpus': str(cpu_per_container),
                    'mem_limit': mem_per_container
                }

    return docker_compose

def save_to_file(data, filename):
    """
    Salva a configuração gerada em um arquivo YAML.

    Args:
        data (dict): Configuração do Docker Compose
        filename (str): Nome do arquivo a ser criado
    """
    with open(filename, 'w') as file:
        yaml.dump(data, file, default_flow_style=False, sort_keys=False)

if __name__ == "__main__":
    """
    Ponto de entrada do script. Solicita o número de subredes ao usuário
    e gera o arquivo docker-compose.yml com a topologia em anel.
    """
    try:
        args = sys.argv[1:]

        num_subnets = int(args[0]) if args else int(input("Digite o número de sub-redes: "))
        with_hosts = bool(int(args[1])) if len(args) > 1 else bool(int(input("Deseja incluir hosts nas sub-redes? (1 para sim, 0 para não): ")))
        
        if len(args) > 2:
            qtd_maxima_roteadores_para_test = int(args[2])
        else:
            qtd_maxima_roteadores_para_test = 0

        if num_subnets < 1:
            raise ValueError("Deve haver pelo menos 1 sub-rede")

        docker_compose = generate_docker_compose(num_subnets, with_hosts, qtd_maxima_roteadores_para_test)
        save_to_file(docker_compose, 'docker-compose.yml')
        print("Arquivo docker-compose.yml gerado com sucesso!")

    except ValueError as e:
        print(f"Erro: {e}")
