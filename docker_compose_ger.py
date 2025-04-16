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
                    'subnet': f'172.20.{i}.0/24'
                }]
            }
        }

    # Criar roteadores interligados
    for i in range(1, num_subnets + 1):
        router_name = f"router{i}"

        links = []
        if i > 1:
            links.append(f"router{i-1}")
        if i < num_subnets:
            links.append(f"router{i+1}")

        networks = {}
        networks[f"subnet_{i}"] = {
            'ipv4_address': f'172.20.{i}.3'
        }
        
        if i > 1:
            networks[f"subnet_{i-1}"] = {
                'ipv4_address': f'172.20.{i-1}.2'
            }
        
        if i < num_subnets:
            networks[f"subnet_{i+1}"] = {
                'ipv4_address': f'172.20.{i+1}.4'
            }

        docker_compose['services'][router_name] = {
            'build': {
                'context': './router',
                'dockerfile': 'Dockerfile'
            },
            'environment': [
                f"router_links={','.join(links)}"
            ],
            'networks': networks
        }

    # # Gerar hosts para cada subrede
    # for i in range(1, num_subnets + 1):
    #     for host, ip_suffix in [('a', 10), ('b', 11)]:
    #         host_name = f"host{i}{host}"
    #         docker_compose['services'][host_name] = {
    #             'build': {
    #                 'context': './host',
    #                 'dockerfile': 'Dockerfile'
    #             },
    #             'networks': {
    #                 f"subnet_{i}": {
    #                     'ipv4_address': f'172.20.{i}.{ip_suffix}'
    #                 }
    #             },
    #             'depends_on': [f'router{i}']
    #         }

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
