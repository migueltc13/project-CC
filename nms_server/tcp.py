import socket
import threading
import sys
import json

import constants as C

from protocol.alert_flow import AlertFlow

# AlertFlow exceptions
from protocol.exceptions.invalid_version import InvalidVersionException
from protocol.exceptions.invalid_header  import InvalidHeaderException


# Maximum number of clients in the TCP server queue
TCP_CLIENTS_QUEUE_SIZE = 8


class TCP(threading.Thread):
    def __init__(self, ui, verbose=False, host='0.0.0.0', port=C.TCP_PORT):
        super().__init__(daemon=True)
        self.ui = ui
        self.verbose = verbose
        self.host = host
        self.port = port
        self.server_hostname = ui.server_hostname
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.settimeout(1.0)
        self.shutdown_flag = threading.Event()
        self.alert_flow = AlertFlow()
        self.threads = []

        # Start the TCP server
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(TCP_CLIENTS_QUEUE_SIZE)
        except OSError:
            self.ui.display_error(f"TCP port {self.port} is already in use. Exiting.")
            sys.exit(1)
        self.ui.save_status(f"TCP Server started on port {self.port}")

    def run(self):
        while not self.shutdown_flag.is_set():
            try:
                client_socket, addr = self.server_socket.accept()
                client_socket.settimeout(1.0)

                self.ui.save_status(f"TCP connection received from {addr}")

                # Create a thread to handle the client socket
                handle_client_thread = threading.Thread(target=self.handle_client,
                                                        args=(client_socket,))
                self.threads.append(handle_client_thread)
                handle_client_thread.start()
            except socket.timeout:
                pass
            except OSError:
                break

    def handle_client(self, client_socket):
        with client_socket:
            while not self.shutdown_flag.is_set():
                try:
                    raw_data = client_socket.recv(C.BUFFER_SIZE)
                    if not raw_data:
                        break

                    try:
                        packet = self.alert_flow.parse_packet(self.alert_flow, raw_data)
                        if self.ui.view_mode and self.verbose:
                            print(f"Received alert {packet}")
                    except (InvalidVersionException, InvalidHeaderException) as e:
                        self.ui.display_error(e)
                        break

                    # Save alerts received
                    agent_id = packet['identifier']
                    alerts = json.loads(packet['data'])

                    for alert_type, alert_data in alerts.items():
                        alert_type = int(alert_type)
                        messages = []
                        match alert_type:
                            case AlertFlow.CPU_USAGE:
                                messages.append(
                                    f"CPU usage {alert_data['cpu_usage']}. " +
                                    f"Alert condition: {alert_data['alert_condition']}"
                                )
                            case AlertFlow.RAM_USAGE:
                                messages.append(
                                    f"RAM usage {alert_data['ram_usage']}. " +
                                    f"Alert condition: {alert_data['alert_condition']}"
                                )
                            case AlertFlow.INTERFACE_STATS:
                                for interface in alert_data:
                                    messages.append(
                                        f"Interface {interface['interface']} " +
                                        f"received {interface['interface_stats']} packets. " +
                                        f"Alert condition: {interface['alert_condition']}"
                                    )
                            case AlertFlow.PACKET_LOSS:
                                messages.append(
                                    f"Packet loss {alert_data['packet_loss']}. " +
                                    f"Alert condition: {alert_data['alert_condition']}"
                                )
                            case AlertFlow.JITTER:
                                messages.append(
                                    f"Jitter {alert_data['jitter']}. " +
                                    f"Alert condition: {alert_data['alert_condition']}"
                                )
                            case _:
                                if self.ui.view_mode:
                                    print("Unknown alert type received")

                        for message in messages:
                            self.ui.save_alert(agent_id, alert_type, message)

                        messages = []
                except socket.timeout:
                    pass

    def shutdown(self):
        # Signal all threads to stop
        self.shutdown_flag.set()

        # Wait for all threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join()

        # Close the socket
        try:
            self.server_socket.close()
        except OSError as e:
            self.ui.display_error(f"Error closing TCP socket: {e}")
