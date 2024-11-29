#!/usr/bin/env python3

import socket
import threading
import sys
import argparse
import time


from constants import EOC_ACK_TIMEOUT

from nms_server import (
    ServerUI,
    ServerPool,
    TCPServer,
    UDPServer,
    TaskServer,
    Config
)


def main():
    # Parse command line arguments
    arg_parser = argparse.ArgumentParser(description="Network Management System Server")
    arg_parser.add_argument("-c", "--config",
                            help="Configuration file path",
                            default=Config.CONFIG_PATH)
    arg_parser.add_argument("-v", "--verbose",
                            help="Enable verbose output",
                            action="store_true")
    args = arg_parser.parse_args()

    # Load the configuration file
    config = Config.load_config(args.config)
    if config is None:
        print("Failed to load configuration. Exiting...")
        sys.exit(1)

    # Initialize the server
    server_hostname = socket.gethostname()

    pool = ServerPool()
    task_server = TaskServer(config)

    ui = ServerUI(server_hostname, pool, verbose=args.verbose)
    ui.display_title()

    tcp_server = TCPServer(ui)
    udp_server = UDPServer(ui, pool, task_server, verbose=args.verbose)

    tcp_server.start()
    udp_server.start()

    try:
        ui.main_menu(tcp_server, udp_server, config)
    except (KeyboardInterrupt, EOFError):
        ui.display_info("Server interrupted. Shutting down...")
    finally:
        # Send EOC to all agents and await until the agents send the ACK
        # or after some seconds, if the agents don't respond, shutdown the server
        udp_server.send_end_of_connection()
        start_time = time.time()
        while (pool.get_nr_packets_to_ack() > 0 and
               time.time() - start_time < EOC_ACK_TIMEOUT):
            if args.verbose:
                print(f"Nr of packs to be acknowledged: {pool.get_nr_packets_to_ack()}")
                print(f"Time elapsed: {time.time() - start_time}")
            time.sleep(1)

        # Shutdown the servers and await until the threads finish
        tcp_server.shutdown()
        udp_server.shutdown()
        tcp_server.join()
        udp_server.join()

        # Display the active threads if verbose mode is enabled
        if (args.verbose):
            print("Active threads:", threading.enumerate())

        # Log the server shutdown
        ui.save_status("Server shutdown complete.")

    sys.exit(0)


if __name__ == "__main__":
    main()
