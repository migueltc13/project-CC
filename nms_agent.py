#!/usr/bin/env python3

import socket
import threading
import sys
import argparse

from nms_agent import ClientTCP
from nms_agent import ClientUDP


def main():
    # Parse command line arguments
    arg_parser = argparse.ArgumentParser(description="Network Management System Agent")
    arg_parser.add_argument("--server", "-s",
                            help="Server IP",
                            default="0.0.0.0")
    args = arg_parser.parse_args()

    server_ip = args.server
    agent_id = socket.gethostname()

    udp_client = ClientUDP(server_ip)
    tcp_client = ClientTCP(server_ip)

    # Start listening for server responses (NetTask)
    udp_client.start()

    # First connection to the server
    udp_client.send_first_connection(agent_id)

    # TODO remove this (test alert) (AlertFlow.CPU_USAGE = 0)
    tcp_client.send_alert(0, agent_id, "Test CPU usage Alert")

    try:
        # Loop to keep the main thread running
        while True:
            pass
    except KeyboardInterrupt:
        print("Agent interrupted. Shutting down...")
    finally:
        # TODO send EOC to the server
        udp_client.shutdown()
        tcp_client.shutdown()
        udp_client.join()
        print("Active threads:", threading.enumerate())

    sys.exit(0)


if __name__ == "__main__":
    main()
