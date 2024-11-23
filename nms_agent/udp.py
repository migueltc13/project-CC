import socket
import threading

# TODO remove json import
import json

import constants as C

from protocol.net_task import NetTask

# NetTask exceptions
from protocol.net_task import (
    InvalidVersionException   as NTInvalidVersionException,
    InvalidHeaderException    as NTInvalidHeaderException,
    ChecksumMismatchException as NTChecksumMismatchException
)


class UDP(threading.Thread):
    def __init__(self, server_ip):
        super().__init__(daemon=True)
        self.server_ip = server_ip
        self.server_port = C.UDP_PORT
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.settimeout(1.0)
        self.shutdown_flag = threading.Event()
        self.net_task = NetTask()
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
