SELECT
    L.nr,
    T.designation AS type,
    L.timestamp,
    L.hostname,
    L.message
FROM log AS L
INNER JOIN log_type AS T ON L.type = T.id
ORDER BY L.nr DESC
{LIMIT};
