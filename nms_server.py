#!/usr/bin/env python3

'''
NMS Server é responsável por:
- Interpretação de Tarefas
- Apresentação de Métricas
- Comunicação UDP (NetTask)
- Comunicação TCP (AlertFlow)
- Armazenamento de Dados
'''

import socket
import threading


host = '127.0.0.1'
port = 55555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()

clients = []
nicknames = []
nick = 0

def broadcast(message):
    for client in clients:
        client.send(message)

def handle(client):
    while True:
        try:
            message = client.recv(1024).decode('ascii')
            print(message)
        except:
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]
            broadcast(f'{nickname} left the chat!'.encode('ascii'))
            nicknames.remove(nickname)
            break

def recieve():
    while True:
        client, address = server.accept()
        print(f"Connected with {str(address)}")

        nick =+ 1
        nicknames.append(nick)
        clients.append(client)

        print(f'Client Nickname is {nick}')
        client.send('Connected to the server'.encode('ascii'))

        thread = threading.Thread(target=handle, args=(client,))
        thread.start()


def write():
    while True:
        message = f'{input("")}'
        broadcast(message.encode('ascii'))

print("Server started...")

recieve_thread = threading.Thread(target=recieve)
write_thread = threading.Thread(target=write)

recieve_thread.start()
write_thread.start()