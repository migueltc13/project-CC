# Exception raised for invalid NMS Protocol header (NetTask or AlertFlow)
class InvalidHeaderException(Exception):
    def __init__(self, message="Invalid header"):
        self.message = message
        super().__init__(self.message)
    pass

    def __str__(self):
        return f"{self.message}"
