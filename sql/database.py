#!/usr/bin/env python3

from os import path
from contextlib import contextmanager
import mysql.connector as connector
from mysql.connector import errors
import threading
import json


# Get the directory with the database files
db_dir = path.join(path.dirname(path.abspath(__file__)), "")


# Establish a connection to the MySQL database
def connect():
    try:
        return connector.connect(
            user="root",
            password="root",
            host="127.0.0.1",
            database="NMS",
            ssl_disabled=True
        )
    except errors.Error as e:
        raise RuntimeError(f"Error connecting to the database: {e}")


# Provides a cursor within a context manager, ensuring cleanup on exit
@contextmanager
def get_cursor():
    connection = connect()
    if connection is None:
        yield None
    else:
        cursor = connection.cursor()
        try:
            yield cursor
            connection.commit()
        except errors.Error as e:
            raise RuntimeError(f"Database operation failed: {e}")
            connection.rollback()
        finally:
            cursor.close()
            connection.close()


# Define the database operations for initializing, inserting, and selecting logs
# as well as printing log entries
class operation:
    # Database operations lock
    db_lock = threading.Lock()

    # Initialize the database tables and populate them with data
    @staticmethod
    def init():
        with operation.db_lock, get_cursor() as cursor:
            if cursor is None:
                raise RuntimeError("Failed to obtain database cursor for initialization")

            try:
                # Create tables "log_type", "alert_type", "metric", and "log"
                with open(path.join(db_dir, "create/log_type.sql"), "r") as log_type_file, \
                     open(path.join(db_dir, "create/alert_type.sql"), "r") as alert_type_file, \
                     open(path.join(db_dir, "create/metric.sql"), "r") as metric_file, \
                     open(path.join(db_dir, "create/log.sql"), "r") as log_file:
                    cursor.execute(log_type_file.read())
                    cursor.execute(alert_type_file.read())
                    cursor.execute(metric_file.read())
                    cursor.execute(log_file.read())

                # Populate tables "log_type" and "alert_type"
                with open(path.join(db_dir, "populate/log_type.sql"), "r") as log_type_populate_file, \
                     open(path.join(db_dir, "populate/alert_type.sql"), "r") as alert_type_populate_file:
                    cursor.execute(log_type_populate_file.read())
                    cursor.execute(alert_type_populate_file.read())

            except (FileNotFoundError, errors.Error) as e:
                raise RuntimeError(f"Error initializing the database: {e}")

    # Insert a log entry into the database
    @staticmethod
    def insert(log_type_id, hostname, message):
        if (
            not isinstance(log_type_id, int) or
            not isinstance(hostname, str) or
            not isinstance(message, str)
        ):
            raise RuntimeError("Invalid input data type(s)")

        with operation.db_lock, get_cursor() as cursor:
            if cursor is None:
                raise RuntimeError("Failed to obtain database cursor for insertion")

            try:
                with open(path.join(db_dir, "queries/insert_log.sql"), "r") as sql_file:
                    cursor.execute(sql_file.read(), (log_type_id, hostname, message))

            except (FileNotFoundError, errors.Error) as e:
                raise RuntimeError(f"Error inserting log: {e}")

    # Insert an alert log entry into the database
    @staticmethod
    def insert_alert(hostname, alert_type_id, message):
        if (
            not isinstance(hostname, str) or
            not isinstance(alert_type_id, int) or
            not isinstance(message, str)
        ):
            raise RuntimeError("Invalid input data type(s)")

        with operation.db_lock, get_cursor() as cursor:
            if cursor is None:
                raise RuntimeError("Failed to obtain database cursor for insertion")

            try:
                with open(path.join(db_dir, "queries/insert_alert.sql"), "r") as sql_file:
                    cursor.execute(sql_file.read(), (hostname, alert_type_id, message))

            except (FileNotFoundError, errors.Error) as e:
                raise RuntimeError(f"Error inserting alert log: {e}")

    # Insert a metric log entry into the database
    @staticmethod
    def insert_metrics(hostname, metrics):
        task_id = metrics.get('task_id')
        cpu_usage = metrics.get('cpu_usage')
        ram_usage = metrics.get('ram_usage')
        interface_stats = metrics.get('interface_stats')
        # convert interface_stats to json string
        interface_stats = json.dumps(interface_stats)
        bandwidth = metrics.get('bandwidth')
        jitter = metrics.get('jitter')
        packet_loss = metrics.get('packet_loss')
        latency = metrics.get('latency')
        message = None

        with operation.db_lock, get_cursor() as cursor:
            if cursor is None:
                print("Failed to obtain database cursor for insertion")
                return

            try:
                with open(path.join(db_dir, "queries/insert_metric/insert_metric.sql"), "r") \
                        as sql_file:
                    cursor.execute(
                        sql_file.read(),
                        (task_id, cpu_usage, ram_usage, interface_stats,
                         bandwidth, jitter, packet_loss, latency)
                    )

                with open(path.join(db_dir, "queries/insert_metric/insert_log.sql"), "r") \
                        as sql_file:
                    cursor.execute(
                        sql_file.read(),
                        (hostname, message)
                    )

            except (FileNotFoundError, errors.Error) as e:
                print(f"Error inserting metric log: {e}")

    # Select log entries with an optional limit
    @staticmethod
    def select_logs(limit=-1):
        if not isinstance(limit, int) or limit < -1:
            raise RuntimeError("Invalid limit value")

        query_limit = "LIMIT %s" % limit if limit > 0 else ""

        with operation.db_lock, get_cursor() as cursor:
            if cursor is None:
                raise RuntimeError("Failed to obtain database cursor for selection")
            try:
                with open(path.join(db_dir, "queries/select_log.sql"), "r") as file:
                    query = file.read().replace("{LIMIT}", query_limit)
                    cursor.execute(query)
                    return cursor.fetchall()
            except (FileNotFoundError, errors.Error) as e:
                raise RuntimeError(f"Error selecting logs: {e}")

    # Select alert log entries with an optional limit
    @staticmethod
    def select_alerts(limit=-1):
        if not isinstance(limit, int) or limit < -1:
            raise RuntimeError("Invalid limit value")

        query_limit = "LIMIT %s" % limit if limit > 0 else ""

        with operation.db_lock, get_cursor() as cursor:
            if cursor is None:
                raise RuntimeError("Failed to obtain database cursor for selection")
            try:
                with open(path.join(db_dir, "queries/select_alert.sql"), "r") as file:
                    query = file.read().replace("{LIMIT}", query_limit)
                    cursor.execute(query)
                    return cursor.fetchall()
            except (FileNotFoundError, errors.Error) as e:
                raise RuntimeError(f"Error selecting logs: {e}")

    # Select metric log entries with an optional limit
    @staticmethod
    def select_metrics(limit=-1):
        if not isinstance(limit, int) or limit < -1:
            raise RuntimeError("Invalid limit value")

        query_limit = "LIMIT %s" % limit if limit > 0 else ""

        with operation.db_lock, get_cursor() as cursor:
            if cursor is None:
                raise RuntimeError("Failed to obtain database cursor for selection")
            try:
                with open(path.join(db_dir, "queries/select_metric.sql"), "r") as file:
                    query = file.read().replace("{LIMIT}", query_limit)
                    cursor.execute(query)
                    return cursor.fetchall()
            except (FileNotFoundError, errors.Error) as e:
                raise RuntimeError(f"Error selecting logs: {e}")

    # Print a log entry
    @staticmethod
    def print_log(log):
        nr, log_type, timestamp, hostname, message, alert_type, metric_id = log

        # Fill attributes with spaces to align the output
        nr = str(nr).rjust(4)
        log_type = log_type.ljust(6)
        hostname = hostname.ljust(8)
        alert_type = "".ljust(10) if alert_type is None else alert_type.ljust(10)
        metric_id = "".ljust(9) if metric_id is None else str(metric_id).ljust(9)

        print(f"{nr} | {log_type} | {timestamp} | {hostname} | {alert_type} | {metric_id} | {message}")

    # Print log entries
    @staticmethod
    def print_logs(logs):
        if len(logs) == 0:
            print("No log entries to display")
            return

        print("-----+--------+---------------------+----------+------------+-----------+---------------------------------------------------")
        print(" Nr  | Type   | Timestamp           | Hostname | Alert Type | Metric ID | Message                                           ")
        print("-----+--------+---------------------+----------+------------+-----------+---------------------------------------------------")
        for log in logs:
            operation.print_log(log)
        print("-----+--------+---------------------+----------+------------+-----------+---------------------------------------------------")

        print("Displayed %d log entries" % len(logs))

    # Print an alert log entry
    @staticmethod
    def print_alert(alert):
        nr, timestamp, hostname, alert_type, message = alert

        # Fill attributes with spaces to align the output
        nr = str(nr).rjust(4)
        hostname = hostname.ljust(8)
        alert_type = alert_type.ljust(10)

        print(f"{nr} | {timestamp} | {hostname} | {alert_type} | {message}")

    # Print alert log entries
    @staticmethod
    def print_alerts(alerts):
        if len(alerts) == 0:
            print("No alert entries to display")
            return

        print("-----+---------------------+----------+------------+--------------------------------------------")
        print(" Nr  | Timestamp           | Hostname | Alert Type | Message                                    ")
        print("-----+---------------------+----------+------------+--------------------------------------------")
        for alert in alerts:
            operation.print_alert(alert)
        print("-----+---------------------+----------+------------+--------------------------------------------")

        print("Displayed %d alert entries" % len(alerts))

    # Print a metric log entry
    @staticmethod
    def print_metric(metric):
        nr, timestamp, hostname, task_id, cpu_usage, ram_usage, \
            bandwidth, jitter, packet_loss, latency, interface_stats = metric

        # Fill attributes with spaces to align the output
        nr              = str(nr).rjust(4)
        hostname        = hostname.ljust(8)
        task_id         = str(task_id).ljust(7)
        cpu_usage       = str(cpu_usage).ljust(9)   if cpu_usage       is not None else "".ljust(9)
        ram_usage       = str(ram_usage).ljust(9)   if ram_usage       is not None else "".ljust(9)
        bandwidth       = str(bandwidth).ljust(9)   if bandwidth       is not None else "".ljust(9)
        jitter          = str(jitter).ljust(8)      if jitter          is not None else "".ljust(8)
        packet_loss     = str(packet_loss).ljust(8) if packet_loss     is not None else "".ljust(8)
        latency         = str(latency).ljust(8)     if latency         is not None else "".ljust(8)
        interface_stats = interface_stats.ljust(15) if interface_stats is not None else "".ljust(15)

        print(f"{nr} | {timestamp} | {hostname} | {task_id} | {cpu_usage} | {ram_usage} | {bandwidth} | {jitter} | {packet_loss} | {latency} | {interface_stats}")

    # Print metric log entries
    @staticmethod
    def print_metrics(metrics):
        if len(metrics) == 0:
            print("No metric entries to display")
            return

        print("-----+---------------------+----------+---------+-----------+-----------+-----------+----------+----------+----------+-----------------")
        print(" Nr  | Timestamp           | Hostname | Task ID | CPU Usage | RAM Usage | Bandwidth | Jitter   | Pkt Loss | Latency  | Interface Stats ")
        print("-----+---------------------+----------+---------+-----------+-----------+-----------+----------+----------+----------+-----------------")
        for metric in metrics:
            operation.print_metric(metric)
        print("-----+---------------------+----------+---------+-----------+-----------+-----------+----------+----------+----------+-----------------")

        print("Displayed %d metric entries" % len(metrics))


class values:
    # Holds the log type constant values
    class log_type:
        STATUS = 1
        ALERT = 2
        METRIC = 3


if __name__ == "__main__":
    try:
        print("Initializing database...")
        operation.init()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
