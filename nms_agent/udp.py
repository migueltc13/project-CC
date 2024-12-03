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
    def __init__(self, agent_id, server_ip, pool, client_task, verbose=False):
        super().__init__(daemon=True)
        self.agent_id = agent_id
        self.server_ip = server_ip
        self.server_port = C.UDP_PORT
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.settimeout(1.0)
        self.shutdown_flag = threading.Event()
        self.net_task = NetTask()
        self.pool = pool
        self.client_task = client_task
        self.lock = threading.Lock()
        self.threads = []
        self.verbose = verbose

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

            # Get the packets to retransmit and retransmit them
            packets = self.pool.get_packets_to_ack()
            for packet in packets:
                # build the packet to be retransmitted and set the retransmission flag
                seq_number = self.pool.get_seq_number()
                window_size = self.pool.get_agent_window_size()
                flags = packet["flags"]
                flags["retransmission"] = 1
                _, ret_packets = self.net_task.build_packet(
                    self.net_task, packet["data"],
                    seq_number, flags,
                    packet["msg_type"], self.agent_id,
                    window_size)

                for ret_packet in ret_packets:
                    # wait if the server window size is 0
                    while self.pool.get_server_window_size() == 0:
                        time.sleep(0.1)

                    with self.lock:
                        self.client_socket.sendto(ret_packet, (self.server_ip, C.UDP_PORT))

                    if self.verbose:
                        print(f"Retransmitting packet: {json.dumps(packet, indent=2)}")

    def window_size_control(self):
        while not self.shutdown_flag.is_set():
            # Sleep for a while before probing the window size
            time.sleep(C.WINDOW_PROBE_SLEEP_TIME)
            if self.shutdown_flag.is_set():
                break

            # Get the window size of the server
            window_size = self.pool.get_server_window_size()
            if window_size == 0:
                self.send("", {"urgent": 1, "window_probe": 1},
                          self.net_task.UNDEFINED)

                if self.verbose:
                    print("Sending window probe to server")

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

        # Save the received server window size
        self.pool.set_server_window_size(packet["window_size"])

        # If the packet received is a ACK, process the previous packet sent
        # as acknowledged and remove it from the list of packets to be "acked",
        # for that specific agent. After that we interrupt this function.
        if packet["flags"]["ack"] == 1:
            self.pool.remove_packet_to_ack(packet["seq_number"])
            return

        # send ACK
        window_size = self.pool.get_agent_window_size()
        ack_packet = self.net_task.build_ack_packet(packet, self.agent_id, window_size)

        with self.lock:
            self.client_socket.sendto(ack_packet, (self.server_ip, C.UDP_PORT))

        # whenever the agent receives a duplicated packet,
        # the ack is sent, but the packet is discarded
        if self.pool.is_packet_received(packet["seq_number"]):
            return

        # Add the sequence number to the list of received packets
        self.pool.add_packet_received(packet["seq_number"])

        # Increment the sequence number
        self.pool.inc_seq_number()

        # Flux control by checking the window size
        # if the URG flag is set, send the packet immediately, regardless of the window size
        # if the window size received is 0, the window size control thread will send window probe
        # packets to the server
        if packet["flags"]["urgent"] == 0:
            while self.pool.get_server_window_size() == 0:
                time.sleep(1)
                if self.verbose:
                    print("Server window size is 0. Waiting...")

        # Packet reordering and defragmentation
        packet = self.pool.reorder_packets(packet)
        if packet is None:
            if self.verbose:
                print("Adding packet to defrag/reorder array")
            return  # wait for the missing packets

        if self.verbose:
            print(f"Possible defragmented packet: {json.dumps(packet, indent=2)}")

        # Based on the packet type:
        # - Send task: process the task and start running it, sending metrics back to the server
        # - EOC (End of Connection): send a ACK and shutdown the agent
        eoc_received = False
        match packet["msg_type"]:
            case self.net_task.SEND_TASKS:
                # Add the task to the loaded tasks list
                if self.verbose:
                    print("Received task")
                # Parse json data to dict
                data = json.loads(packet["data"])
                self.client_task.add_task(data)
            case self.net_task.EOC:
                eoc_received = True

        if eoc_received:
            self.shutdown_flag.set()

    def send(self, data, flags, msg_type):
        seq_number = self.pool.get_seq_number()
        window_size = self.pool.get_agent_window_size()
        seq_number, packets = self.net_task.build_packet(self.net_task, data, seq_number, flags,
                                                         msg_type, self.agent_id, window_size)

        # set the sequence number
        self.pool.set_seq_number(seq_number)

        for packet in packets:
            with self.lock:
                self.client_socket.sendto(packet, (self.server_ip, C.UDP_PORT))

            # parse the packet to save it in the list of packets to be acknowledged
            tmp_packet = self.net_task.parse_packet(self.net_task, packet)
            # add the packet to the list of packets to be acknowledged
            self.pool.add_packet_to_ack(tmp_packet)

            if self.verbose:
                print(f"Sending packet: {json.dumps(tmp_packet, indent=2)}")

    def send_first_connection(self):
        data = ""
        flags = {"urgent": 1}
        msg_type = self.net_task.FIRST_CONNECTION

        self.send(data, flags, msg_type)

    def send_metric(self, metrics):
        flags = {}
        msg_type = self.net_task.SEND_METRICS

        self.send(metrics, flags, msg_type)

    def send_end_of_connection(self):
        data = ""
        flags = {"urgent": 1}
        msg_type = self.net_task.EOC

        self.send(data, flags, msg_type)

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
