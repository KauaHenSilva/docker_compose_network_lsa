"""
Utilitários para formatação de dados usados pelo roteador.
"""

class Formatter:
    """Classe para formatação de dados."""
    
    @staticmethod
    def formatar_vizinhos(vizinhos_str: str) -> dict[str, tuple[str, int]]:
        """
        Formata a string de vizinhos em um dicionário.
        
        Recebe: "[router1, 172.20.1.2, 1],[router3, 172.20.3.2, 1]"
        retorna: {
            "router1": ("172.20.1.2", 1),
            "router3": ("172.20.3.2", 1)
        }
        
        Args:
            vizinhos_str: String no formato "[router1, 172.20.1.2, 1],[router3, 172.20.3.2, 1]"
            
        Returns:
            Dicionário formatado com vizinhos
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
