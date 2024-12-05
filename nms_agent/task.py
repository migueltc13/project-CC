from .task_tools import (link, device)
from protocol.alert_flow import AlertFlow

import threading
import time
import json


# The agent Task class is responsible for:
# - Running the tasks for the agent based on the tasks received from the server.
# - Parsing the results of the tasks and sending them back to the server.
# - Sending alerts if the alert conditions are met.
class Task(threading.Thread):
    def __init__(self, verbose=False):
        super().__init__(daemon=False)
        self.loaded_tasks = []
        self.client_udp = None
        self.client_tcp = None
        self.verbose = verbose
        self.shutdown_flag = threading.Event()

    def set_client_udp(self, client_udp):
        self.client_udp = client_udp

    def set_client_tcp(self, client_tcp):
        self.client_tcp = client_tcp

    def shutdown(self):
        self.shutdown_flag.set()

    # Adds a task to the list of loaded tasks
    # If the task id is already in the list, the task is replaced
    # Otherwise, the task is appended to the list
    def add_task(self, task):
        for i, t in enumerate(self.loaded_tasks):
            if t["task_id"] == task["task_id"]:
                self.loaded_tasks.pop(i)
                break

        self.loaded_tasks.append(task)

    def run(self):
        while self.shutdown_flag.is_set() is False:
            # Sleep for one second when no tasks are loaded
            # This way we save CPU cycles
            if len(self.loaded_tasks) == 0:
                time.sleep(1)
                continue
            else:
                task_threads = []
                for task in self.loaded_tasks:
                    # Create a thread for each task
                    task_thread = threading.Thread(target=self.run_task,
                                                   args=(task,))
                    task_threads.append(task_thread)
                    task_thread.start()

                # Wait for all the task threads to finish
                for task_thread in task_threads:
                    task_thread.join()

    def run_task(self, task):
        metrics = dict()
        alerts  = dict()

        # Device metrics
        device_metrics = task.get("device_metrics", None)
        if device_metrics:
            if device_metrics.get("cpu_usage", False):
                metrics["cpu_usage"] = device.get_cpu_usage()
            if device_metrics.get("ram_usage", False):
                metrics["ram_usage"] = device.get_ram_usage()
            if len(device_metrics.get("interface_stats", [])) > 0:
                interfaces = device_metrics["interface_stats"]
                metrics["interface_stats"] = device.get_network_usage(interfaces)

        ###
        # Link metrics
        # - bandwith    (iperf TCP)
        # - jitter      (iperf UDP, ping)
        # - packet loss (iperf UDP, ping)
        # - latency     (ping)
        ###

        tools_params = task.get("tools_params")

        ###
        # Iperf Metrics
        ###

        # Parse the iperf parameters based on the mode (client or server)
        iperf_params = tools_params.get("iperf", {})
        is_client = iperf_params.get("is_client", False)
        if is_client:
            server = iperf_params.get("server", "0.0.0.0")
            bind_address = iperf_params.get("bind_address", "0.0.0.0")
            port = iperf_params.get("port", 10000)
            duration = iperf_params.get("duration", 10)
            bandwidth_bps = iperf_params.get("bandwidth_bps", 1_000_000)
        else:
            bind_address = iperf_params.get("bind_address", "0.0.0.0")
            port = iperf_params.get("port", 10000)
            iperf_server_timeout = iperf_params.get("server_timeout")

        # Get the bandwidth if iperf is the tool (TCP)
        try:
            if task["link_metrics"]["bandwidth"]["tool"] == "iperf":
                # Client mode (TCP)
                if is_client:
                    if self.verbose:
                        print("Starting iperf TCP client")
                    bandwidth = link.iperf3_client_tcp(
                        server, bind_address, port, duration
                    )
                    if bandwidth:
                        metrics["bandwidth"] = bandwidth
                # Server mode
                else:
                    if self.verbose:
                        print("Starting iperf TCP server")
                    link.iperf3_server(bind_address, port,
                                       verbose=self.verbose, timeout=iperf_server_timeout)
        except KeyError:
            pass

        # Get all the link metrics that use UDP iperf (jitter and packet loss)
        iperf_metrics_udp = [
            key
            for key, value in task["link_metrics"].items()
            if value["tool"] == "iperf" and key != "bandwidth"
        ]

        # Client mode (UDP)
        if is_client:
            if self.verbose:
                print("Starting iperf UDP client")
            # Execute the iperf command
            iperf_results = None
            if iperf_metrics_udp:
                iperf_results = link.iperf3_client_udp(
                    iperf_metrics_udp, bind_address, server,
                    port, duration, bandwidth_bps
                )

            # Parse the iperf results
            if iperf_results:
                for option, value in iperf_results.items():
                    metrics[option] = value
        # Server mode
        else:
            if self.verbose:
                print("Starting iperf UDP server")
            link.iperf3_server(bind_address, port,
                               verbose=self.verbose, timeout=iperf_server_timeout)

        ###
        # Ping Metrics
        ###

        # Get all the link metrics that use ping
        ping_metrics = [
            key
            for key, value in task["link_metrics"].items()
            if value["tool"] == "ping"
        ]

        # Get the ping parameters
        ping_params = tools_params.get("ping", {})
        destination = ping_params.get("destination", "localhost")
        packet_count = ping_params.get("packet_count", 10)

        # Execute the ping command
        ping_results = None
        if ping_metrics:
            ping_results = link.ping(destination, ping_metrics, packet_count)

        # Parse the ping results
        if ping_results:
            for option, value in ping_results.items():
                metrics[option] = value

        ###
        # Alert conditions
        ###

        alert_conditions = task.get("alertflow_conditions")
        if alert_conditions:
            # CPU usage
            if alert_conditions.get("cpu_usage", False):
                # Calculate the CPU usage if it's not in the metrics
                if "cpu_usage" not in metrics:
                    cpu_usage = device.get_cpu_usage()
                else:
                    cpu_usage = metrics["cpu_usage"]

                # Determine if the CPU usage is above the threshold
                if cpu_usage and cpu_usage >= alert_conditions["cpu_usage"]:
                    alerts[AlertFlow.CPU_USAGE] = {
                        "cpu_usage": cpu_usage,
                        "alert_condition": alert_conditions["cpu_usage"]
                    }

            # RAM usage
            if alert_conditions.get("ram_usage", False):
                # Calculate the RAM usage if it's not in the metrics
                if "ram_usage" not in metrics:
                    ram_usage = device.get_ram_usage()
                else:
                    ram_usage = metrics["ram_usage"]

                # Determine if the RAM usage is above the threshold
                if ram_usage and ram_usage >= alert_conditions["ram_usage"]:
                    alerts[AlertFlow.RAM_USAGE] = {
                        "ram_usage": ram_usage,
                        "alert_condition": alert_conditions["ram_usage"]
                    }

            # Interface stats
            if alert_conditions.get("interface_stats"):
                # Calculate the interface stats if it's not in the metrics
                # only for interfaces defined in the alert conditions
                if "interface_stats" not in metrics:
                    interfaces = alert_conditions["interface_stats"].get("interfaces", [])
                    interface_stats = device.get_network_usage(interfaces)
                else:
                    interface_stats = metrics["interface_stats"]

                # Initialize the alerts for the interface stats
                alerts[AlertFlow.INTERFACE_STATS] = []

                # Determine if the interface stats are above the threshold for each interface
                for interface, stats in interface_stats.items():
                    if stats >= alert_conditions["interface_stats"]["threshold"]:
                        alerts[AlertFlow.INTERFACE_STATS].append({
                            "interface": interface,
                            "interface_stats": stats,
                            "alert_condition": alert_conditions["interface_stats"]["threshold"]
                        })

                # if the alerts list is empty, remove the key from the alerts dictionary
                if len(alerts[AlertFlow.INTERFACE_STATS]) == 0:
                    alerts.pop(AlertFlow.INTERFACE_STATS)

            # NOTE if the packet loss or the jitter is not measured in the metrics
            # the corresponding alert will never be triggered

            # TODO Packet loss

            # TODO Jitter

        # Send the task metrics and alerts to the server
        if metrics:
            # set the task id for the metrics
            metrics["task_id"] = task["task_id"]
            self.client_udp.send_metric(json.dumps(metrics))

        if alerts:
            self.client_tcp.send_alert(json.dumps(alerts))

        # Sleep for the task interval
        frequency = task["frequency"]
        time.sleep(frequency)

        return metrics, alerts
