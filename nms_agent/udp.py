import socket
import threading
import time
import json

import constants as C

from protocol.net_task import NetTask

# NetTask exceptions
from protocol.exceptions.invalid_version   import InvalidVersionException
from protocol.exceptions.invalid_header    import InvalidHeaderException
from protocol.exceptions.checksum_mismatch import ChecksumMismatchException


class UDP(threading.Thread):
    def __init__(self, agent_id, server_ip, pool, verbose=False):
        super().__init__(daemon=True)
        self.agent_id = agent_id
        self.server_ip = server_ip
        self.server_port = C.UDP_PORT
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.settimeout(1.0)
        self.shutdown_flag = threading.Event()
        self.net_task = NetTask()
        self.pool = pool
        self.lock = threading.Lock()
        self.threads = []
        self.verbose = verbose

        # Initialize the retransmit thread
        ret_thread = threading.Thread(target=self.retransmit_packets)
        self.threads.append(ret_thread)
        ret_thread.start()

    def retransmit_packets(self):
        while not self.shutdown_flag.is_set():
            # Sleep for a while before retransmitting the packets
            time.sleep(C.RETRANSMIT_SLEEP_TIME)
            if self.shutdown_flag.is_set():
                break

            # Get the packets to retransmit and retransmit them
            packets = self.pool.get_packets_to_ack()
            with self.lock:
                for packet in packets:
                    # buld the packet to be retransmitted
                    seq_number = self.pool.get_seq_number()
                    window_size = self.pool.get_window_size()
                    final_seq_number, ret_packets = self.net_task.build_packet(
                        self.net_task, packet["data"],
                        seq_number, packet["flags"],
                        packet["msg_type"], self.agent_id,
                        window_size)

                    for ret_packet in ret_packets:
                        self.client_socket.sendto(ret_packet, (self.server_ip, C.UDP_PORT))

                    # set the sequence number
                    self.pool.set_seq_number(final_seq_number)

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
            except OSError:
                break

    def handle_packet(self, raw_data):
        try:
            packet = self.net_task.parse_packet(self.net_task, raw_data)
        # If any of the exceptions Invalid Header or Checksum Mismatch are raised, the
        # packet is discarded. By not sending an ACK, the server will resend the packet.
        except InvalidVersionException as e:
            # This exception doesn't need to interrupt the agent. We can just
            # print a message and try to process the packet anyway.
            print(e)
        except (InvalidHeaderException, ChecksumMismatchException) as e:
            print(e)
            return

        if self.verbose:
            print(f"Received packet: {json.dumps(packet, indent=2)}")

        # If the packet received is a ACK, process the previous packet sent
        # as acknowledged and remove it from the list of packets to be "acked",
        # for that specific agent. After that we interrupt this function.
        if packet["flags"]["ack"] == 1:
            self.pool.remove_packet_to_ack(packet["data"])
            return

        # TODO respond to window probes

        # Packet reordering and defragmentation
        # if the more_flags is set, add the packet to the list of packets to be reordered
        # else reorder the packets and defragment the data and combine the packets into one
        if packet["flags"]["more_fragments"] == 1:
            self.pool.add_packet_to_reorder(packet)
            return
        else:
            packet = self.pool.reorder_packets(packet)

        # TODO flux control by checking the window size
        # if the URG flag is set, send the packet immediately, regardless of the window size
        # if the window size received is 0, send WINDOW_PROBE until the window size updates
        if packet["flags"]["urgent"] == 1:
            pass
        elif self.pool.get_window_size() == 0:
            # TODO send window probes until the window size updates
            pass

        # Based on the packet type:
        # - Send task: process the task and start running it, sending metrics back to the server
        # - EOC (End of Connection): send a ACK and shutdown the agent
        eoc_received = False
        match packet["msg_type"]:
            case self.net_task.SEND_TASK:
                # TODO add to the task queue/list/class
                pass
            case self.net_task.EOC:
                eoc_received = True

        # Send ACK
        seq_number = self.pool.inc_seq_number()
        if self.verbose:
            print(f"Sending ACK for packet {packet['seq_number']} to server")
        window_size = self.pool.get_window_size()
        seq_number, ack_packet = self.net_task.build_ack_packet(packet, seq_number,
                                                                self.agent_id, window_size)

        # Increment the sequence number for the agent
        # TODO check if the sequence number is correct between agent and server
        self.pool.set_seq_number(seq_number)

        with self.lock:
            self.client_socket.sendto(ack_packet, (self.server_ip, C.UDP_PORT))

        if eoc_received:
            self.shutdown_flag.set()

    def send_first_connection(self):
        seq_number = self.pool.get_seq_number()
        flags = {"urgent": 1}
        msg_type = self.net_task.FIRST_CONNECTION
        window_size = self.pool.get_window_size()
        seq_number, packets = self.net_task.build_packet(self.net_task, "", seq_number, flags,
                                                         msg_type, self.agent_id, window_size)

        # This loop will only run once, since the first connection packet is small (50 bytes)
        for packet in packets:
            with self.lock:
                # send the packet to the server
                self.client_socket.sendto(packet, (self.server_ip, C.UDP_PORT))

            # parse the packet to save it in the list of packets to be acknowledged
            tmp_packet = self.net_task.parse_packet(self.net_task, packet)
            # add the packet to the list of packets to be acknowledged
            self.pool.add_packet_to_ack(tmp_packet)

            if self.verbose:
                print(f"Sending packet: {json.dumps(tmp_packet, indent=2)}")

    # TODO: def send_metric(self, metric):

    def send_end_of_connection(self):
        seq_number = self.pool.get_seq_number()
        flags = {"urgent": 1}
        msg_type = self.net_task.EOC
        window_size = self.pool.get_window_size()
        seq_number, packets = self.net_task.build_packet(self.net_task, "", seq_number, flags,
                                                         msg_type, self.agent_id, window_size)

        for packet in packets:
            with self.lock:
                self.client_socket.sendto(packet, (self.server_ip, C.UDP_PORT))

            # parse the packet to save it in the list of packets to be acknowledged
            tmp_packet = self.net_task.parse_packet(self.net_task, packet)
            # add the packet to the list of packets to be acknowledged
            self.pool.add_packet_to_ack(tmp_packet)

            if self.verbose:
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
