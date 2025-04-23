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
LSA_UPDATE_INTERVAL = 30  # segundos (periodic update interval)

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
        """
        Constrói um grafo a partir dos LSAs para o algoritmo de Dijkstra
        
        Exemplo do grafo:
        {
            "router1": {"router2": 1, "router3": 2},
            "router2": {"router1": 1, "router3": 1},
            "router3": {"router1": 2, "router2": 1}
        }
        """
        grafo = {router: {} for router in self.obter_todos_roteadores()}
        
        # Preenche as conexões do grafo
        for lsa in self.lsas.values():
            for hostname, vizinho in lsa.vizinhos.items():
                grafo[lsa.id][hostname] = vizinho.custo
        
        return grafo
    
    def __len__(self) -> int:
        return len(self.lsas)
    
    def __bool__(self) -> bool:
        return bool(self.lsas)

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
        return bool(self.rotas)

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
        """Thread otimizada para receber LSAs."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", self.porta_lsa))
        
        while True:
            try:
                dados, addr = sock.recvfrom(4096)
                dados_dict = json.loads(dados.decode())
                
                lsa = LSA.from_dict(dados_dict)
                if self.lsdb.adicionar_lsa(lsa):
                    for hostname, vizinho in self.vizinhos.items():
                        sock.sendto(dados, (vizinho.ip, self.porta_lsa))
    
            except Exception as e:
                self.log(f"Erro ao receber LSA: {e}")
    
    def testar_vizinhos(self, vizinhos: List[Vizinho]) -> Dict[str, Vizinho]:
        """Testa a conectividade com os vizinhos e atualiza a lista de vizinhos ativos."""
        vizinhos_ativos = {}
        
        for hostname, vizinho in vizinhos.items():
            try:
                cmd = f"ping -c 1 -W 1 {vizinho.ip}"
                result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode == 0:
                    self.log(f"Vizinho {hostname} ({vizinho.ip}) está acessível")
                    vizinhos_ativos[hostname] = vizinho
                else:
                    self.log(f"Vizinho {hostname} ({vizinho.ip}) não está acessível")
            except Exception as e:
                self.log(f"Erro ao testar vizinho {hostname}: {e}")
        
        return vizinhos_ativos

    def enviar_lsa(self) -> None:
        """Thread para enviar LSAs apenas quando necessário ou periodicamente."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        while True:
            try:
                self.log(f"Enviando LSA, seq={self.seq})")
                
                vizinhos_ativos = self.testar_vizinhos(self.vizinhos)
                self.seq += 1
                lsa = LSA(id=self.hostname, ip=self.ip_address, vizinhos=vizinhos_ativos, seq=self.seq)
                mensagem = json.dumps(lsa.to_dict()).encode()
                
                for _, vizinho in vizinhos_ativos.items():
                    sock.sendto(mensagem, (vizinho.ip, self.porta_lsa))
                    
            except Exception as e:
                self.log(f"Erro ao enviar LSA: {e}")
                time.sleep(TIME_SLEEP)

    def atualizar_tabela(self) -> None:
        """Thread para atualizar a tabela de rotas apenas quando necessário ou periodicamente."""
        while True:
            try:
                if not self.lsdb:
                    continue
                    
                nova_tabela = self.dijkstra(self.hostname)
                self.tabela_rotas = nova_tabela
                self.atualizar_tabela_rotas_sistema()
                self.log(f"Tabela atualizada com {len(nova_tabela)} rotas")
                self.precisa_recalcular = False
                        
            except Exception as e:
                self.log(f"Erro ao atualizar tabela: {e}")
                time.sleep(TIME_SLEEP)

    def _ips_na_mesma_rede(self, ip1: str, ip2: str) -> bool:
        """Verifica se dois IPs estão na mesma rede (subnet /24)."""
        return ip1.split('.')[:3] == ip2.split('.')[:3]
    
    def atualizar_tabela_rotas_sistema(self) -> None:
        """
        Atualiza a tabela de rotas do sistema operacional baseado nas LSAs recebidas.
        Mantém um cache de rotas para evitar mudanças desnecessárias.
        """
        self.log("Atualizando tabela de rotas do sistema")
        
        # Obtendo informações de interfaces locais
        interfaces = {}
        try:
            result = subprocess.run(["ip", "-o", "addr", "show"], text=True, capture_output=True)
            
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
        redes_conectadas = {info["rede"] for info in interfaces.values()}
        
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
                        # Adicionar à lista de novas rotas
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
            
            for rede, (next_hop, interface) in novas_rotas.items():
                if rede not in self.rotas_atuais or self.rotas_atuais[rede] != (next_hop, interface):
                    self.log(f"Adicionando rota: {rede} via {next_hop} dev {interface}")
                    self._adicionar_rota_sistema(rede, next_hop, interface)
                    self.rotas_atuais[rede] = (next_hop, interface)
            
            for rede in list(self.rotas_atuais.keys()):
                if rede not in novas_rotas:
                    next_hop, interface = self.rotas_atuais[rede]
                    self.log(f"Removendo rota: {rede} via {next_hop} dev {interface}")
                    self._remover_rota_sistema(rede)
                    del self.rotas_atuais[rede]
                
        except Exception as e:
            self.log(f"Erro ao atualizar rotas: {e}")
            import traceback
            self.log(traceback.format_exc())

    def _adicionar_rota_sistema(self, subnet_destino: str, next_hop_ip: str, dev_interface: str) -> None:
        """Adiciona uma rota no sistema operacional."""
        try:
            cmd_add = f"ip route add {subnet_destino} via {next_hop_ip} dev {dev_interface}"
            self.log(f"Executando: {cmd_add}")
            
            result = subprocess.run(cmd_add, shell=True, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0 and "RTNETLINK answers: File exists" in result.stderr:
                cmd_replace = f"ip route replace {subnet_destino} via {next_hop_ip} dev {dev_interface}"
                subprocess.run(cmd_replace, shell=True)
            
        except Exception as e:
            self.log(f"Exceção ao executar comando: {e}")

    def _remover_rota_sistema(self, subnet_destino: str) -> None:
        """Remove uma rota do sistema operacional."""
        try:
            cmd = f"ip route del {subnet_destino}"
            self.log(f"Executando: {cmd}")
            subprocess.run(cmd, shell=True)
        except Exception as e:
            self.log(f"Exceção ao remover rota: {e}")

    def iniciar(self) -> None:
        """Inicia o roteador e suas threads."""
        self.log("Iniciando roteador...")
        self.log(f"Hostname: {self.hostname}")
        self.log(f"IP Address: {self.ip_address}")
        self.log(f"Vizinhos: {[v.hostname for v in self.vizinhos.values()]}")
        
        try:
            routes_result = subprocess.run(["ip", "route", "list"], stdout=subprocess.PIPE, text=True)
            self.log(f"Rotas atuais antes de iniciar:\n{routes_result.stdout}")
        except Exception as e:
            self.log(f"ERRO ao listar rotas atuais: {e}")
        
        threads = [
            threading.Thread(target=self.receber_lsa, name="RecvLSA"),
            threading.Thread(target=self.enviar_lsa, name="SendLSA"),
            threading.Thread(target=self.atualizar_tabela, name="UpdateTable"),
        ]
        
        for thread in threads:
            thread.daemon = True
            thread.start()
            self.log(f"Thread {thread.name} iniciada")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.log("Roteador sendo encerrado")

if __name__ == "__main__":
    router = Router()
    router.iniciar()