import psutil
import time

import constants as C


# Get the current CPU usage (%)
def get_cpu_usage():
    cpu_usage = psutil.cpu_percent(interval=1)
    return round(cpu_usage / 100, C.DECIMAL_PRECISION)


# Get the current RAM usage (%)
def get_ram_usage():
    ram_usage = psutil.virtual_memory().percent
    return round(ram_usage / 100, C.DECIMAL_PRECISION)


# Get the packets per second per network interface
def get_network_usage(interfaces):

    initial_stats = {
        interface: stats.packets_sent + stats.packets_recv
        for interface, stats in psutil.net_io_counters(pernic=True).items()
        if interface in interfaces
    }

    time.sleep(1)

    end_stats = {
        interface: stats.packets_sent + stats.packets_recv
        for interface, stats in psutil.net_io_counters(pernic=True).items()
        if interface in interfaces
    }

    network_usage = dict()
    for interface, stats in end_stats.items():
        end = end_stats[interface]
        start = initial_stats[interface]
        network_usage[interface] = end - start

    return network_usage
