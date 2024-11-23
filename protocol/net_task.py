# NetTask app protocol for communication between the server and the agents.

import struct
import constants as C

# NetTask Header:
# - Packet Size     ( 4 bytes)
# - NetTask version ( 1 byte)
# - Sequence number ( 2 bytes)
# - Flags and Type  ( 1 byte)
# - Fragment Offset ( 4 bytes)
# - Window size     ( 2 bytes)
# - Checksum        ( 2 bytes)
# - Message ID      ( 2 bytes)
# - Identifier      (32 bytes) [Default: UTF-8]
# - Data            ( N bytes) [Default: UTF-8] [If ACK: ACK seq. number]

# Packet flags:
# ARUWF0000 where:
# - A: ACK
# - R: Retransmission
# - U: Urgent
# - W: Window Probe
# - F: More Fragments
# _____001 - 1 - First connection [Server  <- Agent]
# _____010 - 2 - Send task        [Server  -> Agent]
# _____011 - 3 - Send metrics     [Server  <- Agent]
# _____100 - 4 - EOC              [Server <-> Agent]
# _____*** - Reserved message types

# Integers like sequence number, fragment offset, window size, and ACK seq. number
# are stored in network byte order (big-endian) unsigned integers.

# If the flag ACK is set, the payload data will contain 4 bytes
# with the sequence number of the message being acknowledged.


###
# Constants
###

# Constants for header field sizes
SIZE_PACKET_SIZE = 4
SIZE_NMS_VERSION = 1
SIZE_SEQ_NUMBER  = 2
SIZE_FLAGS_TYPE  = 1
SIZE_FRAGMENT    = 4
SIZE_WINDOW_SIZE = 2
SIZE_CHECKSUM    = 2
SIZE_MSG_ID      = 2
SIZE_IDENTIFIER  = 32

# Header total size
HEADER_SIZE = (SIZE_PACKET_SIZE + SIZE_NMS_VERSION + SIZE_SEQ_NUMBER +
               SIZE_FLAGS_TYPE + SIZE_FRAGMENT + SIZE_WINDOW_SIZE +
               SIZE_CHECKSUM + SIZE_MSG_ID + SIZE_IDENTIFIER)

# Struct format for the header fields
# !    network (big-endian) byte order
# B    unsigned char       (1 byte)
# H    unsigned short      (2 bytes)
# I    unsigned int        (4 bytes)
# Xs   string with X chars (X bytes)
STRUCT_FORMAT = '!I B H B I H H H 32s'


###
# NetTask Main Class
###

class NetTask:
    # Constants for message types
    FIRST_CONNECTION = 1
    SEND_TASK        = 2
    SEND_METRICS     = 3
    EOC              = 4

    # Calculate the checksum of a packet, padding the checksum field with 0
    @staticmethod
    def calculate_checksum(packet):
        checksum_start = (SIZE_PACKET_SIZE + SIZE_NMS_VERSION + SIZE_SEQ_NUMBER +
                          SIZE_FLAGS_TYPE + SIZE_FRAGMENT + SIZE_WINDOW_SIZE)
        checksum_end = checksum_start + SIZE_CHECKSUM
        data = packet[:checksum_start] + packet[checksum_end:]

        # Calculate a 16-bit checksum of the packet
        checksum = 0
        for i in range(0, len(data), 2):
            part = data[i:i + 2]
            if len(part) == 1:
                # If there's a single byte left, pad it
                part += b'\x00'
            checksum += int.from_bytes(part, 'big')

        # Fold 32-bit checksum to 16-bit
        while checksum > 0xFFFF:
            checksum = (checksum & 0xFFFF) + (checksum >> 16)

        # Return the one's complement of the checksum
        return ~checksum & 0xFFFF

    # usage: ack_flag, parsed_packet = NetTask.parser(packet)
    @staticmethod
    def parse_packet(self, packet):
        # Extract the header and data
        header = packet[:HEADER_SIZE]
        data = packet[HEADER_SIZE:]

        # Unpack the header fields
        try:
            # Check if the NMS NetTask version is correct before unpacking the rest of the header
            version = header[SIZE_PACKET_SIZE:SIZE_PACKET_SIZE + SIZE_NMS_VERSION]
            version = int.from_bytes(version, byteorder='big')
            if version != C.NET_TASK_VERSION:
                raise InvalidVersionException(version, C.NET_TASK_VERSION)

            packet_size, version, seq_number, flags_type, fragment_offset, \
                window_size, checksum, msg_id, identifier = struct.unpack(STRUCT_FORMAT, header)

        except Exception:
            raise InvalidHeaderException()

        # Checksum validation
        if self.calculate_checksum(packet) != checksum:
            print(f"Checksum mismatch: {self.calculate_checksum(packet)} != {checksum}")
            raise ChecksumMismatchException()

        # Parse flags and message type
        ack_flag            = (flags_type & 0b10000000) >> 7
        retransmission_flag = (flags_type & 0b01000000) >> 6
        urgent_flag         = (flags_type & 0b00100000) >> 5
        window_probe_flag   = (flags_type & 0b00010000) >> 4
        more_fragments_flag = (flags_type & 0b00001000) >> 3
        msg_type            = (flags_type & 0b00000111)

        # Remove padding from the identifier
        identifier = identifier.rstrip(b'\x00')

        return {
            "packet_size": packet_size,
            "version": version,
            "seq_number": seq_number,
            "flags": {
                "ack": ack_flag,
                "retransmission": retransmission_flag,
                "urgent": urgent_flag,
                "window_probe": window_probe_flag,
                "more_fragments": more_fragments_flag,
            },
            "msg_type": msg_type,
            "fragment_offset": fragment_offset,
            "window_size": window_size,
            "checksum": checksum,
            "msg_id": msg_id,
            "identifier": identifier.decode(C.ENCODING),
            # If the packet is an ACK, the data field will contain the
            # sequence number of the message being acknowledged
            "data": (data.decode(C.ENCODING)
                     if ack_flag == 0
                     else int.from_bytes(data, byteorder='big'))
        }

    @staticmethod
    def build_header(self, seq_number, flags_type, fragment_offset,
                     window_size, msg_id, identifier, data, is_ack=False):

        packet_size = (HEADER_SIZE + len(data)
                       if not is_ack
                       else HEADER_SIZE + SIZE_SEQ_NUMBER)

        # Initial header with checksum set to 0
        header = struct.pack(
            STRUCT_FORMAT,
            packet_size,
            C.NET_TASK_VERSION,
            seq_number,
            flags_type,
            fragment_offset,
            window_size,
            0,  # Placeholder for checksum
            msg_id,
            identifier.encode(C.ENCODING)
        )

        # Concatenate header and data to calculate the checksum
        if not is_ack:
            if isinstance(data, str):
                data = data.encode(C.ENCODING)
        else:
            data = data.to_bytes(2, byteorder='big')
        packet = header + data
        checksum = self.calculate_checksum(packet)

        # Repack the header with the actual checksum
        header = struct.pack(
            STRUCT_FORMAT,
            packet_size,
            C.NET_TASK_VERSION,
            seq_number,
            flags_type,
            fragment_offset,
            window_size,
            checksum,
            msg_id,
            identifier.encode(C.ENCODING)
        )

        return header

    @staticmethod
    def build_packet(self, data, seq_number, flags, msg_type, identifier, window_size):

        if isinstance(data, str):
            data = data.encode(C.ENCODING)

        # Set flags and type field
        flags_type = (
            (flags.get("ack",            0) << 7) |
            (flags.get("retransmission", 0) << 6) |
            (flags.get("urgent",         0) << 5) |
            (flags.get("window_probe",   0) << 4) |
            (flags.get("more_fragments", 0) << 3) |
            (msg_type & 0b00000111)
        )

        packets = []
        msg_id = seq_number

        # Split the data to fragments of size NET_TASK_BUFFER_SIZE (default: 1500 bytes)
        data_chunk_size = C.BUFFER_SIZE - HEADER_SIZE

        data_segments = ([data[i:i + data_chunk_size]
                         for i in range(0, len(data), data_chunk_size)] or [b""])

        for i, data_segment in enumerate(data_segments):
            fragment_offset = i * (len(data_segment) + HEADER_SIZE)

            # Set the "more_fragments" flag
            flags["more_fragments"] = 1 if i < len(data_segments) - 1 else 0

            # Build the header
            header = self.build_header(self,
                                       seq_number,
                                       flags_type,
                                       fragment_offset,
                                       window_size,
                                       msg_id,
                                       identifier,
                                       data_segment)

            # Build the packet and append it to the list
            packet = header + data_segment
            packets.append(packet)

            # Increment the sequence number for the next fragment
            seq_number += 1

        return seq_number, packets

    def build_ack_packet(self, packet, seq_number, identifier, window_size):
        # Set the appropriate flags for the ACK packet combine the remaining
        # flags and type of the packet being acknowledged
        flags_type = (
            (1 << 7) |  # ACK flag
            (0 << 6) |  # No retransmission
            (packet['flags'].get("urgent", 0) << 5) |
            (0 << 4) |  # No window probe
            (0 << 3) |  # No more fragments
            (packet["msg_type"] & 0b00000111)
        )

        ack_number = packet["seq_number"]

        # Build the header
        header = self.build_header(self,
                                   seq_number,
                                   flags_type,
                                   0,           # No fragment offset
                                   window_size,
                                   seq_number,  # Message ID: seq nr of the packet to acknowledge
                                   identifier,
                                   ack_number,  # Data: seq nr of the packet to acknowledge
                                   is_ack=True)

        return seq_number + 1, header + ack_number.to_bytes(2, byteorder='big')


###
# Exceptions TODO merge with AlertFlow exceptions
###

class InvalidHeaderException(Exception):
    # Exception raised for invalid NetTask header
    def __init__(self, message="Invalid header"):
        self.message = message
        super().__init__(self.message)
    pass

    def __str__(self):
        return f'{self.message}'


class InvalidVersionException(Exception):
    # Exception raised for invalid NMS NetTask version
    def __init__(self, received_version, expected_version, message="Invalid NMS NetTask version"):
        self.expected_version = expected_version
        self.received_version = received_version
        self.message = f"{message}\n" \
                       f"Received version: {received_version}\n" \
                       f"Expected version: {expected_version}"
        super().__init__(self.message)
    pass

    def __str__(self):
        return f'{self.message}'


# Checksum mismatch
class ChecksumMismatchException(Exception):
    # Exception raised for checksum mismatch in packets
    def __init__(self, message="Checksum mismatch"):
        self.message = message
        super().__init__(self.message)
    pass

    def __str__(self):
        return f'{self.message}'
