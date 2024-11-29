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
    client_task = ClientTask()

    tcp_client = ClientTCP(agent_id, server_ip)
    udp_client = ClientUDP(agent_id, server_ip, pool, client_task, verbose=args.verbose)

    udp_client.start()

    # First connection to the server
    udp_client.send_first_connection()

    # Test metric
    time.sleep(2)
    udp_client.send_metrics(None)

    # Test alert (AlertFlow.CPU_USAGE = 0)
    # tcp_client.send_alert(0, "Test CPU usage Alert")

    # TODO Create execute tasks thread
    # execute_tasks_thread = threading.Thread(target=client_task.run_tasks,
    #                                         daemon=True)

    try:
        # Loop to keep the main thread running
        while udp_client.shutdown_flag.is_set() is False:
            if len(client_task.loaded_tasks) == 0:
                time.sleep(1)
                continue
            print(f"Loaded tasks: {client_task.loaded_tasks}")
            client_task.run_tasks()
            print(f"Task results: {client_task.tasks_results}")
            # TODO remove this: reset task results
            client_task.tasks_results = dict()
            # print(f"Empty task results: {client_task.tasks_results}")
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
                print(f"Packet(s) to be acknowledged: {pool.packets_to_ack}")
                print(f"Time elapsed: {time.time() - start_time}")
            time.sleep(1)

        # Shutdown the clients and await until the threads finish
        udp_client.shutdown()
        tcp_client.shutdown()
        udp_client.join()

        # Display the active threads if verbose mode is enabled
        if args.verbose:
            print("Active threads:", threading.enumerate())

    sys.exit(0)


if __name__ == "__main__":
    main()
