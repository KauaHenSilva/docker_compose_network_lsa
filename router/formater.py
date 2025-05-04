"""
Utilitários para Formatação de Dados do Roteador
-----------------------------------------------
Este módulo fornece funções e classes para formatação de dados
utilizados pelo roteador na implementação do algoritmo de estado de enlace.
"""

class Formatter:
    """Classe para formatação de dados do roteador."""
    
    @staticmethod
    def formatar_vizinhos(vizinhos_str: str) -> dict[str, tuple[str, int]]:
        """
        Formata a string de vizinhos em um dicionário estruturado.
        
        Args:
            vizinhos_str (str): String no formato "[router1, 172.20.1.2, 1],[router3, 172.20.3.2, 1]"
            
        Returns:
            dict: Dicionário formatado com vizinhos no formato {nome: (ip, custo)}
        """
        vizinhos_dict = {}
        if not vizinhos_str:
            return vizinhos_dict
            
        vizinhos = vizinhos_str.strip("[]").split("],[")

        for vizinho in vizinhos:
            partes = vizinho.split(",")
            nome = partes[0].strip()
            ip = partes[1].strip()
            custo = int(partes[2].strip())
            vizinhos_dict[nome] = (ip, custo)

        return vizinhos_dict
