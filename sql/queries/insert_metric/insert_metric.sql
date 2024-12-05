INSERT INTO metric (task_id, cpu_usage, ram_usage, interface_stats, bandwidth, jitter, packet_loss, latency)
VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s);
