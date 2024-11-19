# AlertFlow app protocol for communication between the server and the clients.

import struct

# AlertFlow header:
# - Packet Size         ( 4 bytes)
# - AlertFlow version   ( 1 byte)
# - Alert Type          ( 1 byte)
# - Identifier          (32 bytes)
# - Data                ( N bytes) [Default: UTF-8]

# Alert Types:
# 0 - CPU usage
# 1 - RAM usage
# 2 - Interface stats
# 3 - Packet loss
# 4 - Jitter

# NOTE if the data size is greater than the buffer size (1500 bytes) or the MTU
# of the route, we will need to handle fragmentation, we need to check if that
# is needed for the AlertFlow protocol, if so, we will need to add the following
# fields to the header:

# - More Fragments Flag ( 1 byte)
# - Fragment Offset     ( 4 bytes)

###
# Constants
###

# Constants for header field sizes
SIZE_PACKET_SIZE = 4
SIZE_NMS_VERSION = 1
SIZE_ALERT_TYPE  = 1
SIZE_IDENTIFIER  = 32

# Header total size
HEADER_SIZE = (SIZE_PACKET_SIZE + SIZE_NMS_VERSION +
               SIZE_ALERT_TYPE + SIZE_IDENTIFIER)

# Struct format for the header fields
# !    network (big-endian) byte order
# B    unsigned char       (1 byte)
# H    unsigned short      (2 bytes)
# I    unsigned int        (4 bytes)
# Xs   string with X chars (X bytes)
STRUCT_FORMAT = '!I B B 32s'


###
# AlertFlow Main Class
###

class AlertFlow:
    # Constants for alert types
    CPU_USAGE       = 0
    RAM_USAGE       = 1
    INTERFACE_STATS = 2
    PACKET_LOSS     = 3
    JITTER          = 4

    @staticmethod
    def parse_alert_type(self, alert_type):
        match alert_type:
            case self.CPU_USAGE:
                return "CPU usage"
            case self.RAM_USAGE:
                return "RAM usage"
            case self.INTERFACE_STATS:
                return "Interface stats"
            case self.PACKET_LOSS:
                return "Packet loss"
            case self.JITTER:
                return "Jitter"
            case _:
                return "Unknown alert type"

    def __init__(self, constants):
        self.C = constants

    @staticmethod
    def parse_packet(self, packet):
        # Extract the header and data
        header = packet[:HEADER_SIZE]
        data = packet[HEADER_SIZE:]

        # Unpack header
        try:
            # Check if the NMS AlertFlow version is correct before unpacking the rest of the header
            version = header[SIZE_PACKET_SIZE:SIZE_PACKET_SIZE + SIZE_NMS_VERSION]
            version = int.from_bytes(version, byteorder='big')
            if version != self.C.ALERT_FLOW_VERSION:
                raise InvalidVersionException(version, self.C.ALERT_FLOW_VERSION)

            packet_size, version, alert_type, identifier = struct.unpack(STRUCT_FORMAT, header)
        except Exception:
            raise InvalidHeaderException()

        # Remove padding from the identifier
        identifier = identifier.rstrip(b'\x00')

        return {
            "packet_size": packet_size,
            "version": version,
            "alert_type": alert_type,
            "identifier": identifier.decode(self.C.ENCODING),
            "data": data.decode(self.C.ENCODING)
        }

    @staticmethod
    def build_packet(self, alert_type, identifier, data):
        # Calculate packet size
        packet_size = HEADER_SIZE + len(data)

        # Build header
        header = struct.pack(
            STRUCT_FORMAT,
            packet_size,
            self.C.ALERT_FLOW_VERSION,
            alert_type,
            identifier.encode(self.C.ENCODING)
        )

        return header + data.encode(self.C.ENCODING)


###
# Exceptions TODO merge with NetTask exceptions
###

class InvalidHeaderException(Exception):
    # Exception raised for invalid AlertFlow header
    def __init__(self, message="Invalid header"):
        self.message = message
        super().__init__(self.message)
    pass

    def __str__(self):
        return f'{self.message}'


class InvalidVersionException(Exception):
    # Exception raised for invalid NMS NetTask version
    def __init__(self, received_version, expected_version, message="Invalid NMS AlertFlow version"):
        self.expected_version = expected_version
        self.received_version = received_version
        self.message = f"{message}\n" \
            f"Received version: {received_version}\n" \
            f"Expected version: {expected_version}"
        super().__init__(self.message)
    pass

    def __str__(self):
        return f'{self.message}'
