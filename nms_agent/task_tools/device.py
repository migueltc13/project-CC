import psutil


# Get the current CPU usage (%)
def get_cpu_usage():
    cpu_usage = psutil.cpu_percent(interval=1)
    return cpu_usage / 100


# Get the current RAM usage (%)
def get_ram_usage():
    ram_usage = psutil.virtual_memory().percent
    return ram_usage / 100


# Get the packets per second per network interface
def get_network_usage(interfaces):
    network_usage = dict()
    for interface, stats in psutil.net_io_counters(pernic=True).items():
        if interface in interfaces:
            network_usage[interface] = stats.packets_sent + stats.packets_recv
    return network_usage
