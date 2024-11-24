import threading

from constants import INITIAL_WINDOW_SIZE


class Pool:
    # List of connected agents and respective addresses
    # List of sequence number of each agent
    # List of packets sent yet to be acknowledged by each agent
    # List of packets received yet to be reordered and defragmented
    # Server buffer size (window size)
    def __init__(self):
        self.clients = dict()
        self.seq_numbers = dict()
        self.packets_to_ack = dict()
        self.packets_to_reorder = dict()
        self.window_size = INITIAL_WINDOW_SIZE
        self.lock = threading.Lock()

    ###
    # Clients
    ###

    def add_client(self, client, addr):
        with self.lock:
            self.clients[client] = addr
            self.seq_numbers[client] = 1
            self.packets_to_ack[client] = []
            self.packets_to_reorder[client] = []

    def remove_client(self, client):
        with self.lock:
            del self.clients[client]
            del self.seq_numbers[client]
            del self.packets_to_ack[client]
            del self.packets_to_reorder[client]

    def get_connected_clients(self):
        with self.lock:
            return self.clients

    ###
    # Sequence numbers
    ###

    def get_seq_number(self, client):
        with self.lock:
            return self.seq_numbers[client]

    def set_seq_number(self, client, seq_number):
        with self.lock:
            self.seq_numbers[client] = seq_number

    def inc_seq_number(self, client):
        with self.lock:
            self.seq_numbers[client] += 1
            return self.seq_numbers[client]

    ###
    # Packets sent to be acknowledged
    ###

    def add_packet_to_ack(self, client, packet):
        with self.lock:
            # Set the retransmission flag
            packet["flags"]["retransmission"] = 1
            self.packets_to_ack[client].append(packet)

    def remove_packet_to_ack(self, client, seq_number):
        with self.lock:
            self.packets_to_ack[client] = [f_packet
                                           for f_packet in self.packets_to_ack[client]
                                           if f_packet["seq_number"] != seq_number]

    def get_packets_to_ack(self, client):
        with self.lock:
            return self.packets_to_ack[client]

    ###
    # Packets received to be reordered and defragmented
    # Window size
    ###

    def add_packet_to_reorder(self, client, packet):
        with self.lock:
            self.packets_to_reorder[client].append(packet)
            self.window_size -= 1

    def reorder_packets(self, client, packet):
        try:
            # Add the packet to the list of packets to reorder
            self.add_packet_to_reorder(client, packet)
        except KeyError:
            # No packets to reorder from that client, return the packet as is
            return packet

        with self.lock:
            packets = self.packets_to_reorder[client]

            # filter only packets with the same message id
            packets = [f_packet for f_packet in packets
                       if f_packet["msg_id"] == packet["msg_id"]]

            # reorder packets by sequence number
            packets.sort(key=lambda x: x["seq_number"])

            # defragment data by concatenating the data of all packets
            packet = packets[0]
            for i in range(1, len(packets)):
                packet["data"] += packets[i]["data"]

            # update the window size
            self.window_size += len(packets)

            # remove the defragmented packets from the list of packets to reorder
            self.packets_to_reorder[client] = [f_packet
                                               for f_packet in self.packets_to_reorder[client]
                                               if f_packet not in packets]

            return packet  # packet with defragmented data

    ###
    # Window size
    ###

    def get_window_size(self):
        with self.lock:
            return self.window_size
