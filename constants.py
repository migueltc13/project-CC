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
INITIAL_WINDOW_SIZE = 32  # packets

# Time to sleep before retransmitting packets
RETRANSMIT_SLEEP_TIME = 5  # seconds

# Time to sleep before probing the window size
WINDOW_PROBE_SLEEP_TIME = 5  # seconds

# Timout for end of connection acknowledgments
EOC_ACK_TIMEOUT = RETRANSMIT_SLEEP_TIME * 3  # seconds

# Decimal precision for floating point numbers
DECIMAL_PRECISION = 4
