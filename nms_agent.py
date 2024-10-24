#!/usr/bin/env python3

'''
NMS Agent é responsável por:
- Comunicação UDP (NetTask)
- Comunicação TCP (AlertFlow)
- Execução de Primitivas de Sistema
    - ping para testar latência
    - iperf para testes de largura de banda (cliente ou servidor)
    - Comandos de monitorização de interfaces de rede (ip)
'''

import socket
import sys
import threading

if (sys.argv[1] is None):
    ip = '127.0.0.1'

ip = sys.argv[1]

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((ip, 55550))

def recieve():
    while True:
        try:
            message = client.recv(1024).decode('ascii')
            print(message)
        except:
            print("An error occurred!")
            client.close()
            break

def write():
    while True:
        message = f'{input("")}'
        client.send(message.encode('ascii'))

recieve_thread = threading.Thread(target=recieve)
write_thread = threading.Thread(target=write)

recieve_thread.start()
write_thread.start()