SELECT
    L.nr,
    L.timestamp,
    L.hostname,
    A.designation AS type,
    L.message
FROM log AS L
INNER JOIN alert_type AS A ON L.alert_type = A.id 
WHERE L.type = 2
ORDER BY L.nr DESC
{LIMIT};