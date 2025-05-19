# Implementação do Algoritmo de Estado de Enlace com Docker e Python

## Universidade Federal do Piauí - Campus Senador Helvídio Nunes de Barros
### Curso de Bacharel em Sistemas de Informação
### Disciplina: Redes de Computadores II

## Sobre o Projeto

Este projeto implementa uma simulação de rede de computadores composta por hosts e roteadores utilizando Python e Docker. Os roteadores implementam o algoritmo de roteamento por estado de enlace (Link State Routing Algorithm), permitindo a comunicação eficiente entre hosts em diferentes subredes.

### Objetivos

- [x] Simular uma rede com múltiplas subredes, cada uma contendo 2 hosts e 1 roteador
- [x] Implementar topologias entre os roteadores, pelo menos parcialmente conectada. (fila, anel)
- [x] Implementar o algoritmo de estado de enlace em cada roteador
- [x] Manter uma base de dados de enlaces (LSDB) e tabela de roteamento atualizada
- [x] Utilizar threads para receber e transmitir pacotes de estado de enlace
- [x] Implementar comunicação entre roteadores usando UDP Ou TCP

## Tecnologias Utilizadas

- **Python 3**: Desenvolvimento da lógica dos roteadores e hosts
- **Docker e Docker Compose**: Criação e simulação dos elementos da rede
- **Biblioteca Threading**: Implementação de concorrência para operações paralelas
- **Socket UDP**: Comunicação entre roteadores para troca de LSAs
- **Comando `ip route`**: Manutenção da tabela de roteamento nos roteadores

## Estrutura do Projeto

```
prova_1_rayner/
├── router/                    # Implementação dos roteadores
│   ├── router.py              # Código principal do roteador
│   ├── dycastra.py            # Implementação do algoritmo de Dijkstra
│   ├── formater.py            # Utilitário para formatação de dados
│   └── Dockerfile             # Configuração para build do container
├── host/                      # Implementação dos hosts
│   ├── host.py                # Código do host cliente
│   └── Dockerfile             # Configuração para build do container
├── scripts_test/              # Scripts de teste e verificação
│   ├── router_show_tables.py  # Exibe tabelas de roteamento
│   ├── router_connect_router.py # Testa conectividade entre roteadores
│   ├── user_connect_router.py # Testa conectividade de hosts para roteadores
│   └── user_connect_user.py   # Testa conectividade entre hosts
├── docker_compose_ger_fila.py # Gerador de topologia em fila
├── docker_compose_ger_cir.py  # Gerador de topologia em anel
├── docker_compose_ger_enu.py  # Gerador de topologia em malha
└── makefile                   # Comandos para facilitar a execução
```

## Checklist de Funcionalidades

- [x] **Roteamento dinâmico**
  - [x] Implementação do algoritmo de Dijkstra
  - [x] Cálculo de menor caminho entre roteadores
  - [x] Atualização automática de rotas

- [x] **Comunicação entre roteadores**
  - [x] Envio periódico de Link State Advertisements (LSA)
  - [x] Inundação controlada de LSAs na rede
  - [x] Atualização da base de dados LSDB

- [x] **Gerenciamento de tabelas de roteamento**
  - [x] Adição de novas rotas via `ip route add`
  - [x] Remoção de rotas obsoletas via `ip route del`
  - [x] Substituição de rotas modificadas via `ip route replace`

- [x] **Tolerância a falhas**
  - [x] Detecção de vizinhos inativos via ping
  - [x] Recálculo de rotas quando a topologia muda
  - [x] Sequenciamento de LSAs para evitar loops

- [x] **Topologias suportadas**
  - [x] Topologia em fila (linear)
  - [x] Topologia em anel (circular)

## Como Executar o Projeto

### Pré-requisitos

- Docker (versão 20.10 ou superior)
- Docker Compose (versão 2.0 ou superior)
- Python 3.8 ou superior
- Make (opcional, para usar os comandos do Makefile)

### Passos Detalhados para Execução

1. **Clone o repositório**:
   ```bash
   git clone https://github.com/KauaHenSilva/{Nome_Repositorio}.git
   cd {Nome_Repositorio}
   ```

2. **Escolha e gere a topologia desejada**:
   
   Para topologia em fila:
   ```bash
   make ger_fila
   ```
   ou
   ```bash
   python3 docker_compose_ger_fila.py
   ```
   
   Para topologia em anel:
   ```bash
   make ger_cir
   ```
   ou
   ```bash
   python3 docker_compose_ger_cir.py
   ```
   
   Quando solicitado, insira o número de subredes.

3. **Inicie os containers**:
   ```bash
   make up
   ```
   ou
   ```bash
   docker compose up --build
   ```
   
   Use a flag `-d` para executar em segundo plano:
   ```bash
   docker compose up --build -d
   ```

4. **Aguarde a convergência da rede**:
   Após iniciar os containers, aguarde aproximadamente 30 segundos para que os roteadores estabeleçam suas tabelas de roteamento.

5. **Verifique as tabelas de roteamento**:
   ```bash
   make router-show-tables
   ```
   ou
   ```bash
   python3 scripts_test/router_show_tables.py
   ```

6. **Teste a conectividade entre roteadores**:
   ```bash
   make router-connect-router
   ```
   ou
   ```bash
   python3 scripts_test/router_connect_router.py
   ```

7. **Teste a conectividade entre hosts e roteadores**:
   ```bash
   make user-connect-router
   ```
   ou
   ```bash
   python3 scripts_test/user_connect_router.py
   ```

8. **Teste a conectividade entre hosts**:
   ```bash
   make user-connect-user
   ```
   ou
   ```bash
   python3 scripts_test/user_connect_user.py
   ```

9. **Para encerrar os containers**:
   ```bash
   make down
   ```
   ou
   ```bash
   docker compose down
   ```

10. **Para limpar completamente (remover imagens e volumes)**:
    ```bash
    make clear
    ```
    ou
    ```bash
    docker compose down --rmi all --volumes --remove-orphans
    docker network prune -f
    ```

### Verificação de Sucesso

A implementação foi bem-sucedida quando:

- [x] Todos os roteadores possuem rotas para todas as subredes
- [x] O teste de conectividade entre roteadores mostra 100% de sucesso
- [x] O teste de conectividade entre hosts mostra 100% de sucesso
- [x] As tabelas de roteamento são atualizadas automaticamente quando há mudanças na topologia

### Solução de Problemas

- **Problema**: Alguns pings estão falhando:
  - Solução: Aguarde mais tempo para a convergência da rede ou reinicie os containers.

- **Problema**: Containers não iniciam:
  - Solução: Verifique se o arquivo docker-compose.yml foi gerado corretamente.

- **Problema**: Erro nas configurações de IP:
  - Solução: Verifique se não há conflito de IP em sua máquina host.

## Justificativa do Protocolo Escolhido

Para a comunicação entre roteadores, foi escolhido o protocolo **UDP** pelos seguintes motivos:

1. **Baixa sobrecarga**: O UDP não estabelece conexão, reduzindo a latência e o overhead de comunicação.
2. **Simplicidade**: Ideal para comunicação em tempo real entre roteadores, onde a perda ocasional de pacotes é aceitável.
3. **Eficiência para dados pequenos**: Pacotes de estado de enlace são geralmente pequenos e frequentes, características que se adequam ao UDP.
4. **Multicast**: Suporte nativo para envio de mensagens para múltiplos destinatários, útil para disseminação de informações de estado de enlace.
5. **Sem congestionamento**: Não implementa controle de congestionamento, permitindo que os roteadores enviem atualizações mesmo em situações de rede congestionada.

Embora o TCP ofereça garantia de entrega, sua sobrecarga de estabelecimento de conexão e reconhecimentos pode atrasar a disseminação de informações críticas de roteamento. No contexto de roteamento por estado de enlace, a rapidez na disseminação de informações é mais importante que a garantia de entrega de cada pacote individual.

## Construção da Topologia

A topologia da rede é gerada pelos scripts `docker_compose_ger_*.py`, que:

1. Criam múltiplas subredes, cada uma com 2 hosts e 1 roteador
2. Estabelecem conexões entre os roteadores de acordo com a topologia escolhida
3. Configuram os endereços IP e rotas estáticas iniciais
4. Geram o arquivo `docker-compose.yml` com toda a configuração necessária

Cada topologia tem características específicas:
- **Fila**: Cada roteador se conecta apenas aos adjacentes, formando uma linha
- **Anel**: Similar à fila, mas o último roteador conecta-se ao primeiro, fechando um círculo

## Implementação do Algoritmo de Estado de Enlace

Cada roteador implementa o algoritmo de estado de enlace com as seguintes características:

1. **Base de Dados de Enlaces (LSDB)**:
   - Armazena informações sobre todos os enlaces na rede
   - Atualizada quando novos pacotes de estado de enlace são recebidos
   - Mantém um identificador único para cada pacote para evitar loops

2. **Threads de Comunicação**:
   - Thread de recebimento: Escuta continuamente por pacotes de estado de enlace
   - Thread de transmissão: Envia periodicamente o estado atual do roteador

3. **Algoritmo de Dijkstra**:
   - Calcula o caminho mais curto para todos os destinos
   - Atualiza a tabela de roteamento com base nos resultados
   - Executado quando a LSDB é modificada

4. **Atualização da Tabela de Roteamento**:
   - Modifica as rotas usando o comando `ip route`
   - Adiciona ou atualiza rotas conforme necessário
   - Remove rotas obsoletas


