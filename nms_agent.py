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
import threading
import json
import sys
import argparse
import constants as C
from protocol.net_task import NetTask
from protocol.alert_flow import AlertFlow


class ClientTCP:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.alert_flow = AlertFlow(C)

        # Connect to the server
        try:
            self.client_socket.connect((self.server_ip, C.TCP_PORT))
        except Exception:
            print(f"Error connecting to TCP server {self.server_ip}:{C.TCP_PORT}")
            print("Ensure the server is running and the IP address is correct.")
            print("Exiting...")
            sys.exit(1)

    def send_alert(self, alert_type, agent_id, data):
        packet = self.alert_flow.build_packet(self.alert_flow, alert_type, agent_id, data)
        self.client_socket.send(packet)

    def shutdown(self):
        self.client_socket.close()


class ClientUDP(threading.Thread):
    def __init__(self, server_ip, server_port):
        super().__init__(daemon=True)
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.settimeout(1.0)
        self.shutdown_flag = threading.Event()
        self.net_task = NetTask(C)

    def run(self):
        while not self.shutdown_flag.is_set():
            try:
                print("DEBUG: Waiting for server response...")  # TODO remove this
                raw_data, addr = self.client_socket.recvfrom(C.BUFFER_SIZE)
                if not raw_data:
                    break

                # Create a thread to handle the packet
                threading.Thread(target=self.handle_packet, args=(raw_data,)).start()
            except socket.timeout:
                continue
            except OSError:  # TODO check this exception
                break

    # TODO
    def handle_packet(self, raw_data):
        packet = self.net_task.parse_packet(self.net_task, raw_data)
        # TODO catch exceptions
        print(f"Received packet: {json.dumps(packet, indent=2)}")

    def send_first_connection(self, agent_id):
        seq_number = 0  # TODO
        flags = {"urgent": 1}
        msg_type = self.net_task.FIRST_CONNECTION
        window_size = 64  # TODO
        packet = self.net_task.build_packet(self.net_task, "", seq_number, flags,
                                            msg_type, agent_id, window_size)
        self.client_socket.sendto(packet, (self.server_ip, C.UDP_PORT))

    def shutdown(self):
        self.shutdown_flag.set()
        self.client_socket.close()


if __name__ == "__main__":
    # Parse command line arguments
    arg_parser = argparse.ArgumentParser(description="Network Management System Agent")
    arg_parser.add_argument("--server", "-s", help="Server IP", default="0.0.0.0")
    args = arg_parser.parse_args()

    server_ip = args.server
    agent_id = socket.gethostname()

    udp_client = ClientUDP(server_ip, C.UDP_PORT)
    tcp_client = ClientTCP(server_ip, C.TCP_PORT)

    # Start listening for server responses (NetTask)
    udp_client.start()

    # First connection to the server
    udp_client.send_first_connection(agent_id)

    # TODO remove this (test alert)
    # tcp_client.send_alert(AlertFlow.CPU_USAGE, agent_id, "Test CPU usage Alert")

    try:
        # Loop to keep the main thread running
        while True:
            pass
    except KeyboardInterrupt:
        print("Agent shutting down...")
        print("TODO send EOC to server")  # TODO
    finally:
        udp_client.shutdown()
        tcp_client.shutdown()

    # TCP - open a connection for sending critical alerts
    # When running into a critical alert situation, send an alert to the server

    # UDP - Send a Hello with identification (hostname)
    # Await for ACK if not received, retry
    # Await for tasks from server
    # Parse/execute tasks in a thread
