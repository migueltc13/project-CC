INSERT INTO log (type, timestamp, hostname, alert_type, message)
VALUES
    (2, NOW(), %s, %s, %s);
