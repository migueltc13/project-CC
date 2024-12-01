SELECT
    L.nr,
    T.designation AS type,
    L.timestamp,
    L.hostname,
    L.message,
    A.id AS alert_type,
    M.id AS metric_id
FROM log AS L
INNER JOIN log_type AS T ON L.type = T.id
LEFT JOIN alert_type AS A ON L.alert_type = A.id
LEFT JOIN metric AS M ON L.metric_id = M.id
ORDER BY L.nr DESC
{LIMIT};