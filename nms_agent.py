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

# NetTask exceptions
from protocol.net_task import (
    InvalidVersionException   as NTInvalidVersionException,
    InvalidHeaderException    as NTInvalidHeaderException,
    ChecksumMismatchException as NTChecksumMismatchException
)


class ClientTCP:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.alert_flow = AlertFlow(C)

        # Check TCP connectivity with the server on initialization
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(1.0)
            self.client_socket.connect((self.server_ip, C.TCP_PORT))
            self.client_socket.close()
        except Exception:
            print(f"Error connecting to TCP server {self.server_ip}:{C.TCP_PORT}")
            print("Ensure the server is running and the IP address is correct.")
            print("Exiting...")
            sys.exit(1)

    def send_alert(self, alert_type, agent_id, data):
        # Build the packet
        packet = self.alert_flow.build_packet(self.alert_flow, alert_type, agent_id, data)

        # Connect to the server
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(1.0)
        self.client_socket.connect((self.server_ip, C.TCP_PORT))

        # Send the packet
        self.client_socket.send(packet)

        # Close the connection
        self.client_socket.close()

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
        self.threads = []

    def run(self):
        while not self.shutdown_flag.is_set():
            try:
                raw_data, addr = self.client_socket.recvfrom(C.BUFFER_SIZE)
                if not raw_data:
                    break

                # Create a thread to handle the packet
                handle_packet_thread = threading.Thread(target=self.handle_packet,
                                                        args=(raw_data,))
                self.threads.append(handle_packet_thread)
                handle_packet_thread.start()
            except socket.timeout:
                continue
            except OSError:  # TODO check this exception
                break

    # TODO
    def handle_packet(self, raw_data):
        try:
            packet = self.net_task.parse_packet(self.net_task, raw_data)
        # If any of the exceptions Invalid Header or Checksum Mismatch are raised, the
        # packet is discarded. By not sending an ACK, the server will resend the packet.
        except NTInvalidVersionException as e:
            # This exception doesn't need to interrupt the server. We can just
            # print a message and try to process the packet anyway.
            print(e)
        except (NTInvalidHeaderException, NTChecksumMismatchException) as e:
            print(e)
            return

        # TODO remove this (debug only)
        print(f"Received packet: {json.dumps(packet, indent=2)}")

    def send_first_connection(self, agent_id):
        seq_number = 1  # TODO
        flags = {"urgent": 1}
        msg_type = self.net_task.FIRST_CONNECTION
        window_size = 64  # TODO
        seq_number, packets = self.net_task.build_packet(self.net_task, "", seq_number, flags,
                                                         msg_type, agent_id, window_size)
        print(f"Sending {len(packets)} packets for first connection")
        for packet in packets:
            self.client_socket.sendto(packet, (self.server_ip, C.UDP_PORT))
            # TODO remove this
            tmp_packet = self.net_task.parse_packet(self.net_task, packet)
            print(f"Sending packet: {json.dumps(tmp_packet, indent=2)}")

    def shutdown(self):
        # Signal all threads to stop
        self.shutdown_flag.set()

        # Close the socket
        try:
            self.client_socket.close()
        except OSError as e:
            print(f"Error closing UDP socket: {e}")

        # Wait for all threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join()


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
    # time.sleep(2)
    # tcp_client.send_alert(AlertFlow.CPU_USAGE, agent_id, "Test CPU usage Alert")

    try:
        # Loop to keep the main thread running
        while True:
            pass
    except KeyboardInterrupt:
        print("Agent interrupted. Shutting down...")
    finally:
        print("TODO send EOC to server")  # TODO
        udp_client.shutdown()
        tcp_client.shutdown()
        udp_client.join()
        print("Active threads:", threading.enumerate())

    # TCP - open a connection for sending critical alerts
    # When running into a critical alert situation, send an alert to the server

    # UDP - Send a Hello with identification (hostname)
    # Await for ACK if not received, retry
    # Await for tasks from server
    # Parse/execute tasks in a thread
