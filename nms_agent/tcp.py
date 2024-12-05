import socket
import sys
import threading

import constants as C

from protocol.alert_flow import AlertFlow


class TCP:
    def __init__(self, agent_id, server_ip):
        self.agent_id = agent_id
        self.server_ip = server_ip
        self.server_port = C.TCP_PORT
        self.alert_flow = AlertFlow()
        self.lock = threading.Lock()

        # Check TCP connectivity with the server on initialization
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_ip, C.TCP_PORT))
            self.client_socket.close()
        except Exception:
            print(f"Error connecting to TCP server {self.server_ip}:{C.TCP_PORT}")
            print("Ensure the server is running and the IP address is correct.")
            print("Exiting...")
            sys.exit(1)

    def send_alert(self, data):
        # Build the packet
        packet = self.alert_flow.build_packet(self.alert_flow, self.agent_id, data)

        with self.lock:
            # Connect to the server
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_ip, C.TCP_PORT))

            # Send the packet
            self.client_socket.send(packet)

            # Close the connection
            self.client_socket.close()

    def shutdown(self):
        self.client_socket.close()
