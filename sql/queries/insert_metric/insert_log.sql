INSERT INTO log (type, timestamp, hostname, message, metric_id)
VALUES
    (3, NOW(), %s, %s, LAST_INSERT_ID());
