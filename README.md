# CC TP2

### To Do List

#### Geral

- [ ] *Pool* de agentes conectados, pacotes por processar e pacotes por enviar (extra: *pool* de *threads*)
- [ ] *Parsing* de tarefas pelos agentes
- [ ] Execução e envio dos resultados (métricas e alertas) das tarefas
- [ ] *Parsing* dos resultados pelo servidor
- [ ] Adicionar tabelas de base de dados para armazenar métricas e alertas

#### NetTask

- [x] Estrutura do *header*
- [x] Verificar versão do NMS
- [x] Realizar e validar *checksum*
- [ ] Pensar sobre o número de sequência (opção: para cada agente, numerá-lo de forma sequencial, problema: identificar os ACKs?)
- [ ] Implementar *retransmissão* de pacotes se não houver resposta (ACK)
- [ ] Fragmentação de pacotes
- [ ] Controlo de fluxo através do *window size* e *urgent flag*

#### AlertFlow

- [ ] Estrutura do *header*
- [x] Verificar versão do NMS
- [ ] Fragmentação de pacotes

## Protocolos Aplicacionais

### *NetTask* (UDP)

![NetTask Header](report/img/nettask_header.png)

### *AlertFlow* (TCP)

**TODO add AlertFlow header image**

### Q&A

***Q*: How does TCP handle out of order packets?**

*A*: TCP uses sequence numbers to order packets.
If a packet arrives out of order, it is stored in a buffer until the missing packets arrive.
When the missing packets arrive, the packets are reassembled in the correct order.

***Q*: How does TCP handle lost packets?**

*A*: TCP uses a retransmission mechanism to handle lost packets.
If a packet is lost, the receiver will send a `NACK` to the sender.
The sender will then retransmit the lost packet.

***Q*: How does TCP detect errors?**

*A*: TCP uses a checksum to detect errors.
The checksum is calculated by summing the bytes in the packet.
If the checksum does not match the calculated checksum, the packet is *discarded*.

***Q*: How does TCP correct errors?**

*A*: TCP does not correct errors.

***Q*: How does TCP handle flow control?**

*A*: TCP uses a sliding window mechanism to handle flow control.
The receiver advertises a window size to the sender.
The sender will only send packets up to the window size.
If the window size is 0, the sender will stop sending packets.

### Libraries

- json
- iperf
- ping3 (requires root privileges, maybe use another library that doesn't require root privileges)
