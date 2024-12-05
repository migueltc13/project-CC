SELECT
    L.nr,
    L.timestamp,
    L.hostname,
    M.task_id,
    M.cpu_usage,
    M.ram_usage,
    M.bandwidth,
    M.jitter,
    M.packet_loss,
    M.latency,
    M.interface_stats
FROM (
    SELECT *
    FROM log
    WHERE type = 3
    ORDER BY nr DESC
    {LIMIT}
) AS L
INNER JOIN metric AS M ON L.metric_id = M.id
ORDER BY L.nr ASC;
