import iperf3
import subprocess

import constants as C


# Iperf client udp
# NOTE:
# The bandwidth is in bits per second
# The duration is in seconds
# Options:
# - jitter
# - packet_loss
def iperf3_client_udp(options, bind_address, server, port, duration, bandwidth):
    client = iperf3.Client()
    client.server_hostname = server
    client.bind_address = bind_address
    client.port = port
    client.duration = duration
    client.bandwidth = bandwidth
    client.protocol = "udp"
    client.blksize = 32768  # MSS (Maximum Segment Size)
    iperf_result = client.run()

    # If the test failed, return None
    if iperf_result.error:
        return None

    result = dict()
    for option in options:
        match option:
            case "jitter":
                result[option] = round(iperf_result.jitter_ms,    C.DECIMAL_PRECISION)
            case "packet_loss":
                result[option] = round(iperf_result.lost_percent, C.DECIMAL_PRECISION)

    # if the result is empty, return None
    return result if result else None


# Iperf client tcp (bandwidth)
def iperf3_client_tcp(server, bind_address, port, duration):
    client = iperf3.Client()
    client.server_hostname = server
    # client.bind_address = bind_address
    client.port = port
    client.duration = duration
    client.protocol = "tcp"
    iperf_result = client.run()

    # If the test failed, return None
    if iperf_result.error:
        return None

    return round(iperf_result.sent_Mbps, C.DECIMAL_PRECISION) if iperf_result.sent_Mbps else None


def iperf3_server(bind_address, port, verbose, timeout=30):

    command = f"iperf3 -s -B {bind_address} -p {port}"
    try:
        process = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        try:
            if timeout is None or timeout < 0:
                timeout = 30

            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if verbose:
                print("iperf3 server timed out. Terminating...")
            process.terminate()
            process.wait()  # Ensure the process exits
    except Exception as e:
        print(f"Error running iperf3 server: {e}")


# Usage:
# ping("google.com", ["jitter", "packet_loss", "latency"], packet_count=5)
# Options:
# - jitter
# - packet_loss
# - latency
def ping(host, options, packet_count=10):
    command = f"ping -c {packet_count} {host} | tail -n 2"
    process = subprocess.run(command, shell=True, capture_output=True, text=True)
    if process.returncode != 0:
        return None

    output = process.stdout.strip()

    # Strip output into two lines
    lines = output.split("\n")
    packet_line = lines[0]
    rtt_line = lines[1]

    # Get the values from the output
    rtt_values = rtt_line.split("=")[1].strip().split(" ")[0].split("/")
    packet_loss = packet_line.split(",")[2].strip().split(" ")[0].split("%")[0]

    results = dict()
    # For each option, add the result to the dictionary
    for option in options:
        match option:
            case "jitter":
                results[option] = round(float(rtt_values[3]), C.DECIMAL_PRECISION)
            case "packet_loss":
                results[option] = round(float(packet_loss),   C.DECIMAL_PRECISION)
            case "latency":
                results[option] = round(float(rtt_values[1]), C.DECIMAL_PRECISION)

    # If the result is empty, return None
    return results if results else None
