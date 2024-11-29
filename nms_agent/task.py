from .task_tools import (link, device)
from protocol.alert_flow import AlertFlow

import time


# The agent Task class is responsible for:
# - Running the tasks for the agent based on the tasks received from the server.
# - Parsing the results of the tasks and sending them back to the server.
# - Sending alerts if the alert conditions are met.
class Task:
    def __init__(self):
        self.loaded_tasks = []
        self.tasks_results = dict()

    # Adds a task to the list of loaded tasks
    # If the task id is already in the list, the task is replaced
    # Otherwise, the task is appended to the list
    def add_task(self, task):
        for i, t in enumerate(self.loaded_tasks):
            if t["task_id"] == task["task_id"]:
                self.loaded_tasks.pop(i)
                break

        self.loaded_tasks.append(task)

    def run_tasks(self):
        for task in self.loaded_tasks:
            # Sleep for the task interval
            frequency = task["frequency"]
            time.sleep(frequency)
            # Initialize the result
            self.tasks_results[task["task_id"]] = dict()

            # Device metrics
            device_metrics = task["device_metrics"]
            if device_metrics:
                metrics = {}
                if device_metrics["cpu_usage"]:
                    metrics["cpu_usage"] = device.get_cpu_usage()
                if device_metrics["ram_usage"]:
                    metrics["ram_usage"] = device.get_ram_usage()
                if device_metrics["interface_stats"]:
                    interfaces = device_metrics["interface_stats"]
                    metrics["interface_stats"] = device.get_network_usage(interfaces)

                self.tasks_results[task["task_id"]]["device_metrics"] = metrics

            # TODO Link metrics

            # Alert conditions
            # NOTE if the conditions are not calculated before,
            # the alerts will never be triggered
            alert_conditions = task["alertflow_conditions"]
            if alert_conditions:
                alerts = []
                if alert_conditions["cpu_usage"]:
                    cpu_usage = metrics["cpu_usage"]
                    print(f"CPU usage: {cpu_usage}")
                    print(f"Alert condition: {alert_conditions['cpu_usage']}")
                    if cpu_usage and cpu_usage >= alert_conditions["cpu_usage"]:
                        alerts.append(AlertFlow.CPU_USAGE)

                if alert_conditions["ram_usage"]:
                    ram_usage = metrics["ram_usage"]
                    if ram_usage and ram_usage >= alert_conditions["ram_usage"]:
                        alerts.append(AlertFlow.RAM_USAGE)

                if alert_conditions["interface_stats"]:
                    for interface, stats in metrics["interface_stats"].items():
                        if stats >= alert_conditions["interface_stats"]:
                            alerts.append(AlertFlow.INTERFACE_STATS)

                # TODO Packet loss

                # TODO Jitter

                self.tasks_results[task["task_id"]]["alerts"] = alerts

    # def send_result(self, task_id, result):
    #     # TODO Send the result back to the server
    #     pass
