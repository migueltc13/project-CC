# AlertFlow app protocol for communication between the server and the clients.

import struct
import constants as C

from .exceptions.invalid_version import InvalidVersionException
from .exceptions.invalid_header  import InvalidHeaderException

# AlertFlow header:
# - AlertFlow version   ( 1 byte)
# - Identifier          (32 bytes)
# - Data                ( N bytes) [Default: UTF-8] [JSON]

# Alert Types:
# 0 - CPU usage
# 1 - RAM usage
# 2 - Interface stats
# 3 - Packet loss
# 4 - Jitter


###
# Constants
###

# Constants for header field sizes
SIZE_NMS_VERSION = 1
SIZE_IDENTIFIER  = 32

# Header total size
HEADER_SIZE = SIZE_NMS_VERSION + SIZE_IDENTIFIER

# Struct format for the header fields
# !    network (big-endian) byte order
# B    unsigned char       (1 byte)
# H    unsigned short      (2 bytes)
# I    unsigned int        (4 bytes)
# Xs   string with X chars (X bytes)
STRUCT_FORMAT = '!B 32s'


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

    @staticmethod
    def parse_packet(self, packet):
        # Extract the header and data
        header = packet[:HEADER_SIZE]
        data = packet[HEADER_SIZE:]

        # Unpack header
        try:
            # Check if the NMS AlertFlow version is correct before unpacking the rest of the header
            version = header[:SIZE_NMS_VERSION]
            version = int.from_bytes(version, byteorder='big')
            if version != C.ALERT_FLOW_VERSION:
                raise InvalidVersionException(version, C.ALERT_FLOW_VERSION)

            version, identifier = struct.unpack(STRUCT_FORMAT, header)
        except Exception:
            raise InvalidHeaderException()

        # Remove padding from the identifier
        identifier = identifier.rstrip(b'\x00')

        return {
            "version": version,
            "identifier": identifier.decode(C.ENCODING),
            "data": data.decode(C.ENCODING)
        }

    @staticmethod
    def build_packet(self, identifier, data):

        # Build header
        header = struct.pack(
            STRUCT_FORMAT,
            C.ALERT_FLOW_VERSION,
            identifier.encode(C.ENCODING)
        )

        return header + data.encode(C.ENCODING)
