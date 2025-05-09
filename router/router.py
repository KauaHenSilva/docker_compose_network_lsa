"""
Implementação de Roteador com Algoritmo de Estado de Enlace
----------------------------------------------------------
Este módulo contém toda a lógica necessária para implementar
um roteador utilizando o algoritmo de estado de enlace (Link State)
para determinar as melhores rotas em uma rede de computadores.
"""

import json
import os
import socket
import threading
import time
import subprocess
from typing import Dict, Tuple, Any
from formater import Formatter
from dycastra import dijkstra

ROTEADOR_IP = os.getenv("my_ip")
ROTEADOR_NAME = os.getenv('my_name')
VIZINHOS = Formatter.formatar_vizinhos(os.getenv("vizinhos"))

PORTA_LSA = 5000

class Logger:
    """Classe para gerenciar logs do roteador."""

    @staticmethod    
    def log(message: str) -> None:  
        """
        Registra uma mensagem de log.
        
        Args:
            message: Mensagem a ser registrada
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"[{timestamp}] [{ROTEADOR_IP}] {message}", flush=True)

class NetworkUtils:
    """Classe para utilitários de rede."""
    
    @staticmethod
    def _testar_ping(ip: str, result: Dict[str, Tuple[bool, float]], treadlock: threading.Lock) -> None:
        """
        Testa a conectividade com um IP via ping.
        
        Args:
            ip: Endereço IP a ser testado
            result: Dicionário para armazenar os resultados do ping

        Returns:
            True se ping bem sucedido, False caso contrário
        """
        is_alive = False
        init_ping = time.time()
        try:
            process = subprocess.run(
                ["ping", "-c", "5", "-W", "1", ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            end_ping = time.time()
            is_alive = process.returncode == 0
        except Exception:
            ...
            
        with treadlock:
            tempo_ping = end_ping - init_ping   
            result[ip] = (is_alive, tempo_ping)

    
    @staticmethod
    def realizar_pings(vizinhos: Dict[str, Tuple[str, int]]) -> Dict[str, Tuple[str, str]]:
        """
        Executa pings para todos os vizinhos em paralelo e retorna os ativos.
        
        Args:
            vizinhos: Dicionário de vizinhos
            
        Returns:
            Dicionário de vizinhos ativos (nome, ip)
        """
        vizinhos_ativos = {}
        threads = []
        result = {}
        treadlock = threading.Lock()
        
        for viz, (ip, ant_custo) in vizinhos.items():
            thread = threading.Thread(target=NetworkUtils._testar_ping, args=(ip, result, treadlock))
            thread.daemon = True
            thread.start()
            threads.append((viz, ip, thread))

        for viz, ip, thread in threads:
            thread.join()
            is_alive, tempo_ping = result[ip]
            if is_alive:
                vizinhos_ativos[viz] = (ip, tempo_ping)
            else:
                ...
            
        return vizinhos_ativos

class LSAHandler:
    """Classe para manipulação de LSA (Link State Advertisement)."""
    
    @staticmethod
    def criar_pacote_lsa(roteador_id: str, seq: int, vizinhos: Dict[str, Tuple[str, int]]) -> Dict[str, Any]:    
        """
        Cria um pacote LSA com informações atuais do roteador.
        
        Args:
            roteador_id: ID do roteador
            seq: Número de sequência do pacote LSA
            
        Returns:
            Dicionário contendo o pacote LSA formatado
        """
        try:
            pacote = {
                "id": roteador_id,
                "vizinhos": {viz: (ip, custo) for viz, (ip, custo) in vizinhos.items()},
                "seq": seq
            }
            return pacote
        except Exception as e:
            Logger.log(f"Erro ao criar pacote LSA: {e}")
            return {}
        
    @staticmethod
    def enviar_lsa_para_vizinho(sock: socket.socket, mensagem: bytes, vizinho: str, ip: str) -> bool:
        """
        Envia um LSA para um vizinho específico.
        
        Args:
            sock: Socket UDP para envio
            mensagem: Mensagem LSA serializada
            vizinho: Identificador do vizinho
            ip: Endereço IP do vizinho
            
        Returns:
            True se o envio foi bem sucedido, False caso contrário
        """
        try:
            sock.sendto(mensagem, (ip, PORTA_LSA))
            # Logger.log(f"LSA enviado para {vizinho} ({ip})")
            return True
        except Exception as e:
            Logger.log(f"Erro ao enviar LSA para {vizinho} ({ip}): {e}")
            return False
        
class NetworkInterface:
    
    @staticmethod
    def obter_rotas_existentes(rotas: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
        """
        Obtém todas as rotas existentes no sistema e compara com as novas rotas.
        
        Args:
            rotas (Dict[str, str]): Dicionário com as novas rotas a serem configuradas (destino -> próximo_salto)
        
        Returns:
            Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]: 
                - Dicionário com as novas rotas a serem adicionadas
                - Dicionário com as rotas a serem removidas
                - Dicionário com as rotas a serem substituídas
        """
        rotas_existentes = {}
        rotas_sistema = {}
        
        rotas_adicionar = {}
        rotas_remover = {}
        rotas_replase = {}
        
        try:
            # Padroniza formato das novas rotas
            novas_rotas = {}
            for destino, proximo_salto in rotas.items():
                parts = destino.split('.')
                network_prefix = '.'.join(parts[:3])
                network = f"{network_prefix}.0/24"
                novas_rotas[network] = proximo_salto
            
            # Obtém rotas existentes do sistema
            resultado = subprocess.run(
                ["ip", "route", "show"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Processa cada linha do resultado
            for linha in resultado.stdout.splitlines():
                partes = linha.split()
                
                if partes[0] != "default" and partes[1] == "via":
                    rede = partes[0]  # ex: 172.20.5.0/24
                    proximo_salto = partes[2]  # ex: 172.20.4.3
                    rotas_existentes[rede] = proximo_salto
                    
                elif partes[1] == 'dev':
                    rede = partes[0]
                    proximo_salto = partes[-1]
                    rotas_sistema[rede] = proximo_salto
                
            # Replase rotas que mudaram
            for rede, proximo_salto in novas_rotas.items():
                if (rede in rotas_existentes) and (rotas_existentes[rede] != proximo_salto):
                    rotas_replase[rede] = proximo_salto
                    
            # Adicionar rotas inexistentes
            for rede, proximo_salto in novas_rotas.items():
                if (rede not in rotas_existentes) and (rede not in rotas_sistema):
                    rotas_adicionar[rede] = proximo_salto
            
            # Remover rotas que não estão mais ativas
            for rede, proximo_salto in rotas_existentes.items():
                if (rede not in novas_rotas):
                    rotas_remover[rede] = proximo_salto
                    
            return rotas_adicionar, rotas_remover, rotas_replase
        
        except Exception as e:
            Logger.log(f"Erro ao obter rotas existentes: {e}")
            return {}, {}, {}
        
    @staticmethod
    def adicionar_interface(destino: str, proximo_salto: str):
        """
        Configura a interface de rede para o próximo salto.
        
        Args:
            destino (str): Endereço IP de destino (exemplo: 172.21.8.3)
            proximo_salto (str): Endereço IP do próximo salto (exemplo: 172.21.1.3)
            
        Returns:
            bool: True se a configuração foi bem sucedida, False caso contrário
        """
        try:
            parts = destino.split('.')
            network_prefix = '.'.join(parts[:3])
            destino = f"{network_prefix}.0/24"
                
            command_add = f"ip route add {destino} via {proximo_salto}"
            process = subprocess.run(
                command_add.split(),
                capture_output=True,
            )
            if process.returncode == 0:
                Logger.log(f"Rota adicionada: {destino} via {proximo_salto}")
            else:
                Logger.log(f"Erro ao adicionar rota: {process.stderr.decode()}")
        except subprocess.CalledProcessError as e:
            Logger.log(f"Erro ao adicionar rota: {e}")
        except Exception as e:
            Logger.log(f"Erro inesperado ao adicionar rota: {e}")

    @staticmethod
    def remover_interfaces(destino: str) -> None:
        """
        Remove a configuração da interface de rede.
        
        Args:
            destino (str): Endereço IP de destino a ser removido da tabela de roteamento
        """
        try:
            process = subprocess.run(["ip", "route", "del", destino], check=True)
            if process.returncode == 0:
                Logger.log(f"Rota removida: {destino}")
            else:
                Logger.log(f"Erro ao remover rota: {process.stderr.decode()}")
        except subprocess.CalledProcessError as e:
            Logger.log(f"Erro ao remover rota: {e}")
        except Exception as e:
            Logger.log(f"Erro inesperado ao remover rota: {e}")
            
    def salvar_lsdb_rotas_arquivo(lsdb: Dict[str, Any], rotas: Dict[str, str]) -> None:
        """
        Salva a LSDB e tabela de rotas em arquivos JSON.
        
        Args:
            lsdb (Dict[str, Any]): Dicionário com a base de dados de estado de enlace
            rotas (Dict[str, str]): Dicionário com a tabela de rotas
        """
        try:
            with open(f"lsdb/lsdb_{ROTEADOR_NAME}.json", "w") as file:
                json.dump(lsdb, file, indent=4)
            with open(f"rotas/rotas_{ROTEADOR_NAME}.json", "w") as file:
                json.dump(rotas, file, indent=4)
        except Exception as e:
            Logger.log(f"Erro ao salvar LSDB: {e}")
            
    def replase_interface(destino: str, proximo_salto: str) -> None:
        """
        Substitui a configuração existente de interface de rede.
        
        Args:
            destino (str): Endereço IP de destino
            proximo_salto (str): Novo endereço IP do próximo salto
        """
        try:
            parts = destino.split('.')
            network_prefix = '.'.join(parts[:3])
            destino = f"{network_prefix}.0/24"
            
            command = f"ip route replace {destino} via {proximo_salto}"
            process = subprocess.run(command.split(), check=True)
            if process.returncode == 0:
                Logger.log(f"Rota Alterada: {destino} via {proximo_salto}")
            else:
                Logger.log(f"Erro ao substituir rota: {process.stderr.decode()}")
        except subprocess.CalledProcessError as e:
            Logger.log(f"Erro ao substituir rota: {e}")
        except Exception as e:
            Logger.log(f"Erro inesperado ao substituir rota: {e}")
    
    @staticmethod
    def config_interface(lsdb: Dict[str, Any], vizinhos: Dict[str, Tuple[str, int]]) -> None:
        """
        Configura as interfaces de rede com base na LSDB e vizinhos ativos.
        
        Args:
            lsdb (Dict[str, Any]): Base de dados de estado de enlace
            vizinhos (Dict[str, Tuple[str, int]]): Dicionário de vizinhos ativos
        """
        rotas = dijkstra(ROTEADOR_IP, lsdb)
        NetworkInterface.salvar_lsdb_rotas_arquivo(lsdb, rotas)
        
        rotas_validas = {}
        for destino, proximo_salto in rotas.items():
            for viz, (ip, _) in vizinhos.items():
                if proximo_salto == ip:
                    rotas_validas[destino] = proximo_salto
                    break
        
        rotas_adicionar, rotas_remover, rotas_replase = NetworkInterface.obter_rotas_existentes(rotas_validas)
        for destino in rotas_remover.keys():
            NetworkInterface.remover_interfaces(destino)
                
        for destino, proximo_salto in rotas_adicionar.items():
            NetworkInterface.adicionar_interface(destino, proximo_salto)
                
        for destino, proximo_salto in rotas_replase.items():
            NetworkInterface.replase_interface(destino, proximo_salto)

class Router:
    """Classe principal do roteador."""
    
    def __init__(self):
        """Inicializa o roteador e suas dependências."""
        # Configurações obtidas de variáveis de ambiente
        self.lsdb = {}  # Link State Database
        self.vizinhos = {}
        self.lock = threading.Lock()
        
        Logger.log(f"Roteador inicializado com Nome: {ROTEADOR_IP}")
        Logger.log(f"Vizinhos configurados: {VIZINHOS}")
    
    def comparar_vizinhos(self, vizinhos_antigos: Dict[str, Tuple[str, int]], vizinhos_ativos: Dict[str, Tuple[str, int]]) -> True:
        """
        Compara os vizinhos ativos com os antigos e retorna True se houver diferença.
        
        Args:
            vizinhos_antigos: Dicionário de vizinhos antigos
            vizinhos_ativos: Dicionário de vizinhos ativos
            
        Returns:
            True se houver diferença, False caso contrário
        """
        if len(vizinhos_antigos) != len(vizinhos_ativos):
            return True
        
        for viz, (ip, custo) in vizinhos_ativos.items():
            if viz not in vizinhos_antigos or vizinhos_antigos[viz] != (ip, custo):
                return True
        
        return False
            
        
    def thread_enviar_lsa(self) -> None:
        """Thread para enviar LSAs periodicamente."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        seq = 0
        
        while True:
            vizinhos_ativos = NetworkUtils.realizar_pings(VIZINHOS)
            if self.comparar_vizinhos(self.vizinhos, vizinhos_ativos):
                seq += 1
                lsa = LSAHandler.criar_pacote_lsa(ROTEADOR_IP, seq, vizinhos_ativos) 
                mensagem = json.dumps(lsa).encode()
                
                for viz, (ip, custo) in vizinhos_ativos.items():
                    LSAHandler.enviar_lsa_para_vizinho(sock, mensagem, viz, ip)
  
                with self.lock:
                    self.lsdb[ROTEADOR_IP] = lsa
                    self.vizinhos = vizinhos_ativos
                    NetworkInterface.config_interface(self.lsdb, self.vizinhos)
                
    def thread_receber_lsa(self) -> None:
        """Thread para receber LSAs de outros roteadores."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Isso permite que o socket seja reutilizado
        
        try:
            sock.bind(("0.0.0.0", PORTA_LSA))
        except Exception as e:
            Logger.log(f"Erro ao vincular socket: {e}")
            return
            
        while True:
            try:
                dados, addr = sock.recvfrom(4096)
                
                lsa = json.loads(dados.decode())
                origem = lsa["id"]

                if origem not in self.lsdb or lsa["seq"] > self.lsdb[origem]["seq"]:
                    for viz, (ip, custo) in VIZINHOS.items():
                        if ip != addr[0]:
                            sock.sendto(dados, (ip, PORTA_LSA))
                    
                    with self.lock:
                        self.lsdb[origem] = lsa
                        NetworkInterface.config_interface(self.lsdb, self.vizinhos)

            except socket.error as e:
                Logger.log(f"Erro ao receber LSA: {e}")
            except json.JSONDecodeError:
                Logger.log("Erro ao decodificar LSA recebido.")
            except Exception as e:
                Logger.log(f"Erro inesperado ao receber LSA: {e}")
        
    def iniciar(self) -> None:
        """Inicia as threads do roteador."""
        
        while True:
            with open("start.txt", 'r') as file:
                if file.read().strip() == "start":
                    break
        
        threads = [
            threading.Thread(target=self.thread_enviar_lsa, daemon=True, name="enviar_lsa"),
            threading.Thread(target=self.thread_receber_lsa, daemon=True, name="receber_lsa"),
        ]
        
        for thread in threads:
            thread.start()
        threading.Event().wait()

if __name__ == "__main__":
    # Inicializa e executa o roteador
    router = Router()
    router.iniciar()
