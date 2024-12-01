SELECT
    L.nr,
    L.timestamp,
    L.hostname
    M.cpu_usage,
    M.ram_usage,
    M.interface_stats,
    M.bandwidth,
    M.jitter,
    M.packet_loss,
    M.latency
INNER JOIN metric AS M ON L.metric_id = M.id
WHERE L.type = 3
ORDER BY L.nr DESC
{LIMIT};