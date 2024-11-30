INSERT INTO metric (cpu_usage, ram_usage, interface_stats, bandwidth, jitter, packet_loss, latency)
VALUES
    (%s, %s, %s, %s, %s, %s, %s);

INSERT INTO log (type, timestamp, hostname, message, metric_id)
VALUES
    (3, NOW(), %s, %s, LAST_INSERT_ID());