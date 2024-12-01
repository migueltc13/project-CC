INSERT INTO log (type, timestamp, hostname, message, alert_type)
VALUES
    (2, NOW(), %s, %s, %s);