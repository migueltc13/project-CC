import threading

from constants import INITIAL_WINDOW_SIZE


class Pool:
    # List of connected agents and respective addresses
    # List of sequence number of each agent
    # List of packets sent yet to be acknowledged by each agent
    # List of packets received yet to be reordered and defragmented
    # List of sequence numbers of packets received (for descarting duplicates)
    # Server buffer size (window size)
    # List of agents window sizes
    def __init__(self):
        self.clients = dict()
        self.seq_numbers = dict()
        self.packets_to_ack = dict()
        self.packets_to_reorder = dict()
        self.packets_received = dict()
        self.agents_window_sizes = dict()
        self.server_window_size = INITIAL_WINDOW_SIZE
        self.lock = threading.Lock()

    ###
    # Clients
    ###

    def add_client(self, client, addr):
        with self.lock:
            self.clients[client] = addr
            self.seq_numbers[client] = 1
            self.packets_to_ack[client] = []

            # The packets to reorder can be already created by the server
            # for that client, so we need to check if it exists before creating
            # This is necessary because the server can receive packets out of order
            if client not in self.packets_to_reorder:
                self.packets_to_reorder[client] = []

            self.packets_received[client] = []

            self.agents_window_sizes[client] = INITIAL_WINDOW_SIZE

    def remove_client(self, client):
        with self.lock:
            if client not in self.clients:
                return
            del self.clients[client]
            del self.seq_numbers[client]
            del self.packets_to_ack[client]
            del self.packets_to_reorder[client]
            del self.packets_received[client]
            del self.agents_window_sizes[client]

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
            copy_packet = packet.copy()
            self.packets_to_ack[client].append(copy_packet)

    def remove_packet_to_ack(self, client, seq_number):
        with self.lock:
            self.packets_to_ack[client] = [f_packet
                                           for f_packet in self.packets_to_ack[client]
                                           if f_packet["seq_number"] != seq_number]

    def get_packets_to_ack(self, client):
        with self.lock:
            return self.packets_to_ack[client]

    def get_nr_packets_to_ack(self):
        with self.lock:
            return sum([len(self.packets_to_ack[client])
                        for client in self.packets_to_ack])

    ###
    # Packets received to be reordered and defragmented
    # Server window size
    ###

    def reorder_packets(self, client, packet):
        with self.lock:
            # Copy the packet to ensure data encapsulation
            copy_packet = packet.copy()

            # Check if client exists
            if client not in self.packets_to_reorder:
                self.packets_to_reorder[client] = []

            # Add the packet to the list of packets to reorder
            self.packets_to_reorder[client].append(copy_packet)
            self.server_window_size -= 1

            # Check if the defragmention/reordering is possible
            # it is possible when all packets with sequence number,
            # between the message id and the last fragment, are received
            # if not possible, return None to wait for the missing packets

            # get all packets to reorder/defragment for the client
            packets = self.packets_to_reorder[client]

            # get the receive packet message id
            message_id = packet["msg_id"]

            # filter only packets with the same message id
            packets = [
                f_packet for f_packet in packets
                if f_packet["msg_id"] == packet["msg_id"]
            ]

            # get the last fragment (if it exists)
            # to check if all packets were received
            last_fragment = None
            for p in packets:
                if p["flags"]["more_fragments"] == 0:
                    last_fragment = p
                    break

            # if the last fragment was not received yet, return None
            if last_fragment is None:
                return None

            # check if all packets with the same message id are received
            # if not, return None
            sequence_numbers = [p["seq_number"] for p in packets]
            for i in range(message_id, last_fragment["seq_number"] + 1):
                if i not in sequence_numbers:
                    return None

            # if the message_id is equal to sequence number of the packet
            # with the last fragment, the message is not fragmented,
            # return the packet as is
            if message_id == last_fragment["seq_number"]:
                # remove the packet from the list of packets to reorder
                self.packets_to_reorder[client] = [
                    f_packet for f_packet in self.packets_to_reorder[client]
                    if f_packet != packet
                ]
                return packet

            # Fragmentation/reordering is possible

            # save the packets to remove from the list of packets to reorder
            buffered_packets = packets.copy()

            # reorder packets by sequence number
            # note: duplicated packets were already removed before calling this method
            packets = sorted(packets, key=lambda x: x["seq_number"])

            # defragment data by concatenating the data of all packets
            packet = packets[0]
            for i in range(1, len(packets)):
                packet["data"] += packets[i]["data"]

            # remove the defragmented packets from the list of packets to reorder
            self.packets_to_reorder[client] = [
                f_packet for f_packet in self.packets_to_reorder[client]
                if f_packet not in buffered_packets
            ]

            # update the window size
            self.server_window_size += len(buffered_packets)

            return packet  # packet with defragmented data

    ###
    # Sequence numbers of packets received
    ###

    def add_packet_received(self, client, seq_number):
        with self.lock:
            if client not in self.packets_received:
                self.packets_received[client] = []
            self.packets_received[client].append(seq_number)

    def is_packet_received(self, client, seq_number):
        with self.lock:
            if client not in self.packets_received:
                return False
            return seq_number in self.packets_received[client]

    ###
    # Server window size
    ###

    def get_server_window_size(self):
        with self.lock:
            return self.server_window_size

    ###
    # Agents window sizes
    ###

    def get_client_window_size(self, client):
        with self.lock:
            try:
                return self.agents_window_sizes[client]
            except KeyError:
                return 1

    def set_client_window_size(self, client, window_size):
        with self.lock:
            try:
                self.agents_window_sizes[client] = window_size
            except KeyError:
                pass
