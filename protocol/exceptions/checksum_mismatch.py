# Exception raised for checksum mismatch in NetTask packets
class ChecksumMismatchException(Exception):
    def __init__(self, message="Checksum mismatch"):
        self.message = message
        super().__init__(self.message)
    pass

    def __str__(self):
        return f'{self.message}'
