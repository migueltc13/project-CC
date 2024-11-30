CREATE TABLE IF NOT EXISTS metric (
    id INT PRIMARY KEY,
    task_id INT,
    cpu_usage FLOAT,
    ram_usage FLOAT,
    interface_stats NVARCHAR(200),
    bandwidth FLOAT,
    jitter FLOAT,
    packet_loss FLOAT,
    latency FLOAT
);