CREATE TABLE IF NOT EXISTS log (
    nr INT AUTO_INCREMENT PRIMARY KEY,
    type INT NOT NULL,
    timestamp DATETIME NOT NULL,
    hostname NVARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    alert_type INT,
    metric_id INT,
    FOREIGN KEY (type) REFERENCES log_type(id),
    FOREIGN KEY (alert_type) REFERENCES alert_type(id),
    FOREIGN KEY (metric_id) REFERENCES metric(id)
);