# NetTask app protocol for communication between the server and the agents.

import struct

# NetTask Header:
# - Packet Size     ( 4 bytes)
# - NetTask version ( 1 byte)
# - Sequence number ( 2 bytes)
# - Flags and Type  ( 1 byte)
# - Fragment Offset ( 4 bytes)
# - Window size     ( 2 bytes)
# - Checksum        ( 2 bytes)
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
SIZE_IDENTIFIER  = 32

# Header total size
HEADER_SIZE = (SIZE_PACKET_SIZE + SIZE_NMS_VERSION + SIZE_SEQ_NUMBER +
               SIZE_FLAGS_TYPE + SIZE_FRAGMENT + SIZE_WINDOW_SIZE +
               SIZE_CHECKSUM + SIZE_IDENTIFIER)

# Struct format for the header fields
# !    network (big-endian) byte order
# B    unsigned char       (1 byte)
# H    unsigned short      (2 bytes)
# I    unsigned int        (4 bytes)
# Xs   string with X chars (X bytes)
STRUCT_FORMAT = '!I B H B I H H 32s'


###
# NetTask Main Class
###

class NetTask:
    # Constants for message types
    FIRST_CONNECTION = 1
    SEND_TASK        = 2
    SEND_METRICS     = 3
    EOC              = 4

    def __init__(self, constants):
        self.C = constants

    # Exclude the checksum field from the header and calculate the checksum
    # TODO make checksum of the total packet as this method is used
    # when checksum field is padded with 0
    @staticmethod
    def calculate_checksum(packet):
        # Extract the header without the checksum field plus the data
        checksum_start = (SIZE_PACKET_SIZE + SIZE_NMS_VERSION + SIZE_SEQ_NUMBER +
                          SIZE_FLAGS_TYPE + SIZE_FRAGMENT + SIZE_WINDOW_SIZE)
        checksum_end = checksum_start + SIZE_CHECKSUM
        data = packet[:checksum_start] + packet[checksum_end:]

        # Calculate a 16-bit checksum of the data
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
            if version != self.C.NET_TASK_VERSION:
                raise InvalidVersionException(version, self.C.NET_TASK_VERSION)

            packet_size, version, seq_number, flags_type, fragment_offset, \
                window_size, checksum, identifier = struct.unpack(STRUCT_FORMAT, header)

        except Exception:
            raise InvalidHeaderException()

        # Checksum validation
        if self.calculate_checksum(packet) != checksum:
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

        if ack_flag:
            # Convert data to int (sequence number)
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
                "identifier": identifier.decode(self.C.ENCODING),
                "ack_number": int.from_bytes(data, byteorder='big')
            }

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
            "identifier": identifier.decode(self.C.ENCODING),
            "data": data.decode(self.C.ENCODING)
        }

    @staticmethod
    def build_packet(self, data, seq_number, flags, msg_type, identifier, window_size):
        # Calculate packet size
        packet_size = HEADER_SIZE + len(data)

        # Set flags and type field
        flags_type = (
            (flags.get("ack",            0) << 7) |
            (flags.get("retransmission", 0) << 6) |
            (flags.get("urgent",         0) << 5) |
            (flags.get("window_probe",   0) << 4) |
            (flags.get("more_fragments", 0) << 3) |
            (msg_type & 0b00000111)
        )

        # TODO How to define the sequence number?
        # TODO Check if fragmentation is needed (set more fragments flag and fragment offset)
        fragment_offset = 0

        # Initial header with checksum set to 0
        header = struct.pack(
            STRUCT_FORMAT,
            packet_size,
            self.C.NET_TASK_VERSION,
            seq_number,
            flags_type,
            fragment_offset,
            window_size,
            0,  # Placeholder/padding for checksum
            identifier.encode(self.C.ENCODING)
        )

        # Concatenate header and data to calculate the checksum
        packet = header + data.encode(self.C.ENCODING)
        checksum = self.calculate_checksum(packet)

        # Repack the header with the actual checksum
        header = struct.pack(
            STRUCT_FORMAT,
            packet_size,
            self.C.NET_TASK_VERSION,
            seq_number,
            flags_type,
            fragment_offset,
            window_size,
            checksum,
            identifier.encode(self.C.ENCODING)
        )

        # Return the packet with the checksum included in the header
        return header + data.encode(self.C.ENCODING)

    def build_ack_packet(self, packet, seq_number, identifier, window_size):
        # Calculate packet size
        packet_size = HEADER_SIZE + SIZE_SEQ_NUMBER

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

        # Initial header with checksum set to 0
        header = struct.pack(
            STRUCT_FORMAT,
            packet_size,
            self.C.NET_TASK_VERSION,
            seq_number,
            flags_type,
            0,  # Fragment offset
            window_size,
            0,  # Placeholder/padding for checksum
            identifier.encode(self.C.ENCODING)
        )

        # Concatenate header and data to calculate the checksum
        ack_number = packet["seq_number"].to_bytes(2, byteorder='big')
        ack_packet = header + ack_number
        checksum = self.calculate_checksum(ack_packet)

        # Repack the header with the actual checksum
        header = struct.pack(
            STRUCT_FORMAT,
            packet_size,
            self.C.NET_TASK_VERSION,
            seq_number,
            flags_type,
            0,  # Fragment offset
            window_size,
            checksum,
            identifier.encode(self.C.ENCODING)
        )

        # Return the ack packet with the checksum included in the header
        return header + packet["seq_number"].to_bytes(2, byteorder='big')

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
