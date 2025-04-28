import yaml

def generate_docker_compose(num_subnets):
    docker_compose = {
        'services': {},
        'networks': {}
    }

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
            'environment': [
                f"vizinhos={','. join(vizinhos)}",
                f"my_ip={my_ip}",
                f"my_name={router_name}"
            ],
            'networks': networks,
            'cap_add': [
                'NET_ADMIN'
            ],
            'command': f'/bin/bash -c "ip route del default && ip route add default via {my_ip} && python router.py"'
        }

        # Gerar hosts para cada subrede
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
                'command': f'/bin/bash -c "ip route del default && ip route add default via {my_ip} dev eth0 && python host.py"',
                'cap_add': [
                    'NET_ADMIN'
                ]
            }

    return docker_compose

def save_to_file(data, filename):
    with open(filename, 'w') as file:
        yaml.dump(data, file, default_flow_style=False, sort_keys=False)

if __name__ == "__main__":
    try:
        num_subnets = int(input("Digite o número de sub-redes: "))
        if num_subnets < 1:
            raise ValueError("Deve haver pelo menos 1 sub-rede")

        docker_compose = generate_docker_compose(num_subnets)
        save_to_file(docker_compose, 'docker-compose.yml')
        print("Arquivo docker-compose.yml gerado com sucesso!")

    except ValueError as e:
        print(f"Erro: {e}")
