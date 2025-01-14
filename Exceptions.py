from ANSI import ANSI

class PacketParsingError(Exception):
    """
    Base class for all packet parsing errors.
    """
    def __init__(self, message="A packet parsing error occurred."):
        super().__init__(f"{ANSI.FAIL}{message}{ANSI.ENDC}")


class PacketTooShortError(PacketParsingError):
    """
    Raised when the packet data is too short to parse the required fields.
    """
    def __init__(self, actual_length, required_length):
        message = (
            f"Packet is only {actual_length} bytes long, but at least "
            f"{required_length} bytes are required."
        )
        super().__init__(message)


class CookieMismatchError(PacketParsingError):
    """
    Raised when the packet's magic cookie doesn't match the expected value.
    """
    def __init__(self, expected_cookie, actual_cookie):
        message = (
            f"Magic cookie mismatch. Expected 0x{expected_cookie:x}, "
            f"but got 0x{actual_cookie:x}."
        )
        super().__init__(message)


class UnknownMessageTypeError(PacketParsingError):
    """
    Raised when the message type is not recognized by the protocol.
    """
    def __init__(self, message_type: int):
        message = f"Unknown message type: 0x{message_type:x}."
        super().__init__(message)
