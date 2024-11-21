#!/usr/bin/env python3

import socket
import threading
import json
import os
import sys
import argparse
import sql.database as db
import constants as C
from protocol.net_task import NetTask
from protocol.alert_flow import AlertFlow

# NetTask exceptions
from protocol.net_task import (
    InvalidVersionException   as NTInvalidVersionException,
    InvalidHeaderException    as NTInvalidHeaderException,
    ChecksumMismatchException as NTChecksumMismatchException
)

# AlertFlow exceptions
from protocol.alert_flow import (
    InvalidHeaderException     as AFInvalidHeaderException,
    InvalidVersionException    as AFInvalidVersionException
)

###
# Local Constants
###

# Maximum number of clients in the TCP server queue
TCP_CLIENTS_QUEUE_SIZE = 8

# Default configuration file path
CONFIG_PATH = "config/config.json"

# SO_NO_CHECK for disabling UDP checksum
SO_NO_CHECK = 11


###
# Configuration
###

def load_config(config_path):
    if not os.path.exists(config_path):
        return None
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    return config


###
# Server Classes
###

class ServerUI:
    def __init__(self, server_hostname):
        self.running = True
        self.view_mode = False  # Real-time view mode
        self.server_hostname = server_hostname

    def display_title(self):
        print("========================================")
        print("    Network Management System Server    ")
        print("========================================")

    def save_status(self, hostname, message):
        db.operation.insert(db.values.log_type.STATUS, hostname, message)
        if self.view_mode:
            print(f"[STATUS] ({hostname}) {message}")

    def save_alert(self, hostname, alert_type, message):
        db.operation.insert(db.values.log_type.ALERT,  hostname, message)
        if self.view_mode:
            print(f"[ALERT]  ({hostname}) {{{alert_type}}} {message}")

    def save_metric(self, hostname, message):
        db.operation.insert(db.values.log_type.METRIC, hostname, message)
        if self.view_mode:
            print(f"[METRIC] ({hostname}) {message}")

    def display_info(self, message):
        print(f"[INFO] {message}")

    def display_error(self, message):
        print(f"[ERROR] {message}")

    def display_warning(self, message):
        print(f"[WARNING] {message}")

    def display_tasks(self, tasks):
        print("[CONFIGURATION] Loaded Tasks:")
        print(json.dumps(tasks, indent=2))

    def display_menu(self):
        print()
        print("Menu")
        print("1. Display Loaded Tasks")
        print("2. View Real-Time Events")
        print("3. View Connection Status")
        print("4. Shutdown Server")

    def handle_menu_choice(self, choice, tcp_server, udp_server, config):
        match choice:
            case 1:
                self.display_tasks(config["tasks"])
            case 2:
                self.display_info("Listening for real-time connections, alerts and metrics...\n"
                                  "Press Enter to return to the main menu.")
                self.view_mode = True
                input()
                self.view_mode = False
            case 3:
                self.display_info("Displaying connection status...")
                # TODO connection status display using the Pool class
            case 4:
                self.display_info("Shutting down server...")
                tcp_server.shutdown()
                udp_server.shutdown()
                self.running = False
            case _:
                self.display_error("Invalid choice. Please try again.")

    def main_menu(self, tcp_server, udp_server, config):
        while self.running:
            self.display_menu()
            try:
                choice = int(input("Enter your choice: "))
                self.handle_menu_choice(choice, tcp_server, udp_server, config)
            except ValueError:
                self.display_error("Invalid input. Please enter a number.")


# TCP Server for AlertFlow
class TCPServer(threading.Thread):
    def __init__(self, ui, host='0.0.0.0', port=C.TCP_PORT):
        super().__init__(daemon=True)
        self.ui = ui
        self.host = host
        self.port = port
        self.server_hostname = ui.server_hostname
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.settimeout(1.0)
        self.shutdown_flag = threading.Event()
        self.alert_flow = AlertFlow(C)

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

                self.ui.save_status(self.server_hostname, f"TCP connection received from {addr}")

                # Create a thread to handle the client socket
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
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
                    except AFInvalidVersionException as e:
                        self.ui.display_error(e)
                        break
                    except AFInvalidHeaderException as e:
                        self.ui.display_error(e)
                        break

                    alert_type = self.alert_flow.parse_alert_type(self.alert_flow,
                                                                  packet['alert_type'])
                    self.ui.save_alert(str(packet['identifier']), alert_type, str(packet['data']))
                except socket.timeout:
                    pass

    def shutdown(self):
        self.shutdown_flag.set()
        self.server_socket.close()


# UDP Server for NetTask
class UDPServer(threading.Thread):
    def __init__(self, ui, host='0.0.0.0', port=C.UDP_PORT):
        super().__init__(daemon=True)
        self.ui = ui
        self.host = host
        self.port = port
        self.server_hostname = ui.server_hostname
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.settimeout(1.0)
        self.shutdown_flag = threading.Event()
        self.net_task = NetTask(C)

        # Start the UDP server
        try:
            # Disable checksum check for UDP (Linux only)
            self.server_socket.setsockopt(socket.SOL_SOCKET, SO_NO_CHECK, 1)
            self.server_socket.bind((self.host, self.port))
        except OSError:
            self.ui.display_error(f"UDP port {self.port} is already in use. Exiting.")
            sys.exit(1)
        self.ui.save_status(self.server_hostname, f"UDP Server started on port {self.port}")

    def run(self):
        while not self.shutdown_flag.is_set():
            try:
                raw_data, addr = self.server_socket.recvfrom(C.BUFFER_SIZE)
                if not raw_data:
                    break

                # Create a thread to handle the packet
                threading.Thread(target=self.handle_packet, args=(raw_data, addr,)).start()
            except socket.timeout:
                continue
            except OSError:  # TODO check this exception
                break

    def handle_packet(self, raw_data, addr):
        try:
            packet = self.net_task.parse_packet(self.net_task, raw_data)
        # If any of the exceptions Invalid Header or Checksum Mismatch are raised, the
        # packet is discarded. By not sending an ACK, the agent will resend the packet.
        except NTInvalidVersionException as e:
            # This exception doesn't need to interrupt the server. We can just
            # send a message in the UI and try to process the packet anyway.
            self.ui.display_warning(e)
        except NTInvalidHeaderException as e:
            self.ui.display_error(e)
            return
        except NTChecksumMismatchException as e:
            self.ui.display_error(e)
            return

        # TODO If the packet received is a ACK, process the previous packet sent
        # as acknowledged and remove it from the list of packets to be "acked",
        # for that specific agent. After that we interrupt this function.

        # TODO packet reordering and defragmentation
        # TODO flux control by checking the window size
        # if the URG flag is set, send the packet immediately, regardless of the window size
        # if the window size received is 0, send WINDOW_PROBE until the window size updates

        # TODO check for packet type
        # - First connection: add the client to the clients pool
        # - Task Metric: save the metric, after parsing data (also save the agent hostname)
        # - End of connection: remove the client from the clients pool

        # TODO remove this (debug only)
        print(f"Received packet: {json.dumps(packet, indent=2)}")
        # self.ui.save_metric(packet["identifier"], f"Metric data: {packet['data']}")

        # Send ACK
        seq_number = 0  # TODO
        identifier = self.server_hostname
        window_size = 128  # TODO
        ack_packet = self.net_task.build_ack_packet(packet, seq_number,
                                                    identifier, window_size)
        self.server_socket.sendto(ack_packet, addr)

    def shutdown(self):
        self.shutdown_flag.set()
        self.server_socket.close()


###
# Main
###

def main():
    arg_parser = argparse.ArgumentParser(description="Network Management System Server")
    arg_parser.add_argument("--config", "-c", help="Configuration file path", default=CONFIG_PATH)
    args = arg_parser.parse_args()

    config = load_config(args.config)
    if config is None:
        print("Failed to load configuration. Exiting.")
        sys.exit(1)

    server_hostname = socket.gethostname()

    ui = ServerUI(server_hostname)
    ui.display_title()

    tcp_server = TCPServer(ui)
    udp_server = UDPServer(ui)

    tcp_server.start()
    udp_server.start()

    try:
        ui.main_menu(tcp_server, udp_server, config)
    except (KeyboardInterrupt, EOFError):
        ui.display_info("Server interrupted. Shutting down...")
    finally:
        tcp_server.shutdown()
        udp_server.shutdown()
        ui.save_status(server_hostname, "Server shutdown complete.")
        print("TODO send EOC to connected agents")


if __name__ == "__main__":
    main()
