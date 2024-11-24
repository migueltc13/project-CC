# Server ports
TCP_PORT = 5000  # AlertFlow
UDP_PORT = 6000  # NetTask

# Buffer size is set as the usual MTU size
BUFFER_SIZE = 1500  # bytes

# Data and Identifier Encoding
ENCODING = "utf-8"

# NMS protocols versions
NET_TASK_VERSION   = 1
ALERT_FLOW_VERSION = 1

# SO_NO_CHECK for disabling UDP checksum
SO_NO_CHECK = 11

# Initial window size for flow control,
# as the space available in the server/agent buffer
INITIAL_WINDOW_SIZE = 64

# Time to sleep before retransmitting packets
RETRANSMIT_SLEEP_TIME = 5  # seconds
