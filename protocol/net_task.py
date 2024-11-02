# Utils module for the server and client

# TODO use TLV format for messages

# NetTask Header:
# - Size of packet (4 bytes)
# - Sequence number (4 bytes)
# - Retransmission flag (1 byte)
# - Message type (1 byte) (0 - Request X, 1 - ACK, etc.)
# - Identifier (1 byte)
# - Message (N bytes)

# Message parser
def parser(message):
    size = int(message[:4])
    seq = int(message[4:8])
    retransmission = int(message[8])
    msg_type = int(message[9])
    return message[10:size + 10], seq, retransmission, msg_type


# Message builder
def build_message(message, seq, retransmission, msg_type):
    size = len(message)
    return str(size).zfill(4) + str(seq).zfill(4) + str(retransmission) + str(msg_type) + message

# TODO flow control

# TODO format of new task
