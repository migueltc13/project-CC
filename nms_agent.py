#!/usr/bin/env python3

import socket
import threading
import sys
import argparse

from nms_agent import (
    ClientTCP,
    ClientUDP,
    ClientPool
)


def main():
    # Parse command line arguments
    arg_parser = argparse.ArgumentParser(description="Network Management System Agent")
    arg_parser.add_argument("-s", "--server",
                            help="Server IP",
                            default="0.0.0.0")
    arg_parser.add_argument("-v", "--verbose",
                            help="Enable verbose output",
                            action="store_true")
    args = arg_parser.parse_args()

    server_ip = args.server
    agent_id = socket.gethostname()

    pool = ClientPool()

    tcp_client = ClientTCP(agent_id, server_ip)
    udp_client = ClientUDP(agent_id, server_ip, pool, verbose=args.verbose)

    udp_client.start()

    # First connection to the server
    udp_client.send_first_connection()

    # Test alert (AlertFlow.CPU_USAGE = 0)
    # tcp_client.send_alert(0, "Test CPU usage Alert")

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
        if args.verbose:
            print("Active threads:", threading.enumerate())

    sys.exit(0)


if __name__ == "__main__":
    main()
