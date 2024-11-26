import threading

from constants import INITIAL_WINDOW_SIZE


class Pool:
    # Current sequence number
    # List of packets sent yet to be
    # List of packets received yet to be reordered and defragmented
    # Agent buffer size (window size)
    def __init__(self):
        self.seq_number = 1
        self.packets_to_ack = []
        self.packets_to_reorder = []
        self.window_size = INITIAL_WINDOW_SIZE
        self.lock = threading.Lock()

    ###
    # Sequence number
    ###

    def get_seq_number(self):
        with self.lock:
            return self.seq_number

    def set_seq_number(self, seq_number):
        with self.lock:
            self.seq_number = seq_number

    def inc_seq_number(self):
        with self.lock:
            self.seq_number += 1
            return self.seq_number

    ###
    # Packets sent to be acknowledged
    ###

    def add_packet_to_ack(self, packet):
        with self.lock:
            copy_packet = packet.copy()
            self.packets_to_ack.append(copy_packet)

    # Remove the acknowledged packet by the sequence number
    def remove_packet_to_ack(self, seq_number):
        with self.lock:
            self.packets_to_ack = [f_packet
                                   for f_packet in self.packets_to_ack
                                   if f_packet["seq_number"] != seq_number]

    def get_packets_to_ack(self):
        with self.lock:
            return self.packets_to_ack

    def get_nr_packets_to_ack(self):
        with self.lock:
            return len(self.packets_to_ack)

    ###
    # Packets received to be reordered and defragmented
    # Window size
    ###

    def add_packet_to_reorder(self, packet):
        with self.lock:
            copy_packet = packet.copy()
            self.packets_to_reorder.append(copy_packet)
            self.window_size -= 1

    def reorder_packets(self, packet):
        try:
            # Add the packet to the list of packets to reorder
            self.add_packet_to_reorder(packet)
        except KeyError:
            # No packets to reorder from server, return the packet as is
            return packet

        with self.lock:
            packets = self.packets_to_reorder

            # filter only packets with the same message id
            packets = [
                f_packet for f_packet in packets
                if f_packet["msg_id"] == packet["msg_id"]
            ]

            # save the packets to remove from the list of packets to reorder
            buffered_packets = packets.copy()

            # remove dupplicate packets by the sequence number
            unique_packets = {}
            for p in packets:
                if p["seq_number"] not in unique_packets:
                    unique_packets[p["seq_number"]] = p

            # reorder packets by sequence number
            packets = sorted(unique_packets.values(), key=lambda x: x["seq_number"])

            # defragment data by concatenating the data of all packets
            packet = packets[0]
            for i in range(1, len(packets)):
                packet["data"] += packets[i]["data"]

            # remove the defragmented packets from the list of packets to reorder
            self.packets_to_reorder = [
                f_packet for f_packet in self.packets_to_reorder
                if f_packet not in buffered_packets
            ]

            # update the window size
            self.window_size += len(buffered_packets)

            return packet  # packet with defragmented data

    ###
    # Window size
    ###

    def get_window_size(self):
        with self.lock:
            return self.window_size
