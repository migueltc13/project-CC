INSERT INTO log (type, timestamp, hostname, message)
VALUES
    (%s, NOW(), %s, %s);
