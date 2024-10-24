#!/usr/bin/env python3

'''
NMS ServerTCP é responsável por:
- Interpretação de Tarefas
- Apresentação de Métricas
- Comunicação UDP (NetTask)
- Comunicação TCP (AlertFlow)
- Armazenamento de Dados
'''

import socket
import threading


host = '0.0.0.0'
port = 55550


        ## TCP Server
serverTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverTCP.bind((host, port))
serverTCP.listen()

class ServerTCP:
    def __init__(self, clients, ids, counter):
        self.clients = clients
        self.ids = ids
        self.counter = counter
        self.lock = threading.Lock()

s = ServerTCP([],[],0)

def broadcast(message):
    for client in s.clients:
        client.send(message)

def handle(client):
    while True:
        try:
            message = client.recv(1024).decode('ascii')
            print(message)
        except:
            index = s.clients.index(client)
            s.clients.remove(client)
            client.close()
            nickname = s.ids[index]
            broadcast(f'{nickname} left the chat!'.encode('ascii'))
            s.ids.remove(nickname)
            break

def recieve():
    while True:
        client, address = serverTCP.accept()
        print(f"Connected with {str(address)}")

        s.lock.acquire()
        try:
            s.counter += 1  
        finally:
            s.lock.release()
                
        s.ids.append(s.counter)
        s.clients.append(client)

        print(f'Client Nickname is {s.counter}')
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