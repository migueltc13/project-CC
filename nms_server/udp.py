import socket
import threading
import sys
import time
import json

import constants as C

from protocol.net_task import NetTask

# NetTask exceptions
from protocol.exceptions.invalid_version   import InvalidVersionException
from protocol.exceptions.invalid_header    import InvalidHeaderException
from protocol.exceptions.checksum_mismatch import ChecksumMismatchException


class UDP(threading.Thread):
    def __init__(self, ui, pool, task_server, verbose=False, host='0.0.0.0'):
        super().__init__(daemon=True)
        self.ui = ui
        self.host = host
        self.port = C.UDP_PORT
        self.server_hostname = ui.server_hostname
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.settimeout(1.0)
        self.shutdown_flag = threading.Event()
        self.net_task = NetTask()
        self.pool = pool
        self.task_server = task_server
        self.lock = threading.Lock()
        self.threads = []
        self.verbose = verbose

        # Start the UDP server
        try:
            # Disable checksum check for UDP (Linux only)
            self.server_socket.setsockopt(socket.SOL_SOCKET, C.SO_NO_CHECK, 1)
            self.server_socket.bind((self.host, self.port))
        except OSError:
            self.ui.display_error(f"UDP port {self.port} is already in use. Exiting.")
            sys.exit(1)
        self.ui.save_status(f"UDP Server started on port {self.port}")

        # Initialize the retransmit thread
        ret_thread = threading.Thread(target=self.retransmit_packets)
        self.threads.append(ret_thread)
        ret_thread.start()

        # Initialize the window size control thread
        win_thread = threading.Thread(target=self.window_size_control)
        self.threads.append(win_thread)
        win_thread.start()

    # NOTE retransmission of packets does not increment the sequence number
    def retransmit_packets(self):
        while not self.shutdown_flag.is_set():
            # Sleep for a while before retransmitting the packets
            time.sleep(C.RETRANSMIT_SLEEP_TIME)
            if self.shutdown_flag.is_set():
                break

            # Get the connected agents and respective addresses
            agents = self.pool.get_connected_clients()

            # For each agent, get the packets to retransmit and retransmit them
            for agent_id in agents:
                addr = agents[agent_id]
                packets = self.pool.get_packets_to_ack(agent_id)
                for packet in packets:
                    # build the packet to be retransmitted and set the retransmission flag
                    seq_number = self.pool.get_seq_number(agent_id)
                    window_size = self.pool.get_server_window_size()
                    flags = packet["flags"]
                    flags["retransmission"] = 1
                    _, ret_packets = self.net_task.build_packet(
                        self.net_task, packet["data"],
                        seq_number, flags,
                        packet["msg_type"], agent_id,
                        window_size)

                    # wait if the server window size is 0 and the URG flag is not set
                    urgent = flags.get("urgent", 0)
                    if urgent == 0:
                        while self.pool.get_client_window_size(agent_id) <= 0:
                            time.sleep(1)

                    for ret_packet in ret_packets:
                        with self.lock:
                            self.server_socket.sendto(ret_packet, addr)

                        if self.verbose and self.ui.view_mode:
                            print(f"Retransmitting packet: {json.dumps(packet, indent=2)}")

    def window_size_control(self):
        while not self.shutdown_flag.is_set():
            # Sleep for a while before retransmitting the packets
            time.sleep(C.WINDOW_PROBE_SLEEP_TIME)
            if self.shutdown_flag.is_set():
                break

            # Get the connected agents and respective addresses
            agents = self.pool.get_connected_clients()

            # For each agent, if his window size is 0, send a window probe
            for agent_id in agents:
                addr = agents[agent_id]
                window_size = self.pool.get_client_window_size(agent_id)
                if window_size <= 0:
                    self.send("", {"urgent": 1, "window_probe": 1},
                              self.net_task.UNDEFINED, agent_id, addr)

                    if self.verbose and self.ui.view_mode:
                        print(f"Sending window probe to {agent_id}")

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
                # INFO To process the packets sequentially, join the thread
                # handle_packet_thread.join()
            except socket.timeout:
                continue
            except OSError:
                break

    def handle_packet(self, raw_data, addr):
        try:
            packet = self.net_task.parse_packet(self.net_task, raw_data)
        # If any of the exceptions Invalid Header or Checksum Mismatch are raised, the
        # packet is discarded. By not sending an ACK, the agent will resend the packet.
        except InvalidVersionException as e:
            # This exception doesn't need to interrupt the server. We can just
            # send a message in the UI and try to process the packet anyway.
            self.ui.display_warning(e)
        except (InvalidHeaderException, ChecksumMismatchException) as e:
            self.ui.display_error(e)
            return

        if self.verbose and self.ui.view_mode:
            print(f"Received packet: {json.dumps(packet, indent=2)}")

        agent_id = packet["identifier"]

        # Save the received agent window size
        self.pool.set_client_window_size(agent_id, packet["window_size"])

        # If the packet received is a ACK, process the previous packet sent
        # as acknowledged and remove it from the list of packets to be "acked",
        # for that specific agent. After that we interrupt this function.
        if packet["flags"]["ack"] == 1:
            self.pool.remove_packet_to_ack(agent_id, packet["seq_number"])
            return

        # Handle first connection by adding the client to the pool
        if packet["msg_type"] == self.net_task.FIRST_CONNECTION:
            self.pool.add_client(agent_id, addr)

        # send ACK
        window_size = self.pool.get_server_window_size()
        ack_packet = self.net_task.build_ack_packet(packet, agent_id, window_size)

        with self.lock:
            self.server_socket.sendto(ack_packet, addr)

        if self.verbose and self.ui.view_mode:
            print(f"Sending ACK for packet {packet['seq_number']} to {agent_id}")

        # whenever the server receives a duplicated packet,
        # the ack is sent, but the packet is discarded
        if self.pool.is_packet_received(agent_id, packet["seq_number"]):
            return

        # add the sequence number to the list of received packets
        self.pool.add_packet_received(agent_id, packet["seq_number"])

        # increment the sequence number
        self.pool.inc_seq_number(agent_id)

        # Packet reordering and defragmentation
        packet = self.pool.reorder_packets(agent_id, packet)
        if packet is None:
            if self.verbose and self.ui.view_mode:
                print(f"Adding packet to defrag/reorder array for {agent_id}")
            return  # wait for the missing packets

        # if self.verbose and self.ui.view_mode:
        #     print(f"Possible defragmented packet: {json.dumps(packet, indent=2)}")

        # Based on the packet type:
        # - First connection: add the client to the clients pool
        # - Task Metric: save the metric, after parsing data (also save the agent hostname)
        # - End of connection: remove the client from the clients pool
        eoc_received = False
        match packet["msg_type"]:
            case self.net_task.FIRST_CONNECTION:
                # Send tasks to the agent
                self.send_tasks(agent_id, addr)
            case self.net_task.SEND_METRICS:
                metrics = json.loads(packet["data"])
                self.ui.save_metrics(agent_id, metrics)
            case self.net_task.EOC:
                eoc_received = True

        # De/fragmentation test
        # self.send("A" * 3000, {}, self.net_task.UNDEFINED, agent_id, addr)

        if eoc_received:
            self.pool.remove_client(agent_id)
            self.ui.save_status(f"Agent {agent_id} disconnected.")

    def send(self, data, flags, msg_type, agent_id, addr):
        seq_number = self.pool.get_seq_number(agent_id)
        window_size = self.pool.get_server_window_size()
        seq_number, packets = self.net_task.build_packet(self.net_task, data, seq_number, flags,
                                                         msg_type, agent_id, window_size)

        # set the sequence number
        self.pool.set_seq_number(agent_id, seq_number)

        # Flux control by checking the window size
        # if the URG flag is set, send the packet immediately, regardless of the window size
        # if the window size received is 0, the window size control thread will send window probe
        # packets to the agents with window size 0
        urgent = flags.get("urgent", 0)
        if urgent == 0:
            while self.pool.get_client_window_size(agent_id) <= 0:
                time.sleep(1)
                if self.verbose and self.ui.view_mode:
                    print(f"Agent {agent_id} window size is 0 or less. Waiting...")

        for packet in packets:
            with self.lock:
                self.server_socket.sendto(packet, addr)

            # parse the packet to save it in the list of packets to be acknowledged
            tmp_packet = self.net_task.parse_packet(self.net_task, packet)
            # add the packet to the list of packets to be acknowledged
            self.pool.add_packet_to_ack(agent_id, tmp_packet)

            if self.verbose and self.ui.view_mode:
                print(f"Sending packet: {json.dumps(tmp_packet, indent=2)}")

    def send_tasks(self, agent_id, addr):
        tasks = self.task_server.get_agent_tasks(agent_id)
        if tasks:
            for task in tasks:
                self.send(json.dumps(task), {}, self.net_task.SEND_TASKS, agent_id, addr)
                if self.verbose and self.ui.view_mode:
                    print(f"Sending task {task['task_id']} to {agent_id}")
        elif self.verbose and self.ui.view_mode:
            print(f"No tasks to send to {agent_id}")

    def send_end_of_connection(self):
        # Get the connected agents and respective addresses
        agents = self.pool.get_connected_clients()

        # For each agent, send the EOC packet
        for agent_id in self.pool.get_connected_clients():
            addr = agents[agent_id]
            msg_type = self.net_task.EOC

            self.send("", {"urgent": 1}, msg_type, agent_id, addr)

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
