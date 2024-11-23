import socket
import threading
import sys

import constants as C

from protocol.alert_flow import AlertFlow

# AlertFlow exceptions
from protocol.exceptions.invalid_version import InvalidVersionException
from protocol.exceptions.invalid_header  import InvalidHeaderException


# Maximum number of clients in the TCP server queue
TCP_CLIENTS_QUEUE_SIZE = 8


class TCP(threading.Thread):
    def __init__(self, ui, host='0.0.0.0', port=C.TCP_PORT):
        super().__init__(daemon=True)
        self.ui = ui
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
        self.ui.save_status(self.server_hostname, f"TCP Server started on port {self.port}")

    def run(self):
        while not self.shutdown_flag.is_set():
            try:
                client_socket, addr = self.server_socket.accept()
                client_socket.settimeout(1.0)

                self.ui.save_status(self.server_hostname, f"TCP connection received from {addr}")

                # Create a thread to handle the client socket
                handle_client_thread = threading.Thread(target=self.handle_client,
                                                        args=(client_socket,))
                self.threads.append(handle_client_thread)
                handle_client_thread.start()
            except socket.timeout:
                pass
            except OSError:  # TODO check this exception
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
                    except (InvalidVersionException, InvalidHeaderException) as e:
                        self.ui.display_error(e)
                        break

                    alert_type = self.alert_flow.parse_alert_type(self.alert_flow,
                                                                  packet['alert_type'])
                    self.ui.save_alert(str(packet['identifier']), alert_type, str(packet['data']))
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
