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
    def __init__(self):
        super().__init__(daemon=False)
        self.loaded_tasks = []
        self.client_udp = None
        self.client_tcp = None
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
                # TODO intialize a thread for each task
                for task in self.loaded_tasks:
                    metrics, alerts = self.run_task(task)

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

    def run_task(self, task):
        metrics = dict()
        alerts  = dict()

        # Device metrics
        device_metrics = task["device_metrics"]
        if device_metrics:
            if device_metrics["cpu_usage"]:
                metrics["cpu_usage"] = device.get_cpu_usage()
            if device_metrics["ram_usage"]:
                metrics["ram_usage"] = device.get_ram_usage()
            if device_metrics["interface_stats"]:
                interfaces = device_metrics["interface_stats"]
                metrics["interface_stats"] = device.get_network_usage(interfaces)

        # Link metrics
        # - bandwith    (iperf TCP)
        # - jitter      (iperf UDP, ping)
        # - packet loss (iperf UDP, ping)
        # - latency     (ping)

        # TODO Get all the link metrics that use iperf
        iperf_metrics = [
            key
            for key, value in task["link_metrics"].items()
            if value["tool"] == "iperf"
        ]

        # Get all the link metrics that use ping
        ping_metrics = [
            key
            for key, value in task["link_metrics"].items()
            if value["tool"] == "ping"
        ]

        # Get the ping parameters
        ping_params = task["tools_params"]["ping"]
        destination = ping_params.get("destination", "localhost")
        packet_count = ping_params.get("packet_count", 10)

        # Execute the ping command
        ping_results = link.ping(destination, ping_metrics, packet_count)

        # Parse the ping results
        if ping_results:
            for option, value in ping_results.items():
                metrics[option] = value

        # Alert conditions
        alert_conditions = task["alertflow_conditions"]
        if alert_conditions:
            # CPU usage
            if alert_conditions["cpu_usage"]:
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
            if alert_conditions["ram_usage"]:
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
            if alert_conditions["interface_stats"]:
                # Calculate the interface stats if it's not in the metrics
                # only for interfaces defined in the alert conditions
                if "interface_stats" not in metrics:
                    interfaces = alert_conditions["interface_stats"]["interfaces"]
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

            # TODO Packet loss

            # TODO Jitter

        return metrics, alerts
