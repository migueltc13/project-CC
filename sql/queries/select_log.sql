SELECT
    L.nr,
    T.designation AS type,
    L.timestamp,
    L.hostname,
    L.message,
    A.designation AS alert_type,
    L.metric_id
FROM (
    SELECT *
    FROM log
    ORDER BY nr DESC
    {LIMIT}
) AS L
INNER JOIN log_type AS T ON L.type = T.id
LEFT JOIN alert_type AS A ON L.alert_type = A.id
ORDER BY L.nr ASC;
