#!/usr/bin/env python3

import socket
import threading
import json
import os
import sys
import time
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
    InvalidHeaderException    as AFInvalidHeaderException,
    InvalidVersionException   as AFInvalidVersionException
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

# Initial window size for flow control, represents the space available in the server buffer
INITIAL_WINDOW_SIZE = 64

# Time to sleep before retransmitting packets
RETRANSMIT_SLEEP_TIME = 5  # seconds


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
    def __init__(self, server_hostname, pool):
        self.running = True
        self.view_mode = False  # Real-time view mode
        self.server_hostname = server_hostname
        self.pool = pool

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
        print("[CONFIG] Loaded Tasks:")
        print(json.dumps(tasks, indent=2))

    def display_menu(self):
        print()
        print("Menu")
        print("1. Display Loaded Tasks")
        print("2. View Real-Time Events")
        print("3. View Connected Agents")
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
                agents = self.pool.get_connected_clients()
                n = len(agents)
                if n == 0:
                    print("No agents connected.")
                else:
                    print(f"{len(agents)} Connected Agents:")
                    for agent in agents:
                        print(f"Agent: {agent}")
                        # TODO remove the following prints
                        print(f"Address: {agents[agent]}")
                        print(f"Sequence Number: {self.pool.get_seq_number(agent)}")
                        print(f"Packets to Ack: {self.pool.packets_to_ack[agent]}")
                        print(f"Packets to Reorder: {self.pool.packets_to_reorder[agent]}")
            case 4:
                self.display_info("Shutting down server...")
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


# UDP Server for NetTask
class UDPServer(threading.Thread):
    def __init__(self, ui, pool, host='0.0.0.0', port=C.UDP_PORT):
        super().__init__(daemon=True)
        self.ui = ui
        self.host = host
        self.port = port
        self.server_hostname = ui.server_hostname
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.settimeout(1.0)
        self.shutdown_flag = threading.Event()
        self.net_task = NetTask()
        self.pool = pool
        self.lock = threading.Lock()
        self.threads = []

        # Start the UDP server
        try:
            # Disable checksum check for UDP (Linux only)
            self.server_socket.setsockopt(socket.SOL_SOCKET, SO_NO_CHECK, 1)
            self.server_socket.bind((self.host, self.port))
        except OSError:
            self.ui.display_error(f"UDP port {self.port} is already in use. Exiting.")
            sys.exit(1)
        self.ui.save_status(self.server_hostname, f"UDP Server started on port {self.port}")

        # Retransmit packets to be acknowledged
        ret_thread = threading.Thread(target=self.retransmit_packets)
        self.threads.append(ret_thread)
        ret_thread.start()

    def retransmit_packets(self):
        while not self.shutdown_flag.is_set():
            # Sleep for a while before retransmitting the packets
            time.sleep(RETRANSMIT_SLEEP_TIME)
            if self.shutdown_flag.is_set():
                break

            # Get the connected agents and respective addresses
            agents = self.pool.get_connected_clients()

            # For each agent, get the packets to retransmit and retransmit them
            for agent in agents:
                addr = agents[agent]
                packets = self.pool.get_packets_to_ack(agent)
                # if len(packets) != 0:
                #     print(f"Retransmitting {len(packets)} packets to {agent}")
                with self.lock:
                    for packet in packets:
                        self.server_socket.sendto(packet, addr)

    def run(self):
        while not self.shutdown_flag.is_set():
            try:
                raw_data, addr = self.server_socket.recvfrom(C.BUFFER_SIZE)
                if not raw_data:
                    break

                # Create a thread to handle the packet
                handle_packet_thread = threading.Thread(target=self.handle_packet,
                                                        args=(raw_data, addr,))
                self.threads.append(handle_packet_thread)
                handle_packet_thread.start()
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
        except (NTInvalidHeaderException, NTChecksumMismatchException) as e:
            self.ui.display_error(e)
            return

        agent_id = packet["identifier"]

        # If the packet received is a ACK, process the previous packet sent
        # as acknowledged and remove it from the list of packets to be "acked",
        # for that specific agent. After that we interrupt this function.
        if packet["flags"]["ack"] == 1:
            self.pool.remove_packet_to_ack(agent_id, packet)
            return

        # TODO respond to window probes

        # Packet reordering and defragmentation
        # if the more_flags is set, add the packet to the list of packets to be reordered
        # else reorder the packets and defragment the data and combine the packets into one
        if packet["flags"]["more_fragments"] == 1:
            self.pool.add_packet_to_reorder(agent_id, packet)
            return
        else:
            packet = self.pool.reorder_packets(agent_id, packet)

        # TODO flux control by checking the window size
        # if the URG flag is set, send the packet immediately, regardless of the window size
        # if the window size received is 0, send WINDOW_PROBE until the window size updates
        if packet["flags"]["urgent"] == 1:
            pass
        elif self.pool.get_window_size() == 0:
            # TODO send window probes until the window size updates
            pass

        # TODO remove this (debug only)
        print(f"Received packet: {json.dumps(packet, indent=2)}")

        # Based on the packet type:
        # - First connection: add the client to the clients pool
        # - Task Metric: save the metric, after parsing data (also save the agent hostname)
        # - End of connection: remove the client from the clients pool
        match packet["msg_type"]:
            case self.net_task.FIRST_CONNECTION:
                self.pool.add_client(agent_id, addr)
            case self.net_task.SEND_METRICS:
                # self.ui.save_metric(agent_id, f"Metric data: {packet['data']}")
                print("TODO save metric")  # TODO
            case self.net_task.EOC:
                self.pool.remove_client(agent_id)

        # self.ui.save_metric(packet["identifier"], f"Metric data: {packet['data']}")

        # Send ACK
        seq_number = self.pool.increment_seq_number(agent_id)
        print(f"Sending ACK for packet {packet['seq_number']} to {agent_id}")
        identifier = self.server_hostname
        window_size = self.pool.get_window_size()
        seq_number, ack_packet = self.net_task.build_ack_packet(packet, seq_number,
                                                                identifier, window_size)

        # Increment the sequence number for the agent
        # TODO check if the sequence number is correct between agent and server
        self.pool.set_seq_number(agent_id, seq_number)

        with self.lock:
            self.server_socket.sendto(ack_packet, addr)

    def shutdown(self):
        # Signal all threads to stop
        self.shutdown_flag.set()

        # Close the socket
        try:
            self.server_socket.close()
        except OSError as e:
            self.ui.display_error(f"Error closing UDP socket: {e}")

        # Wait for all threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join()


class ServerPool:
    # List of connected agents and respective addresses
    # List of sequence number of each agent
    # List of packets sent yet to be acknowledged by each agent
    # List of packets received yet to be reordered and defragmented
    # Server buffer size (window size)
    def __init__(self):
        self.clients = dict()
        self.seq_numbers = dict()
        self.packets_to_ack = dict()
        self.packets_to_reorder = dict()
        self.window_size = INITIAL_WINDOW_SIZE
        self.lock = threading.Lock()

    def add_client(self, client, addr):
        with self.lock:
            self.clients[client] = addr
            self.seq_numbers[client] = 1
            self.packets_to_ack[client] = []
            self.packets_to_reorder[client] = []

    def remove_client(self, client):
        with self.lock:
            del self.clients[client]
            del self.seq_numbers[client]
            del self.packets_to_ack[client]
            del self.packets_to_reorder[client]

    def get_connected_clients(self):
        with self.lock:
            return self.clients

    def get_seq_number(self, client):
        with self.lock:
            return self.seq_numbers[client]

    def set_seq_number(self, client, seq_number):
        with self.lock:
            self.seq_numbers[client] = seq_number

    def increment_seq_number(self, client):
        with self.lock:
            self.seq_numbers[client] += 1
            return self.seq_numbers[client]

    def add_packet_to_ack(self, client, packet):
        with self.lock:
            self.packets_to_ack[client].append(packet)

    def remove_packet_to_ack(self, client, packet):
        with self.lock:
            self.packets_to_ack[client].remove(packet)

    def get_packets_to_ack(self, client):
        with self.lock:
            return self.packets_to_ack[client]

    def add_packet_to_reorder(self, client, packet):
        with self.lock:
            self.packets_to_reorder[client].append(packet)
            self.window_size -= 1

    def reorder_packets(self, client, packet):
        with self.lock:
            try:
                # Add the packet to the list of packets to reorder
                self.packets_to_reorder[client].append(packet)
                self.window_size -= 1
                packets = self.packets_to_reorder[client]
            except KeyError:
                # No packets to reorder to that client, return the packet as is
                return packet

            # filter only packets with the same message id
            packets = [f_packet for f_packet in packets
                       if f_packet["msg_id"] == packet["msg_id"]]

            # reorder packets
            packets.sort(key=lambda x: x["seq_number"])

            # defragment data by concatenating the data of all packets
            packet = packets[0]
            for i in range(1, len(packets)):
                packet["data"] += packets[i]["data"]

            # update the window size
            self.window_size += len(packets)

            # remove the defragmented packets from the list of packets to reorder
            self.packets_to_reorder[client] = [packet for packet in self.packets_to_reorder[client]
                                               if packet not in packets]

            return packet

    def get_window_size(self):
        with self.lock:
            return self.window_size


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

    pool = ServerPool()

    ui = ServerUI(server_hostname, pool)
    ui.display_title()

    tcp_server = TCPServer(ui)
    udp_server = UDPServer(ui, pool)

    tcp_server.start()
    udp_server.start()

    try:
        ui.main_menu(tcp_server, udp_server, config)
    except (KeyboardInterrupt, EOFError):
        ui.display_info("Server interrupted. Shutting down...")
    finally:
        print("TODO send EOC to connected agents")  # TODO
        # send EOC to all connected agents
        # while the packets to ack are not empty, keep waiting for the acks
        tcp_server.shutdown()
        udp_server.shutdown()
        tcp_server.join()
        udp_server.join()
        ui.save_status(server_hostname, "Server shutdown complete.")
        print("Active threads:", threading.enumerate())

    sys.exit(0)


if __name__ == "__main__":
    main()
