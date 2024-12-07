#!/usr/bin/env python3
# Defragmentation and reordering test
# This test requires the NMS server to be running in verbose mode
# The test sends a fragmented packet and then sends the fragments in reverse order
# The server should reassemble the packet in the correct order

import sys
import os
import argparse
import socket
import time
import json

# Join the parent directory to the sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol.net_task import NetTask
from protocol.net_task import HEADER_SIZE
import constants as C


def main():
    # Parse the command line arguments
    arg_parser = argparse.ArgumentParser(description="NMS Defragmentation and Reordering test")
    arg_parser.add_argument("-s", "--server",
                            help="Server IP",
                            default="0.0.0.0")
    args = arg_parser.parse_args()

    # Check if the server IP is provided
    if not args.server:
        print("Warning: the server IP was not provided. Server IP set to 0.0.0.0")

    # Build the packet to be fragmented
    data  = "A" * (C.BUFFER_SIZE - HEADER_SIZE)
    data += "B" * (C.BUFFER_SIZE - HEADER_SIZE)
    data += "C" * (C.BUFFER_SIZE - HEADER_SIZE)
    data += "D"

    agent_id = "test_agent"

    # Sequence number as 0 so the server will not discard the packet as a duplicate
    seq_nr, packets = NetTask.build_packet(NetTask, data, 10000, {},
                                           NetTask.UNDEFINED, agent_id, 32)

    # Reverse the order of the packets
    packets.reverse()

    # Check if the server is running, using the TCP socket
    try:
        tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_client_socket.connect((args.server, C.TCP_PORT))
        tcp_client_socket.close()
    except Exception:
        print(f"Error connecting to TCP server {args.server}:{C.TCP_PORT}")
        print("Ensure the server is running and the IP address is correct.")
        print("Aborting test...")
        sys.exit(1)

    # Send the first connection to the server
    _, fc_pkt = NetTask.build_packet(NetTask, "", 0, {"urgent": 1},
                                     NetTask.FIRST_CONNECTION, agent_id, 32)

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.sendto(fc_pkt[0], (args.server, C.UDP_PORT))

    # Await the server to proccess the first connection request
    time.sleep(1)

    # Print the packets as they are sent
    for i, packet in enumerate(packets):
        udp_socket.sendto(packet, (args.server, C.UDP_PORT))
        print(f"Sending packet number {seq_nr - i}")

    print("Test completed check if the packet was successfully defragmented and ordered")


if __name__ == '__main__':
    main()
