import iperf3
import ping3


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


# ping: returns the latency in ms
def ping(host):
    return ping3.ping(host)
