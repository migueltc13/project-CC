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
        self.agent_window_size = INITIAL_WINDOW_SIZE
        self.server_window_size = INITIAL_WINDOW_SIZE
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

    def reorder_packets(self, packet):
        with self.lock:
            # Copy the packet to ensure data encapsulation
            copy_packet = packet.copy()

            # Add the packet to the list of packets to reorder
            self.packets_to_reorder.append(copy_packet)
            self.agent_window_size -= 1

            # Check if the defragmention/reordering is possible
            # it is possible when all packets with sequence number,
            # between the message id and the last fragment, are received
            # if not possible, return None to wait for the missing packets

            # get all packets to reorder/defragment
            packets = self.packets_to_reorder

            # get the received packet message id
            message_id = packet["msg_id"]

            # filter only packets with the same message id
            packets = [
                f_packet for f_packet in packets
                if f_packet["msg_id"] == message_id
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
                return packet

            # Fragmentation/reordering is possible

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
            self.agent_window_size += len(buffered_packets)

            return packet  # packet with defragmented data

    ###
    # Agent window size
    ###

    def get_agent_window_size(self):
        with self.lock:
            return self.agent_window_size

    ###
    # Server window size
    ###

    def get_server_window_size(self):
        with self.lock:
            return self.server_window_size

    def set_server_window_size(self, window_size):
        with self.lock:
            self.server_window_size = window_size
