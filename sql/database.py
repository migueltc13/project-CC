#!/usr/bin/env python3

from os import path
from contextlib import contextmanager
import mysql.connector as connector
from mysql.connector import errors
import threading


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
    def insert_metric(metrics):
        hostname = None
        cpu_usage = metrics.get('cpu_usage')
        ram_usage = metrics.get('ram_usage')
        interface_stats = metrics.get('interface_stats')
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
                with open(path.join(db_dir, "queries/insert_metric.sql"), "r") as sql_file:
                    cursor.execute(
                        sql_file.read(),
                        (cpu_usage, ram_usage, interface_stats, bandwidth, jitter, packet_loss, latency, hostname, message)
                    )

            except (FileNotFoundError, errors.Error) as e:
                print(f"Error inserting metric log: {e}")

    # Select log entries with an optional limit
    @staticmethod
    def select(limit=-1):
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
    def select_alert(limit=-1):
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
    def select_metric(limit=-1):
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

        print(f"{nr} | {log_type} | {timestamp} | {hostname} | {alert_type} | {metric_id} | {message}")

    # Print log entries
    @staticmethod
    def print_logs(logs):
        print(" Nr  | Type   | Timestamp           | Host     | Alert Type  | Metric Id | Message               ")
        print("-----|--------|---------------------|----------|-------------|-----------|-----------------------")
        for log in logs:
            operation.print_log(log)

        print("Displayed %d log entries" % len(logs))


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
