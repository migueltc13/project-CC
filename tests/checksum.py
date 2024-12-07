#!/usr/bin/env python3
# Checksum test
# Two packets are builded with different sequence numbers,
# then the checksums are compared,
# the test fails if the checksums are the same

import sys
import os
import json

# Join the parent directory to the sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol.net_task import NetTask


def main():

    print("Packets as binary data\n")

    # Build the packets with different sequence numbers
    _, packet1 = NetTask.build_packet(NetTask, "Example data", 1, {"ack": 1},
                                      NetTask.UNDEFINED, "agent47", 32)
    _, packet2 = NetTask.build_packet(NetTask, "Example data", 0, {"ack": 1},
                                      NetTask.UNDEFINED, "agent47", 32)

    packet1 = packet1[0]
    packet2 = packet2[0]

    print(f"Packet 1: {packet1}")
    print(f"Packet 2: {packet2}")

    # Parse the packets to get the checksums
    packet1 = NetTask.parse_packet(NetTask, packet1)
    packet2 = NetTask.parse_packet(NetTask, packet2)

    checksum1 = packet1["checksum"]
    checksum2 = packet2["checksum"]

    print("\nParsed packets as JSON\n")

    print(f"Packet 1: {json.dumps(packet1, indent=2)}")
    print(f"Packet 2: {json.dumps(packet2, indent=2)}")

    print("\nChecksums\n")

    print(f"Checksum 1: {checksum1}")
    print(f"Checksum 2: {checksum2}")

    print()

    if checksum1 != checksum2:
        print("Success checksums are different")
    else:
        print("Failure checksums are the same")


if __name__ == '__main__':
    main()
