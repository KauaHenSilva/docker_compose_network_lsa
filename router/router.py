import socket
import time
import json
import os 
import threading
import subprocess
from typing import Dict, Any, Set, Tuple, List, Optional

# Constantes globais
TIME_SLEEP = 5
DEFAULT_LSA_PORT = 5000

class Vizinho:
    """Representa um roteador vizinho na topologia de rede."""
    
    def __init__(self, hostname: str, ip: str, custo: int):
        self.hostname = hostname
        self.ip = ip
        self.custo = custo
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o objeto para dicionário para serialização."""
        return {"ip": self.ip, "custo": self.custo}
    
    @classmethod
    def from_dict(cls, hostname: str, dados: Dict[str, Any]) -> 'Vizinho':
        """Cria um objeto Vizinho a partir de um dicionário."""
        return cls(hostname, dados["ip"], dados["custo"])

class LSA:
    """Link State Advertisement - Anuncia o estado dos links para os vizinhos."""
    
    def __init__(self, id: str, ip: str, vizinhos: Dict[str, Vizinho], seq: int):
        self.id = id
        self.ip = ip
        self.vizinhos = vizinhos
        self.seq = seq
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o LSA para um dicionário para serialização"""
        return {
            "id": self.id,
            "ip": self.ip,
            "vizinhos": {hostname: vizinho.to_dict() for hostname, vizinho in self.vizinhos.items()},
            "seq": self.seq
        }
    
    @classmethod
    def from_dict(cls, dados: Dict[str, Any]) -> 'LSA':
        """Cria um objeto LSA a partir de um dicionário"""
        vizinhos = {
            hostname: Vizinho.from_dict(hostname, info) 
            for hostname, info in dados["vizinhos"].items()
        }
        return cls(dados["id"], dados["ip"], vizinhos, dados["seq"])
    
    def __str__(self) -> str:
        return f"LSA(id={self.id}, seq={self.seq}, vizinhos={len(self.vizinhos)})"

class LSDB:
    """Link State Database - Armazena todos os LSAs recebidos."""
    
    def __init__(self):
        self.lsas: Dict[str, LSA] = {}
    
    def adicionar_lsa(self, lsa: LSA) -> bool:
        """Adiciona ou atualiza um LSA na base de dados. Retorna True se houve atualização."""
        if lsa.id not in self.lsas or lsa.seq > self.lsas[lsa.id].seq:
            self.lsas[lsa.id] = lsa
            return True
        return False
    
    def obter_lsa(self, id_router: str) -> Optional[LSA]:
        """Obtém um LSA pelo ID do roteador"""
        return self.lsas.get(id_router)
    
    def obter_todos_roteadores(self) -> Set[str]:
        """Retorna o conjunto de todos os roteadores conhecidos na rede"""
        todos_roteadores = set(self.lsas.keys())
        for lsa in self.lsas.values():
            todos_roteadores.update(lsa.vizinhos.keys())
        return todos_roteadores
    
    def construir_grafo(self) -> Dict[str, Dict[str, int]]:
        """Constrói um grafo a partir dos LSAs para o algoritmo de Dijkstra"""
        grafo = {}
        todos_roteadores = self.obter_todos_roteadores()
        
        # Inicializa o grafo com todos os roteadores conhecidos
        for router in todos_roteadores:
            grafo[router] = {}
        
        # Preenche as conexões do grafo
        for lsa in self.lsas.values():
            for hostname, vizinho in lsa.vizinhos.items():
                grafo[lsa.id][hostname] = vizinho.custo
        
        return grafo
    
    def __len__(self) -> int:
        return len(self.lsas)
    
    def __bool__(self) -> bool:
        return len(self.lsas) > 0

class TabelaRotas:
    """Armazena as rotas calculadas pelo algoritmo de roteamento."""
    
    def __init__(self):
        self.rotas: Dict[str, str] = {}
    
    def adicionar_rota(self, destino: str, proximo_salto: str) -> None:
        """Adiciona uma rota na tabela"""
        self.rotas[destino] = proximo_salto
    
    def obter_proximo_salto(self, destino: str) -> Optional[str]:
        """Obtém o próximo salto para um destino"""
        return self.rotas.get(destino)
    
    def limpar(self) -> None:
        """Limpa todas as rotas"""
        self.rotas.clear()
    
    def items(self):
        """Retorna os itens da tabela de rotas"""
        return self.rotas.items()
    
    def __len__(self) -> int:
        return len(self.rotas)
    
    def __bool__(self) -> bool:
        return len(self.rotas) > 0

class Router:
    """Implementa um roteador com protocolo de estado de enlace (Link State)."""
    
    def __init__(self):
        self.hostname = os.environ.get('my_name', '')
        self.ip_address = os.environ.get('my_ip', '')
        self.vizinhos = self._get_vizinhos()
        
        self.porta_lsa = DEFAULT_LSA_PORT
        self.lsdb = LSDB()
        self.tabela_rotas = TabelaRotas()
        self.seq = 0
        
        # Cache de rotas adicionadas
        self.rotas_atuais = {}  # formato: {rede_destino: (next_hop_ip, interface)}
    
    def log(self, message: str) -> None:
        """Registra mensagens de log com identificador do roteador."""
        print(f"[{self.hostname}] {message}", flush=True)
        
    def _get_vizinhos(self) -> Dict[str, Vizinho]:
        """Obtém os vizinhos do roteador a partir das variáveis de ambiente."""
        vizinhos = {}
        router_links = os.environ.get('router_links', '').split(',')
        for hostname in router_links:
            if not hostname:  # Ignora entradas vazias
                continue
            try:
                ip = socket.gethostbyname(hostname)
                vizinhos[hostname] = Vizinho(hostname, ip, 1)
            except socket.gaierror:
                self.log(f"Não foi possível resolver o hostname: {hostname}")
        return vizinhos

    def dijkstra(self, origem: str) -> TabelaRotas:
        """Implementação do algoritmo de Dijkstra para calcular o caminho mais curto."""
        tabela = TabelaRotas()
        grafo = self.lsdb.construir_grafo()
        
        if not grafo:
            self.log("Grafo vazio, não é possível calcular rotas.")
            return tabela
        
        self.log(f"Calculando rotas para {len(grafo)} nós no grafo")
        
        distancias = {router: float('inf') for router in grafo}
        distancias[origem] = 0
        visitados = set()
        predecessor = {router: None for router in grafo}
        
        while len(visitados) < len(grafo):
            # Encontra o nó não visitado com a menor distância
            nao_visitados = [router for router in grafo if router not in visitados]
            if not nao_visitados:
                break
                
            atual = min(nao_visitados, key=lambda r: distancias[r])
            
            # Se a distância for infinita, não há mais nós alcançáveis
            if distancias[atual] == float('inf'):
                break
                
            # Atualiza as distâncias dos vizinhos
            for vizinho, custo in grafo[atual].items():
                if vizinho not in visitados:
                    nova_distancia = distancias[atual] + custo
                    if nova_distancia < distancias[vizinho]:
                        distancias[vizinho] = nova_distancia
                        predecessor[vizinho] = atual
            
            visitados.add(atual)

        # Para debugging
        self.log(f"Dijkstra completado. Distâncias calculadas para {len(visitados)} nós")
        for node, dist in distancias.items():
            if dist < float('inf'):
                self.log(f"  Distância até {node}: {dist}")

        # Construção da tabela de roteamento (próximo salto)
        for destino in grafo:
            if destino == origem:
                continue  # Não adicionamos rotas para nós mesmo
                
            # Se o destino não é alcançável, pula
            if distancias[destino] == float('inf'):
                self.log(f"Destino {destino} não é alcançável")
                continue
                
            # Encontra o primeiro salto para chegar ao destino
            caminho = self._reconstruir_caminho(predecessor, destino, origem)
            if len(caminho) < 2:
                self.log(f"Caminho para {destino} inválido: {caminho}")
                continue
                
            proximo_salto = caminho[1]  # O segundo nó no caminho
            
            # Verifica se esse próximo salto é um vizinho direto
            if proximo_salto in self.vizinhos:
                tabela.adicionar_rota(destino, proximo_salto)
                self.log(f"Rota para {destino} via {proximo_salto} (distância: {distancias[destino]})")
            else:
                self.log(f"ERRO: Próximo salto {proximo_salto} para {destino} não é vizinho direto")

        # Validação final
        self.log(f"Tabela de rotas construída com {len(tabela)} entradas de {len(grafo)-1} possíveis")
        return tabela

    def _reconstruir_caminho(self, predecessor: Dict[str, str], destino: str, origem: str) -> List[str]:
        """Reconstrói o caminho completo da origem ao destino usando a tabela de predecessores."""
        caminho = [destino]
        atual = destino
        
        # Prevenir loops infinitos
        max_iteracoes = 100
        iteracoes = 0
        
        while atual != origem and predecessor[atual] is not None and iteracoes < max_iteracoes:
            atual = predecessor[atual]
            caminho.insert(0, atual)
            iteracoes += 1
        
        # Se não conseguiu chegar à origem, algo está errado
        if atual != origem:
            self.log(f"AVISO: Não foi possível reconstruir o caminho completo para {destino}")
            return []
        
        return caminho

    def receber_lsa(self) -> None:
        """Thread para receber LSAs de outros roteadores."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", self.porta_lsa))
        
        while True:
            try:
                dados, addr = sock.recvfrom(4096)
                lsa_dict = json.loads(dados.decode())
                self.log(f"Recebendo LSA de {addr[0]}: {lsa_dict['id']} (seq={lsa_dict['seq']})")
                
                lsa = LSA.from_dict(lsa_dict)
                
                # Adiciona o LSA à base de dados e encaminha se for novo
                if self.lsdb.adicionar_lsa(lsa):
                    # Encaminha o LSA para outros vizinhos
                    for hostname, vizinho in self.vizinhos.items():
                        if vizinho.ip != addr[0]:
                            sock.sendto(dados, (vizinho.ip, self.porta_lsa))
                            self.log(f"Encaminhando LSA para {hostname} ({vizinho.ip})")
            except Exception as e:
                    self.log(f"Erro ao receber LSA: {e}")

    def enviar_lsa(self) -> None:
        """Thread para enviar LSAs periodicamente."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        while True:
            try:
                self.seq += 1
                
                # Cria um novo LSA com as informações atuais
                lsa = LSA(
                    id=self.hostname,
                    ip=self.ip_address,
                    vizinhos=self.vizinhos,
                    seq=self.seq
                )
                
                # Converte para dicionário e depois para JSON
                lsa_dict = lsa.to_dict()
                mensagem = json.dumps(lsa_dict).encode()
                
                self.log(f"Enviando LSA (seq={self.seq}) para {len(self.vizinhos)} vizinhos")
                
                # Envia para todos os vizinhos
                for _, vizinho in self.vizinhos.items():
                    sock.sendto(mensagem, (vizinho.ip, self.porta_lsa))
                
                # Adiciona o próprio LSA à base de dados
                self.lsdb.adicionar_lsa(lsa)
                
                time.sleep(TIME_SLEEP)
            except Exception as e:
                self.log(f"Erro ao enviar LSA: {e}")
                time.sleep(TIME_SLEEP)

    def atualizar_tabela(self) -> None:
        """Thread para atualizar a tabela de rotas periodicamente."""
        while True:
                try:
                    if self.lsdb:
                        # Calcula as novas rotas com o algoritmo de Dijkstra
                        self.tabela_rotas = self.dijkstra(self.hostname)
                        
                        if self.tabela_rotas:
                            self.log(f"Nova tabela de rotas ({len(self.tabela_rotas)} entradas):")
                            for destino, proximo_salto in self.tabela_rotas.items():
                                self.log(f"  {destino} via {proximo_salto}")
                            self.atualizar_tabela_rotas_sistema()
                        else:
                            self.log("Nenhuma rota calculada.")
                    else:
                        self.log("LSDB vazia, aguardando LSAs...")
                    
                    time.sleep(TIME_SLEEP)
                except Exception as e:
                    self.log(f"Erro ao atualizar tabela: {e}")
                    time.sleep(TIME_SLEEP)

    def _obter_mapeamento_interfaces(self) -> Dict[str, str]:
        """Obtém o mapeamento entre as subnets e interfaces de rede."""
        interface_map = {}
        
        try:
            # Descobrir todas as interfaces com endereços IP na rede 172.20.x.x
            result = subprocess.run(["ip", "-o", "addr", "show"], 
                                    text=True, capture_output=True)
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        interface = parts[1]
                        ip_with_mask = parts[3]
                        if ip_with_mask.startswith("172.20."):
                            ip = ip_with_mask.split('/')[0]
                            # Extrair o número da subnet do IP (terceiro octeto)
                            subnet_id = ip.split('.')[2]
                            subnet_name = f"subnet_{subnet_id}"
                            interface_map[subnet_name] = interface
                            self.log(f"Mapeada interface {interface} para {subnet_name} com IP {ip}")
        except Exception as e:
            self.log(f"Erro ao obter interfaces: {e}")
            
        return interface_map

    def _encontrar_subnet_compartilhada(self, proximo_salto: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Encontra a subnet compartilhada entre este roteador e o próximo salto.
        
        Retorna uma tupla (subnet_compartilhada, next_hop_ip, interface)
        """
        # Use dynamic discovery instead of hardcoded subnet map
        vizinho = self.vizinhos.get(proximo_salto)
        
        if not vizinho:
            self.log(f"Vizinho {proximo_salto} não encontrado")
            return None, None, None
            
        next_hop_ip = vizinho.ip
        
        try:
            result = subprocess.run(["ip", "route", "get", next_hop_ip], 
                                    text=True, capture_output=True)
            
            if result.returncode == 0:
                output = result.stdout.strip()
                parts = output.split()
                if "dev" in parts:
                    dev_index = parts.index("dev")
                    if dev_index + 1 < len(parts):
                        dev_interface = parts[dev_index + 1]
                        subnet_result = subprocess.run(["ip", "addr", "show", dev_interface], 
                                                    text=True, capture_output=True)
                        if subnet_result.returncode == 0:
                            for line in subnet_result.stdout.splitlines():
                                if "inet " in line and "172.20." in line:
                                    ip_cidr = line.split()[1]
                                    ip = ip_cidr.split('/')[0]
                                    subnet_name = f"subnet_{ip.split('.')[2]}"
                                    self.log(f"Descoberta subnet {subnet_name} via interface {dev_interface}")
                                    return subnet_name, next_hop_ip, dev_interface
        except Exception as e:
            self.log(f"Erro ao descobrir interface para {next_hop_ip}: {e}")
            
        return None, next_hop_ip, None

    def _ip_na_mesma_subnet(self, ip1: str, ip2: str) -> bool:
        """Verifica se dois IPs estão na mesma subnet /24."""
        octetos1 = ip1.split('.')
        octetos2 = ip2.split('.')
        
        # Verifica se os três primeiros octetos são iguais (subnet /24)
        return octetos1[:3] == octetos2[:3]
    
    def atualizar_tabela_rotas_sistema(self) -> None:
        """
        Atualiza a tabela de rotas do sistema operacional baseado nas LSAs recebidas.
        Mantém um cache de rotas para evitar mudanças desnecessárias.
        """
        self.log("Atualizando tabela de rotas do sistema")
        
        # Obtendo informações de interfaces locais
        interfaces = {}
        try:
            result = subprocess.run(["ip", "-o", "addr", "show"], 
                                   text=True, capture_output=True)
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        interface = parts[1]
                        ip_with_mask = parts[3]
                        if ip_with_mask.startswith("172.20."):
                            ip = ip_with_mask.split('/')[0]
                            # Extrair prefixo de rede
                            prefix = ".".join(ip.split(".")[:3])
                            interfaces[interface] = {
                                "ip": ip, 
                                "rede": f"{prefix}.0/24"
                            }
                            self.log(f"Interface {interface} tem IP {ip} na rede {prefix}.0/24")
        except Exception as e:
            self.log(f"Erro ao obter interfaces: {e}")
            return
        
        # Construir mapeamento de redes diretamente conectadas
        redes_conectadas = set()
        for info in interfaces.values():
            redes_conectadas.add(info["rede"])
        
        self.log(f"Redes diretamente conectadas: {redes_conectadas}")
        
        # Conjunto de novas rotas a serem mantidas
        novas_rotas = {}
        
        # Para cada destino na tabela de rotas
        try:
            for destino, proximo_salto in self.tabela_rotas.items():
                # Se o próximo salto é um vizinho direto
                if proximo_salto in self.vizinhos:
                    vizinho = self.vizinhos[proximo_salto]
                    ip_proximo_salto = vizinho.ip
                    
                    # Encontrar a interface que pode alcançar este IP
                    interface_saida = None
                    for interface, info in interfaces.items():
                        # Verificar se o IP do próximo salto está na mesma rede da interface
                        if self._ips_na_mesma_rede(info["ip"], ip_proximo_salto):
                            interface_saida = interface
                            break
                    
                    if not interface_saida:
                        self.log(f"Não encontrei interface para alcançar {ip_proximo_salto}")
                        continue
                    
                    # Determinar rede de destino
                    destino_lsa = self.lsdb.obter_lsa(destino)
                    if not destino_lsa:
                        self.log(f"Não encontrei LSA para {destino}")
                        continue
                    
                    # Identificar redes alcançáveis pelo destino
                    destino_ip = destino_lsa.ip
                    prefix_destino = ".".join(destino_ip.split(".")[:3])
                    rede_destino = f"{prefix_destino}.0/24"
                    
                    # Verificar se rede já não é diretamente conectada
                    if rede_destino not in redes_conectadas:
                        # Adicionar à lista de novas rotas com prioridade 1 (rotas principais)
                        if rede_destino not in novas_rotas:
                            novas_rotas[rede_destino] = (ip_proximo_salto, interface_saida)
                            self.log(f"Identificada rede {rede_destino} alcançável por {destino} via {proximo_salto}")
                    
                    # Procurar redes adicionais alcançáveis pelo destino através de seus vizinhos
                    for vizinho_do_destino in destino_lsa.vizinhos:
                        # Ignorar este roteador como vizinho do destino
                        if vizinho_do_destino == self.hostname:
                            continue
                            
                        vizinho_lsa = self.lsdb.obter_lsa(vizinho_do_destino)
                        if vizinho_lsa:
                            vizinho_ip = vizinho_lsa.ip
                            prefix_vizinho = ".".join(vizinho_ip.split(".")[:3])
                            rede_vizinho = f"{prefix_vizinho}.0/24"
                            
                            # Só adiciona se não for diretamente conectada e se ainda não tiver sido adicionada
                            if rede_vizinho not in redes_conectadas and rede_vizinho not in novas_rotas:
                                novas_rotas[rede_vizinho] = (ip_proximo_salto, interface_saida)
                                self.log(f"Identificada rede {rede_vizinho} alcançável indiretamente via {destino}")
                else:
                    self.log(f"Próximo salto {proximo_salto} não é vizinho direto")
            
            # Garantir que temos rotas para todas as redes da topologia
            # Verificar redes disponíveis em toda a LSDB
            todas_redes = set()
            for hostname, lsa in self.lsdb.lsas.items():
                if hostname != self.hostname:  # Não adicionar nossa própria rede
                    prefix = ".".join(lsa.ip.split(".")[:3])
                    todas_redes.add(f"{prefix}.0/24")
            
            self.log(f"Total de redes conhecidas na topologia: {len(todas_redes)}")
            
            # Agora, comparando com as rotas atuais, adiciona/remove conforme necessário
            # 1. Rotas a serem adicionadas (estão em novas_rotas mas não em rotas_atuais ou mudaram)
            for rede, (next_hop, interface) in novas_rotas.items():
                if rede not in self.rotas_atuais or self.rotas_atuais[rede] != (next_hop, interface):
                    self.log(f"Adicionando rota: {rede} via {next_hop} dev {interface}")
                    self._adicionar_rota_sistema(rede, next_hop, interface)
                    self.rotas_atuais[rede] = (next_hop, interface)
            
            # 2. Rotas a serem removidas (estão em rotas_atuais mas não em novas_rotas)
            rotas_para_remover = []
            for rede, (next_hop, interface) in self.rotas_atuais.items():
                if rede not in novas_rotas:
                    self.log(f"Removendo rota: {rede} via {next_hop} dev {interface}")
                    self._remover_rota_sistema(rede)
                    rotas_para_remover.append(rede)
            
            # Remover as rotas do cache
            for rede in rotas_para_remover:
                del self.rotas_atuais[rede]
                
        except Exception as e:
            self.log(f"Erro ao atualizar rotas: {e}")
            import traceback
            self.log(traceback.format_exc())
    
    def _ips_na_mesma_rede(self, ip1: str, ip2: str) -> bool:
        """Verifica se dois IPs estão na mesma rede (subnet /24)."""
        octetos1 = ip1.split('.')[:3]  # Primeiros 3 octetos (rede /24)
        octetos2 = ip2.split('.')[:3]
        return octetos1 == octetos2

    def _adicionar_rota_sistema(self, subnet_destino: str, next_hop_ip: str, dev_interface: str) -> None:
        """Adiciona uma rota no sistema operacional."""
        try:
            # Remover rota existente para evitar erros
            cmd_remove = f"ip route del {subnet_destino} 2>/dev/null || true"
            subprocess.run(cmd_remove, shell=True)
            
            # Adicionar a nova rota COM o parâmetro dev
            cmd_add = f"ip route add {subnet_destino} via {next_hop_ip} dev {dev_interface}"
            self.log(f"Executando: {cmd_add}")
            
            result = subprocess.run(cmd_add, shell=True, 
                                  stderr=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  text=True)
            
            if "RTNETLINK answers: File exists" in result.stderr:
                self.log("Rota já existe, tentando atualizar...")
                cmd_replace = f"ip route replace {subnet_destino} via {next_hop_ip} dev {dev_interface}"
                replace_result = subprocess.run(cmd_replace, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                if replace_result.returncode == 0:
                    self.log("Rota atualizada com sucesso")
                else:
                    self.log(f"Erro ao atualizar rota: {replace_result.stderr}")
            else:
                self.log(f"Erro ao adicionar rota: {result.stderr}")
            
            # Verificar se a rota foi adicionada
            check_cmd = f"ip route | grep '{subnet_destino}'"
            check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            self.log(f"Verificação da rota: {check_result.stdout}")
            
        except Exception as e:
            self.log(f"Exceção ao executar comando: {e}")

    def _remover_rota_sistema(self, subnet_destino: str) -> None:
        """Remove uma rota do sistema operacional."""
        try:
            cmd = f"ip route del {subnet_destino}"
            self.log(f"Executando: {cmd}")
            
            result = subprocess.run(cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            
            if result.returncode != 0 and "No such process" not in result.stderr:
                self.log(f"Erro ao remover rota: {result.stderr}")
            else:
                self.log(f"Rota removida com sucesso")
        except Exception as e:
            self.log(f"Exceção ao remover rota: {e}")

    def _verificar_rotas(self) -> None:
        """Thread para verificar periodicamente se as rotas estão funcionando."""
        while True:
            try:
                time.sleep(10)  # Verifica a cada 30 segundos
                
                self.log("Verificando rotas...")
                for destino, proximo_salto in self.tabela_rotas.items():
                    # Obter IP do destino através do LSA
                    destino_lsa = self.lsdb.obter_lsa(destino)
                    if destino_lsa:
                        ip_destino = destino_lsa.ip
                        
                        # Tenta fazer ping para o destino
                        cmd = f"ping -c 1 -W 1 {ip_destino}"
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            self.log(f"Rota para {destino} ({ip_destino}) está funcionando!")
                        else:
                            self.log(f"Rota para {destino} ({ip_destino}) NÃO está funcionando")
                    else:
                        self.log(f"Não foi possível encontrar LSA para {destino}")
            except Exception as e:
                self.log(f"Erro ao verificar rotas: {e}")
                time.sleep(10)
                
    def iniciar(self) -> None:
        """Inicia o roteador e suas threads."""
        self.log("Iniciando roteador...")
        self.log(f"Hostname: {self.hostname}")
        self.log(f"IP Address: {self.ip_address}")
        self.log(f"Vizinhos: {[v.hostname for v in self.vizinhos.values()]}")
        
        # Confirmar permissões para modificar rotas (precisa ser root)
        try:
            check_perm = subprocess.run(["ip", "route", "show"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if check_perm.returncode != 0:
                self.log(f"AVISO: Possível falta de permissões para manipular rotas: {check_perm.stderr.decode()}")
        except Exception as e:
            self.log(f"ERRO ao verificar permissões: {e}")
        
        # Limpar qualquer rota antiga que possa interferir
        try:
            # Listar rotas atuais para debug
            routes_result = subprocess.run(["ip", "route", "list"], stdout=subprocess.PIPE, text=True)
            self.log(f"Rotas atuais antes de iniciar:\n{routes_result.stdout}")
            
            # Limpar tabela de rotas atual
            self.rotas_atuais = {}
        except Exception as e:
            self.log(f"ERRO ao listar rotas atuais: {e}")
        
        # Cria e inicia as threads
        threads = [
            threading.Thread(target=self.receber_lsa, name="RecvLSA"),
            threading.Thread(target=self.enviar_lsa, name="SendLSA"),
            threading.Thread(target=self.atualizar_tabela, name="UpdateTable"),
            threading.Thread(target=self._verificar_rotas, name="CheckRoutes")
        ]
        
        for thread in threads:
            thread.daemon = True
            thread.start()
            self.log(f"Thread {thread.name} iniciada")
        
        # Mantém o programa rodando
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.log("Roteador sendo encerrado")

if __name__ == "__main__":
    router = Router()
    router.iniciar()