# Exception raised for invalid NMS Protocol version (NetTask or AlertFlow)
class InvalidVersionException(Exception):
    def __init__(self, received_version, expected_version, message="Invalid NMS Protocol version"):
        self.expected_version = expected_version
        self.received_version = received_version
        self.message = f"{message}\n" \
                       f"Received version: {received_version}\n" \
                       f"Expected version: {expected_version}"
        super().__init__(self.message)
    pass

    def __str__(self):
        return f"{self.message}"
