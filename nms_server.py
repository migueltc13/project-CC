#!/usr/bin/env python3

import socket
import threading
import sys
import argparse

from nms_server import ServerUI
from nms_server import ServerPool
from nms_server import TCPServer
from nms_server import UDPServer
from nms_server import Config


def main():
    arg_parser = argparse.ArgumentParser(description="Network Management System Server")
    arg_parser.add_argument("--config", "-c",
                            help="Configuration file path",
                            default=Config.CONFIG_PATH)
    args = arg_parser.parse_args()

    config = Config.load_config(args.config)
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
        # TODO send EOC to all connected agents
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
