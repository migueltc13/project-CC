#!/usr/bin/env python3

import socket
import threading
import json
import os
import sys
import argparse
import database as db
import constants as C


###
# Constants
###

# Maximum number of clients in the TCP server queue
TCP_CLIENTS_QUEUE_SIZE = 8

# Buffer size is set as the usual MTU size
BUFFER_SIZE = 1500  # bytes


###
# Configuration
###

def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        return None
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    return config


###
# Server Classes
###

class ServerUI:
    def __init__(self):
        self.running = True

    def display_title(self):
        print("========================================")
        print("    Network Management System Server    ")
        print("========================================")

    def save_status(self, message):
        db.insert(db.log_type.STATUS, message)

    def save_alert(self, message):
        db.insert(db.log_type.ALERT, message)

    def save_metric(self, data):
        db.insert(db.log_type.METRIC, data)

    def display_info(self, message):
        print(f"[INFO] {message}")

    def display_error(self, message):
        print(f"[ERROR] {message}")

    def display_tasks(self, tasks):
        print("[CONFIGURATION] Loaded Tasks:")
        print(json.dumps(tasks, indent=2))

    def display_menu(self):
        print()
        print("Menu")
        print("1. Display Loaded Tasks")
        print("2. View Real-Time Alerts and Metrics")
        print("3. View Connection Status")
        print("4. Shutdown Server")

    def handle_menu_choice(self, choice, tcp_server, udp_server, config):
        match choice:
            case 1:
                self.display_tasks(config["tasks"])
            case 2:
                self.display_info("Listening for real-time alerts and metrics...")
                # TODO real-time metrics display logic
            case 3:
                self.display_info("Displaying connection status...")
                # TODO connection status display
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
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.shutdown_flag = threading.Event()
        self.ui = ui

    def run(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(TCP_CLIENTS_QUEUE_SIZE)
        self.ui.save_status(f"TCP Server started on port {self.port}")
        while not self.shutdown_flag.is_set():
            try:
                self.server_socket.settimeout(1.0)
                client_socket, addr = self.server_socket.accept()
                self.ui.save_status(f"Connection from {addr}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            except socket.timeout:
                pass
            except OSError:
                break

    def handle_client(self, client_socket):
        with client_socket:
            while not self.shutdown_flag.is_set():
                try:
                    # TODO format alert message
                    data = client_socket.recv(BUFFER_SIZE)
                    if not data:
                        break
                    alert_message = data.decode()
                    self.ui.save_alert(alert_message)
                except socket.timeout:
                    pass

    def shutdown(self):
        self.shutdown_flag.set()
        self.server_socket.close()


# UDP Server for NetTask
class UDPServer(threading.Thread):
    def __init__(self, ui, host='0.0.0.0', port=C.UDP_PORT):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ui = ui
        self.shutdown_flag = threading.Event()

    def run(self):
        self.server_socket.bind((self.host, self.port))
        self.ui.save_status(f"UDP Server started on port {self.port}")
        while not self.shutdown_flag.is_set():
            try:
                self.server_socket.settimeout(1.0)
                data, addr = self.server_socket.recvfrom(BUFFER_SIZE)
                metric_data = data.decode()
                self.ui.save_metric(f"Metric data from {addr}: {metric_data}")
            except socket.timeout:
                continue
            except OSError:
                break

    def shutdown(self):
        self.shutdown_flag.set()
        self.server_socket.close()


###
# Main
###

def main():
    parser = argparse.ArgumentParser(description="Network Management System Server")
    parser.add_argument("--config", "-c", help="Configuration file path", default="config.json")
    args = parser.parse_args()

    config = load_config(args.config)
    if config is None:
        print("Failed to load configuration. Exiting.")
        sys.exit(1)

    ui = ServerUI()
    ui.display_title()

    tcp_server = TCPServer(ui)
    udp_server = UDPServer(ui)

    tcp_server.start()
    udp_server.start()

    try:
        ui.main_menu(tcp_server, udp_server, config)
    except KeyboardInterrupt:
        ui.display_info("Server interrupted. Shutting down...")
    finally:
        tcp_server.shutdown()
        udp_server.shutdown()
        ui.save_status("Server shutdown complete.")


if __name__ == "__main__":
    main()
