# NetTask app protocol for communication between the server and the agents.

import struct
import constants as C

from .exceptions.invalid_version   import InvalidVersionException
from .exceptions.invalid_header    import InvalidHeaderException
from .exceptions.checksum_mismatch import ChecksumMismatchException

# NetTask Header:
# - NetTask version ( 1 byte)
# - Sequence number ( 2 bytes)
# - Flags and Type  ( 1 byte)
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

# If the flag ACK is set, the payload data will be empty, and the sequence number
# represents the sequence number of the packet being acknowledged.


###
# Constants
###

# Constants for header field sizes
SIZE_NMS_VERSION = 1
SIZE_SEQ_NUMBER  = 2
SIZE_FLAGS_TYPE  = 1
SIZE_WINDOW_SIZE = 2
SIZE_CHECKSUM    = 2
SIZE_MSG_ID      = 2
SIZE_IDENTIFIER  = 32

# Header total size
HEADER_SIZE = (SIZE_NMS_VERSION + SIZE_SEQ_NUMBER + SIZE_FLAGS_TYPE +
               SIZE_WINDOW_SIZE + SIZE_CHECKSUM + SIZE_MSG_ID + SIZE_IDENTIFIER)

# Struct format for the header fields
# !    network (big-endian) byte order
# B    unsigned char       (1 byte)
# H    unsigned short      (2 bytes)
# I    unsigned int        (4 bytes)
# Xs   string with X chars (X bytes)
STRUCT_FORMAT = '!B H B H H H 32s'


###
# NetTask Main Class
###

class NetTask:
    # Constants for message types
    UNDEFINED        = 0
    FIRST_CONNECTION = 1
    SEND_TASK        = 2
    SEND_METRICS     = 3
    EOC              = 4

    # Calculate the checksum of a packet, padding the checksum field with 0
    @staticmethod
    def calculate_checksum(packet):
        checksum_start = (SIZE_NMS_VERSION + SIZE_SEQ_NUMBER + SIZE_FLAGS_TYPE +
                          SIZE_WINDOW_SIZE)
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
            version = header[:SIZE_NMS_VERSION]
            version = int.from_bytes(version, byteorder='big')
            if version != C.NET_TASK_VERSION:
                raise InvalidVersionException(version, C.NET_TASK_VERSION)

            version, seq_number, flags_type, window_size, \
                checksum, msg_id, identifier = struct.unpack(STRUCT_FORMAT, header)

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
            "window_size": window_size,
            "checksum": checksum,
            "msg_id": msg_id,
            "identifier": identifier.decode(C.ENCODING),
            "data": data.decode(C.ENCODING)
        }

    @staticmethod
    def build_header(self, seq_number, flags_type, window_size,
                     msg_id, identifier, data):

        # Initial header with checksum set to 0
        header = struct.pack(
            STRUCT_FORMAT,
            C.NET_TASK_VERSION,
            seq_number,
            flags_type,
            window_size,
            0,  # Placeholder for checksum
            msg_id,
            identifier.encode(C.ENCODING)
        )

        # Concatenate header and data to calculate the checksum
        if isinstance(data, str):
            data = data.encode(C.ENCODING)
        packet = header + data
        checksum = self.calculate_checksum(packet)

        # Repack the header with the actual checksum
        header = struct.pack(
            STRUCT_FORMAT,
            C.NET_TASK_VERSION,
            seq_number,
            flags_type,
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

            # Set the "more_fragments" flag
            flags["more_fragments"] = 1 if i < len(data_segments) - 1 else 0

            # Rebuild the flags and type field
            flags_type = (
                (flags.get("ack",            0) << 7) |
                (flags.get("retransmission", 0) << 6) |
                (flags.get("urgent",         0) << 5) |
                (flags.get("window_probe",   0) << 4) |
                (flags.get("more_fragments", 0) << 3) |
                (msg_type & 0b00000111)
            )

            # Build the header
            header = self.build_header(self,
                                       seq_number,
                                       flags_type,
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

    def build_ack_packet(self, packet, identifier, window_size):
        # Set the appropriate flags for the ACK packet combine the remaining
        # flags and type of the packet being acknowledged
        flags_type = (
            (1 << 7) |  # set ACK flag
            (0 << 6) |  # unset retransmission flag
            (packet['flags'].get("urgent", 0) << 5) |
            (0 << 4) |  # unset window probe flag
            (0 << 3) |  # unset more fragments flag
            (packet["msg_type"] & 0b00000111)
        )

        ack_number = packet["seq_number"]

        # Build the header
        header = self.build_header(self,
                                   ack_number,
                                   flags_type,
                                   window_size,
                                   packet["msg_id"],
                                   identifier,
                                   "")

        return header
