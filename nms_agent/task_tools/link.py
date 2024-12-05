import iperf3
import subprocess


# Iperf
def iperf3_client(options, server, port, duration, bandwidth, protocol):
    client = iperf3.Client()
    client.server_hostname = server
    client.port = port
    client.duration = duration
    client.bandwidth = bandwidth
    client.protocol = protocol
    iperf_result = client.run()

    # If the test failed, return None
    if iperf_result.error:
        return None

    result = dict()
    for option in options:
        match option:
            case "bandwidth":
                result[option] = iperf_result.sent_Mbps
            case "jitter":
                result[option] = 10  # TODO
            case "packet_lost":
                result[option] = 20  # TODO
            case "latency":
                result[option] = 30  # TODO

    # if the result is empty, return None
    if not result:
        return None

    return result


def iperf3_server(port):
    server = iperf3.Server()
    server.port = port
    server.run()


# Usage:
# ping("google.com", ["jitter", "packet_lost", "latency"], packet_count=5)
# Options:
# - jitter
# - packet_lost
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
                results[option] = float(rtt_values[3])
            case "packet_loss":
                results[option] = float(packet_loss)
            case "latency":
                results[option] = float(rtt_values[1])

    return results
