# CC

## Project Structure

```
.
├── config
│   └── config.json
├── nms_agent
│   ├── __init__.py
│   ├── tcp.py
│   └── udp.py
├── nms_server
│   ├── __init__.py
│   ├── config.py
│   ├── pool.py
│   ├── tcp.py
│   ├── udp.py
│   └── ui.py
├── protocol
│   ├── exceptions
│   │   ├── checksum_mismatch.py
│   │   ├── invalid_header.py
│   │   └── invalid_version.py
│   ├── alert_flow.py
│   └── net_task.py
├── sql
│   ├── create/
│   ├── populate/
│   ├── queries/
│   └── database.py
├── constants.py
├── nms_agent.py
├── nms_server.py
└── requirements.txt
```

### To Do List

#### Geral

- [x] server sends identifier of agent instead of its own
- [x] *Pool* de agentes conectados, pacotes por processar e pacotes por enviar
- [ ] *Parsing* de tarefas pelos agentes
- [ ] Execução e envio dos resultados (métricas e alertas) das tarefas
- [ ] *Parsing* dos resultados pelo servidor
- [ ] Adicionar tabelas de base de dados para armazenar métricas
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
- [ ] EOC (End of Connection) packet and logic

#### AlertFlow

- [ ] Estrutura do *header*
- [x] Verificar versão do NMS
- [x] Verificar se é preciso implementar fragmentação de pacotes. Não é necessário, pois os alertas são pequenos.
- [x] Tornar AlertFlow *connection-oriented*: uma conexão por alerta(s) de um agente

## Protocolos Aplicacionais

### *NetTask* (UDP)

![NetTask Header](report/img/nettask_header.png)

### *AlertFlow* (TCP)

**TODO add AlertFlow header image**

Types of Alerts:
- CPU Usage
- RAM Usage
- Interface Stats
- Packet Loss
- Jitter

### Q&A

***Q*: How does TCP handle flow control?**

*A*: TCP uses a sliding window mechanism to handle flow control.
The receiver advertises a window size to the sender.
The sender will only send packets up to the window size.
If the window size is 0, the sender will stop sending packets, until
the receiver advertises a window size greater than 0.

### Libraries

- json
- iperf
- ping3 (requires root privileges, maybe use another library that doesn't require root privileges)
