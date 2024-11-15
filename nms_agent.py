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
import argparse
import constants as C
from protocol.net_task import NetTask
# from protocol.alert_flow import AlertFlow


class ClientTCP:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.server_ip, C.TCP_PORT))

    def send_alert(self, alert_message):
        # TODO format alert message
        self.client.send(alert_message.encode(C.ENCODING))

    def close(self):
        self.client.close()


class ClientUDP:
    def __init__(self, server_ip, server_port, net_task):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client.settimeout(1.0)
        self.net_task = net_task

    def send_first_connection(self, agent_id):
        seq_number = 0  # TODO
        flags = {"urgent": 1}
        msg_type = self.net_task.FIRST_CONNECTION
        packet = self.net_task.build_packet(self.net_task, "", seq_number,
                                            flags, msg_type, agent_id)
        self.client.sendto(packet, (self.server_ip, C.UDP_PORT))


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Network Management System Client")
    parser.add_argument("--server", "-s", help="Server IP", default="0.0.0.0")
    args = parser.parse_args()

    server_ip = args.server
    agent_id = socket.gethostname()

    udp_client = ClientUDP(server_ip, C.UDP_PORT, NetTask(C))
    tcp_client = ClientTCP(server_ip, C.TCP_PORT)  # AlertFlow(C))

    # First connection to the server
    udp_client.send_first_connection(agent_id)

    # TCP - open a connection for sending critical alerts
    # When running into a critical alert situation, send an alert to the server

    # UDP - Send a Hello with identification (hostname)
    # Await for ACK if not received, retry
    # Await for tasks from server
    # Parse/execute tasks in a thread

    # recieve_thread = threading.Thread(target=recieve)
    # write_thread = threading.Thread(target=write)

    # recieve_thread.start()
    # write_thread.start()
