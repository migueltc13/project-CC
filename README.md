# CC

## Solution Architecture

![Solution Architecture](report/img/architecture.png)

### To Do List

#### Geral

- [x] server sends identifier of agent instead of its own
- [x] *Pool* de agentes conectados, pacotes por processar e pacotes por enviar
- [x] *Parsing* de tarefas pelos agentes
- [x] Execução e envio dos resultados (métricas e alertas) das tarefas
- [ ] Execução de métricas pelos agentes
- [ ] *Parsing* dos resultados pelo servidor
- [x] Adicionar tabelas de base de dados para armazenar métricas
- [x] Adicionar tabelas de base de dados para armazenar alertas (+/-)

#### NetTask

- [x] Estrutura do *header*
- [x] Verificar versão do NMS
- [x] Realizar e validar *checksum*
- [x] Definir número de sequência
- [x] Implementar *retransmissão* de pacotes se não houver resposta (ACK)
- [x] Fragmentação de pacotes
- [ ] Controlo de fluxo através do *window size* e *urgent flag*
- [x] Implementar *timeout* para retransmissão de pacotes
- [x] Adicionar *message id field* para desfragmentação/ordenação de pacotes
- [x] EOC (End of Connection) packet and logic
- [x] Determinar o uso do campo *packet size* (pouco, uma vez que UDP é orientado a datagramas)

## Protocolos Aplicacionais

### *NetTask* (UDP)

![NetTask Header](report/img/nettask_header.png)

### *AlertFlow* (TCP)

![AlertFlow Header](report/img/alertflow_header.png)

Types of Alerts:
- CPU Usage
- RAM Usage
- Interface Stats
- Packet Loss
- Jitter

### Libraries

- json
- iperf
- psutil
- ping3
