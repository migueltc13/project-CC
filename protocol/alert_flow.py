# AlertFlow app protocol for communication between the server and the clients.

import struct

# AlertFlow header:
# - Packet Size         ( 4 bytes)
# - AlertFlow version   ( 1 byte)
# - More Fragments Flag ( 1 byte)  [Maybe not needed]
# - Fragment Offset     ( 4 bytes) [Maybe not needed]
# - Identifier          (32 bytes)
# - Data                ( N bytes) [Default: UTF-8]

###
# Constants
###

# Constants for header field sizes
SIZE_PACKET_SIZE = 4
SIZE_NMS_VERSION = 1
SIZE_IDENTIFIER  = 32

# Header total size
HEADER_SIZE = (SIZE_PACKET_SIZE + SIZE_NMS_VERSION + SIZE_IDENTIFIER)

# Struct format for the header fields
# !    network (big-endian) byte order
# B    unsigned char       (1 byte)
# H    unsigned short      (2 bytes)
# I    unsigned int        (4 bytes)
# Xs   string with X chars (X bytes)
STRUCT_FORMAT = '!I B 32s'


###
# AlertFlow Main Class
###

class AlertFlow:

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

            packet_size, version, identifier = struct.unpack(STRUCT_FORMAT, header)
        except Exception:
            raise InvalidHeaderException()

        # Remove padding from the identifier
        identifier = identifier.rstrip(b'\x00')

        # TODO Parse data as JSON
        # data = json.load(data)

        return {
            "packet_size": packet_size,
            "version": version,
            "identifier": identifier.decode(self.C.ENCODING),
            "data": data.decode(self.C.ENCODING)
        }

    @staticmethod
    def build_packet(self, data, identifier):
        # Calculate packet size
        packet_size = HEADER_SIZE + len(data)

        # Build header
        header = struct.pack(
            STRUCT_FORMAT,
            packet_size,
            self.C.ALERT_FLOW_VERSION,
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
