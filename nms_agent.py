#!/usr/bin/env python3

import socket
import threading
import sys
import argparse
import time


from constants import EOC_ACK_TIMEOUT

from nms_agent import (
    ClientTCP,
    ClientUDP,
    ClientPool,
    ClientTask
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
    client_task = ClientTask(verbose=args.verbose)

    tcp_client = ClientTCP(agent_id, server_ip)
    udp_client = ClientUDP(agent_id, server_ip, pool, client_task, verbose=args.verbose)

    client_task.set_client_tcp(tcp_client)
    client_task.set_client_udp(udp_client)

    udp_client.start()

    # First connection to the server
    udp_client.send_first_connection()

    # Test alert
    # tcp_client.send_alert("Test CPU usage Alert")

    # Start the task executer thread
    client_task.start()

    try:
        # Loop to keep the main thread running
        while udp_client.shutdown_flag.is_set() is False:
            if len(client_task.loaded_tasks) == 0:
                print("No tasks loaded. Waiting...")
                time.sleep(1)
                continue
    except KeyboardInterrupt:
        print("Agent interrupted. Shutting down...")
    finally:
        # Send EOC to the server and await until the server sends the ACK
        # or after some seconds, if the server doesn't respond, shutdown the agent
        udp_client.send_end_of_connection()
        start_time = time.time()
        while (pool.get_nr_packets_to_ack() > 0 and
               time.time() - start_time < EOC_ACK_TIMEOUT):
            if args.verbose:
                print(f"Nr of packs to be acknowledged: {pool.get_nr_packets_to_ack()}")
                # print(f"Packet(s) to be acknowledged: {pool.packets_to_ack}")
                print(f"Time elapsed: {time.time() - start_time}")
            time.sleep(1)

        # Shutdown the task executer
        print("Shutting down the task executer...")
        client_task.shutdown()
        client_task.join()

        # Shutdown the clients and await until the threads finish
        print("Shutting down the udp and tcp clients...")
        udp_client.shutdown()
        tcp_client.shutdown()
        udp_client.join()

        # Display the active threads if verbose mode is enabled
        if args.verbose:
            print("Active threads:", threading.enumerate())

    sys.exit(0)


if __name__ == "__main__":
    main()
