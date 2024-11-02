#!/usr/bin/env python3

import mysql.connector
from mysql.connector import Error


class log_type:
    STATUS = 1
    ALERT = 2
    METRIC = 3


def connect():
    return mysql.connector.connect(
            user='root',
            password='root',
            host='127.0.0.1',
            database='NMS',
            ssl_disabled=True)


def init():
    connection = connect()
    cursor = connection.cursor()

    # Create table log_type
    cursor.execute("CREATE TABLE IF NOT EXISTS log_type ("
                   "id INT PRIMARY KEY, "
                   "designation VARCHAR(255) NOT NULL);")

    # Populate table log_type
    cursor.execute("INSERT INTO log_type (id, designation) VALUES"
                   "(1, 'STATUS'),"
                   "(2, 'ALERT'),"
                   "(3, 'METRIC');")

    # Create table log
    cursor.execute("CREATE TABLE IF NOT EXISTS log ("
                   "id INT AUTO_INCREMENT PRIMARY KEY, "
                   "type INT, "
                   "timestamp DATETIME, "
                   "message TEXT, "
                   "FOREIGN KEY (type) REFERENCES log_type(id));")

    connection.commit()
    cursor.close()
    connection.close()


def insert(log_type_id, message):
    try:
        connection = connect()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO log (type, timestamp, message) VALUES (%s, NOW(), %s);",
                       (log_type_id, message))
        connection.commit()
    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


def select(limit=-1):
    try:
        connection = connect()
        cursor = connection.cursor()

        if limit == -1:
            cursor.execute("SELECT * FROM log;")
        else:
            cursor.execute("SELECT * FROM log LIMIT %s;", (limit,))

        result = cursor.fetchall()
        return result
    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


if __name__ == "__main__":
    init()
