#!/usr/bin/env python3

from os import path
from contextlib import contextmanager
import mysql.connector as connector
from mysql.connector import errors

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
    # Initialize the database tables and populate "log_type" table
    @staticmethod
    def init():
        with get_cursor() as cursor:
            if cursor is None:
                raise RuntimeError("Failed to obtain database cursor for initialization")

            try:
                # Create tables "log_type" and "log"
                with open(path.join(db_dir, "create/log_type.sql"), "r") as f:
                    cursor.execute(f.read())

                with open(path.join(db_dir, "create/log.sql"), "r") as f:
                    cursor.execute(f.read())

                # Populate table "log_type"
                with open(path.join(db_dir, "populate/log_type.sql"), "r") as f:
                    cursor.execute(f.read())

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

        with get_cursor() as cursor:
            if cursor is None:
                raise RuntimeError("Failed to obtain database cursor for insertion")

            try:
                with open(path.join(db_dir, "queries/insert.sql"), "r") as f:
                    cursor.execute(f.read(), (log_type_id, hostname, message))

            except (FileNotFoundError, errors.Error) as e:
                raise RuntimeError(f"Error inserting log: {e}")

    # Select log entries with an optional limit
    @staticmethod
    def select(limit=-1):
        if not isinstance(limit, int) or limit < -1:
            raise RuntimeError("Invalid limit value")

        query_limit = "LIMIT %s" % limit if limit > 0 else ""

        with get_cursor() as cursor:
            if cursor is None:
                raise RuntimeError("Failed to obtain database cursor for selection")

            try:
                with open(path.join(db_dir, "queries/select.sql"), "r") as file:
                    query = file.read().replace("{LIMIT}", query_limit)
                    cursor.execute(query)
                    result = cursor.fetchall()
                    return result
            except (FileNotFoundError, errors.Error) as e:
                raise RuntimeError(f"Error selecting logs: {e}")

    # Print a log entry
    @staticmethod
    def print_log(log):
        nr, log_type, timestamp, hostname, message = log

        # Fill atrributes with spaces to align the output
        nr = str(nr).rjust(4)
        log_type = log_type.ljust(6)
        hostname = hostname.ljust(8)

        print(f"{nr} | {log_type} | {timestamp} | {hostname} | {message}")

    # Print log entries
    @staticmethod
    def print_logs(logs):
        print(" Nr  | Type   | Timestamp           | Host     | Message")
        print("-----|--------|---------------------|----------|---------------------")
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
