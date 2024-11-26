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
    def __init__(self, ui, pool, verbose=False, host='0.0.0.0'):
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

        # Retransmit packets to be acknowledged
        ret_thread = threading.Thread(target=self.retransmit_packets)
        self.threads.append(ret_thread)
        ret_thread.start()

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
            for agent in agents:
                addr = agents[agent]
                packets = self.pool.get_packets_to_ack(agent)
                with self.lock:
                    for packet in packets:
                        # buld the packet to be retransmitted
                        seq_number = self.pool.get_seq_number(agent)
                        window_size = self.pool.get_window_size()
                        _, ret_packets = self.net_task.build_packet(
                            self.net_task, packet["data"],
                            seq_number, packet["flags"],
                            packet["msg_type"], agent,
                            window_size)

                        for ret_packet in ret_packets:
                            self.server_socket.sendto(ret_packet, addr)

                            if self.verbose and self.ui.view_mode:
                                print(f"Retransmitting packet: {json.dumps(packet, indent=2)}")

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

        # If the packet received is a ACK, process the previous packet sent
        # as acknowledged and remove it from the list of packets to be "acked",
        # for that specific agent. After that we interrupt this function.
        if packet["flags"]["ack"] == 1:
            self.pool.remove_packet_to_ack(agent_id, packet["seq_number"])
            return

        # Handle first connection by adding the client to the pool
        if packet["msg_type"] == self.net_task.FIRST_CONNECTION:
            self.pool.add_client(agent_id, addr)

        # Whenever a packet is received, the server updated the respective agent's
        # sequence number, unless the packet is a ack or retransmission
        if packet["flags"]["retransmission"] == 0:
            self.pool.inc_seq_number(agent_id)

        # send ACK
        window_size = self.pool.get_window_size()
        ack_packet = self.net_task.build_ack_packet(packet, agent_id, window_size)

        with self.lock:
            self.server_socket.sendto(ack_packet, addr)

        if self.verbose and self.ui.view_mode:
            print(f"Sending ACK for packet {packet['seq_number']} to {agent_id}")

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

        # Based on the packet type:
        # - First connection: add the client to the clients pool
        # - Task Metric: save the metric, after parsing data (also save the agent hostname)
        # - End of connection: remove the client from the clients pool
        eoc_received = False
        match packet["msg_type"]:
            case self.net_task.SEND_METRICS:
                # self.ui.save_metric(agent_id, f"Metric data: {packet['data']}")
                print("TODO save metric")  # TODO
            case self.net_task.EOC:
                eoc_received = True

        if eoc_received:
            self.pool.remove_client(agent_id)
            self.ui.save_status(f"Agent {agent_id} disconnected.")

    def send_end_of_connection(self):
        # Get the connected agents and respective addresses
        agents = self.pool.get_connected_clients()

        # For each agent, send the EOC packet
        for agent in agents:
            addr = agents[agent]
            seq_number = self.pool.get_seq_number(agent)
            flags = {"urgent": 1}
            msg_type = self.net_task.EOC
            window_size = self.pool.get_window_size()
            seq_number, eoc_packets = self.net_task.build_packet(self.net_task, "", seq_number,
                                                                 flags, msg_type, agent,
                                                                 window_size)

            # Increment the sequence number for the agent
            self.pool.set_seq_number(agent, seq_number)

            for eoc_packet in eoc_packets:
                with self.lock:
                    self.server_socket.sendto(eoc_packet, addr)

                # parse the packet to save it in the list of packets to be acknowledged
                tmp_packet = self.net_task.parse_packet(self.net_task, eoc_packet)
                # add the packet to the list of packets to be acknowledged
                self.pool.add_packet_to_ack(agent, tmp_packet)

                if self.verbose and self.ui.view_mode:
                    print(f"Sending packet: {json.dumps(tmp_packet, indent=2)}")

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
