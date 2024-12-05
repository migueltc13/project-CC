SELECT
    L.nr,
    L.timestamp,
    L.hostname,
    A.designation AS type,
    L.message
FROM (
    SELECT *
    FROM log
    WHERE type = 2
    ORDER BY nr DESC
    {LIMIT}
) AS L
INNER JOIN alert_type AS A ON L.alert_type = A.id
ORDER BY L.nr ASC;
