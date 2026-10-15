class ProtocolError(Exception):
    """Raised when a protocol message is invalid."""
    def __init__(self, message: str, code: int = -32600):
        super().__init__(message)
        self.code = code
