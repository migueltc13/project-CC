#!/usr/bin/env python3
# Example of graphing the data from the database for a specific agent task
# Usage: ./analysis.py <task_id> <metrics>
# Example: ./analysis.py 1 latency jitter cpu_usage ram_usage

import sys
import os
from mysql.connector import errors
import matplotlib.pyplot as plt

# Join the parent directory to the sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql import database as db


def main():
    # Define the labels for each possible metric
    labels = {
        "latency": "Latency (ms)",
        "jitter": "Jitter (ms)",
        "packet_loss": "Packet Loss (%)",
        "bandwidth": "Bandwidth (Mbps)",
        "cpu_usage": "CPU Usage (%)",
        "ram_usage": "RAM Usage (%)"
    }

    # Parse the command line arguments
    if len(sys.argv) < 3:
        print("Usage: python3 analysis.py <task_id> <metrics>")
        sys.exit(1)

    task_id = sys.argv[1]

    for arg in sys.argv[2:]:
        metric = arg

        if metric not in labels.keys():
            print(f"Error: metric {metric} is not supported")
            print(f"Supported metrics: {labels.keys()}")
            sys.exit(1)

        with db.get_cursor() as cursor:
            if cursor is None:
                raise RuntimeError("Failed to obtain database cursor for initialization")

            try:
                print(f"Fetching {metric} data for task {task_id}")
                query = """
SELECT M.%s, L.timestamp
FROM metric AS M
LEFT JOIN log AS L ON L.metric_id = M.id
WHERE M.task_id = %s
""" % (metric, task_id)
                print(f"Executing query: {query}")
                cursor.execute(query)
                data = cursor.fetchall()
                if not data:
                    print("No data found for the specified task")
                    sys.exit(1)
            except errors.Error as e:
                print(f"Error: {e}")
                sys.exit(1)

        # Extract the data from the list of tuples
        metric_data = [x[0] if x[0] is not None else 0 for x in data]
        time_data   = [x[1].strftime("%d/%m/%Y %H:%M:%S") for x in data]  # Format: D/M/Y H:m:S
        print(f"Extracted data: {metric_data}")

        # Plot the data
        plt.xlabel("D/M/Y H:m:S")
        plt.ylabel(labels[metric])
        plt.title(f"Measurement of {metric} for task {task_id}")
        plt.plot(time_data, metric_data)
        plt.xticks(rotation=11.75)  # Twist the x-axis labels for better readability
        plt.ylim(bottom=0)  # Start the y-axis from 0

        plt.show()


if __name__ == "__main__":
    main()
