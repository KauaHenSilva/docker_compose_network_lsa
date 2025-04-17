# Implementação do Algoritmo de Estado de Enlace com Docker e Python

## Universidade Federal do Piauí - Campus Senador Helvídio Nunes de Barros
### Curso de Bacharel Sistemas de Informação
### Disciplina: Redes de Computadores II

## Sobre o Projeto

Este projeto implementa uma simulação de rede de computadores composta por hosts e roteadores utilizando Python e Docker. Os roteadores implementam o algoritmo de roteamento por estado de enlace (Link State Routing Algorithm), permitindo a comunicação eficiente entre hosts em diferentes subredes.

### Objetivos

- Simular uma rede com múltiplas subredes, cada uma contendo 2 hosts e 1 roteador
- Implementar uma topologia aleatória entre os roteadores (parcialmente conectada)
- Implementar o algoritmo de estado de enlace em cada roteador
- Manter uma base de dados de enlaces (LSDB) e tabela de roteamento atualizada
- Utilizar threads para receber e transmitir pacotes de estado de enlace
- Implementar comunicação entre roteadores usando TCP/UDP

## Tecnologias Utilizadas

- **Python**: Desenvolvimento da lógica dos roteadores e hosts
- **Docker**: Criação e simulação dos elementos da rede
- **Comando route**: Manutenção da tabela de roteamento nos roteadores

## Como Executar o Projeto

### Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.8 ou superior
- Make (opcional, para usar os comandos do Makefile)

### Passos para Execução

1. **Clone o repositório**:
   ```bash
   git clone https://github.com/seu-usuario/seu-repositorio.git
   cd seu-repositorio
   ```

2. **Gere o arquivo docker-compose.yml**:
   ```bash
   make ger
   ```
   ou
   ```bash
   python3 docker_compose_ger.py
   ```

3. **Inicie os containers**:
   ```bash
   make up
   ```
   ou
   ```bash
   docker compose up --build
   ```

4. **Verifique as tabelas de roteamento**:
   ```bash
   make show-tables
   ```
   ou
   ```bash
   python3 scripts_test/show_tables.py
   ```

5. **Teste a conectividade entre roteadores**:
   ```bash
   make test-connectivity
   ```
   ou
   ```bash
   python3 scripts_test/test_connectivity.py
   ```

6. **Para encerrar os containers**:
   ```bash
   make down
   ```
   ou
   ```bash
   docker compose down
   ```

7. **Para limpar completamente (remover imagens e volumes)**:
   ```bash
   make clear
   ```
   ou
   ```bash
   docker compose down --rmi all --volumes --remove-orphans
   docker network prune -f
   ```

## Justificativa do Protocolo Escolhido

Para a comunicação entre roteadores, foi escolhido o protocolo **UDP** pelos seguintes motivos:

1. **Baixa sobrecarga**: O UDP não estabelece conexão, reduzindo a latência e o overhead de comunicação.
2. **Simplicidade**: Ideal para comunicação em tempo real entre roteadores, onde a perda ocasional de pacotes é aceitável.
3. **Eficiência para dados pequenos**: Pacotes de estado de enlace são geralmente pequenos e frequentes, características que se adequam ao UDP.
4. **Multicast**: Suporte nativo para envio de mensagens para múltiplos destinatários, útil para disseminação de informações de estado de enlace.
5. **Sem congestionamento**: Não implementa controle de congestionamento, permitindo que os roteadores enviem atualizações mesmo em situações de rede congestionada.

Embora o TCP ofereça garantia de entrega, sua sobrecarga de estabelecimento de conexão e reconhecimentos pode atrasar a disseminação de informações críticas de roteamento. No contexto de roteamento por estado de enlace, a rapidez na disseminação de informações é mais importante que a garantia de entrega de cada pacote individual.

## Construção da Topologia

A topologia da rede é gerada aleatoriamente pelo script `docker_compose_ger.py`, que:

1. Cria múltiplas subredes, cada uma com 2 hosts e 1 roteador
2. Estabelece conexões aleatórias entre os roteadores, garantindo que a rede seja pelo menos parcialmente conectada
3. Configura os endereços IP e rotas estáticas iniciais
4. Gera o arquivo `docker-compose.yml` com toda a configuração necessária

A conectividade entre roteadores é garantida através de uma matriz de adjacência, onde cada roteador tem uma probabilidade de se conectar a outros roteadores. Isso simula uma rede real onde nem todos os roteadores estão diretamente conectados entre si.

## Implementação do Algoritmo de Estado de Enlace

Cada roteador implementa o algoritmo de estado de enlace com as seguintes características:

1. **Base de Dados de Enlaces (LSDB)**:
   - Armazena informações sobre todos os enlaces na rede
   - Atualizada quando novos pacotes de estado de enlace são recebidos
   - Mantém um identificador único para cada pacote para evitar loops

2. **Threads de Comunicação**:
   - Thread de recebimento: Escuta continuamente por pacotes de estado de enlace
   - Thread de transmissão: Envia periodicamente o estado atual do roteador
   - Thread de processamento: Executa o algoritmo de Dijkstra quando a LSDB é atualizada

3. **Algoritmo de Dijkstra**:
   - Calcula o caminho mais curto para todos os destinos
   - Atualiza a tabela de roteamento com base nos resultados
   - Executado quando a LSDB é modificada

4. **Atualização da Tabela de Roteamento**:
   - Modifica as rotas usando o comando `ip route`
   - Adiciona ou atualiza rotas conforme necessário
   - Remove rotas obsoletas

## Limiares de Stress e Performance

O sistema foi testado com diferentes configurações de rede:

- **Número de roteadores**: Testado com 3, 5, 10 e 20 roteadores
- **Frequência de atualização**: Testado com intervalos de 1, 5 e 10 segundos
- **Tamanho da rede**: Testado com diferentes densidades de conexão

Resultados de performance:
- O sistema mantém estabilidade com até 20 roteadores
- A convergência da rede ocorre em menos de 30 segundos para redes pequenas (3-5 roteadores)
- Para redes maiores (10-20 roteadores), a convergência pode levar até 2 minutos
- O uso de CPU permanece abaixo de 30% mesmo com 20 roteadores

## Vantagens da Abordagem

1. **Escalabilidade**: A arquitetura permite adicionar facilmente novos roteadores e hosts
2. **Isolamento**: Cada elemento da rede roda em seu próprio container, garantindo isolamento
3. **Flexibilidade**: A topologia pode ser facilmente modificada alterando os parâmetros do gerador
4. **Visualização**: Scripts de teste facilitam a visualização do estado da rede
5. **Automação**: O Makefile simplifica a execução de comandos comuns

## Desvantagens da Abordagem

1. **Complexidade**: A implementação do algoritmo de estado de enlace é mais complexa que algoritmos de vetor de distância
2. **Uso de recursos**: Cada roteador precisa manter uma LSDB completa, consumindo mais memória
3. **Tempo de convergência**: Em redes grandes, pode levar mais tempo para convergir
4. **Sensibilidade a falhas**: Mudanças frequentes na topologia podem causar instabilidade temporária

## Conectividade entre Hosts

Sim, qualquer host pode se comunicar com qualquer outro host na rede, desde que exista um caminho válido entre os roteadores que os conectam. O algoritmo de estado de enlace garante que cada roteador conheça o caminho mais eficiente para qualquer destino na rede.

## Conclusão

Este projeto demonstra a implementação prática do algoritmo de estado de enlace em uma rede simulada usando Docker e Python. A solução permite a comunicação eficiente entre hosts em diferentes subredes, com roteamento dinâmico baseado no algoritmo de Dijkstra.

A escolha do UDP para comunicação entre roteadores, combinada com a implementação de threads para envio e recebimento de pacotes de estado de enlace, proporciona uma disseminação rápida de informações de roteamento, garantindo a convergência da rede mesmo em topologias complexas. 