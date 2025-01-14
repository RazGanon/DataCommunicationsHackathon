import struct
from Exceptions import *
from ANSI import ANSI

MAGIC_COOKIE = 0xabcddcba
OFFER_TYPE = 0x2
REQUEST_TYPE = 0x3
PAYLOAD_TYPE = 0x4

def parse_udp_packet(data):
    """
    parse an incoming udp datagram according to your custom protocol

    packet structure (minimum 5 bytes):
      1) 4 bytes: magic cookie
      2) 1 byte: message type
      => then it branches based on message type:

      - offer (0x2):
          total length = 9 bytes (4 cookie + 1 type + 2 udp port + 2 tcp port)
      - request (0x3):
          total length = 13 bytes (4 cookie + 1 type + 8 file size)
      - payload (0x4):
          total length = >= 21 bytes (4 cookie + 1 type + 8 total seg + 8 curr seg + payload)

    raises:
      packettooshorterror, cookiemismatcherror, unknownmessagetypeerror
    returns:
      a dict with parsed fields if successful
    """
    # check minimum length for magic cookie + message type
    if len(data) < 5:
        error_msg = f"{ANSI.FAIL}received only {len(data)} bytes, but need at least 5 for header{ANSI.ENDC}"
        raise PacketTooShortError(error_msg)

    # unpack the first 5 bytes
    cookie, msg_type = struct.unpack('>I B', data[:5])

    # validate the magic cookie
    if cookie != MAGIC_COOKIE:
        error_msg = (
            f"{ANSI.FAIL}magic cookie mismatch: expected 0x{MAGIC_COOKIE:x}, got 0x{cookie:x}{ANSI.ENDC}"
        )
        raise CookieMismatchError(expected_cookie=MAGIC_COOKIE, actual_cookie=cookie)

    # branch on message type
    if msg_type == OFFER_TYPE:
        # offer: total 9 bytes
        if len(data) < 9:
            error_msg = f"{ANSI.FAIL}offer packet requires 9 bytes, got {len(data)} bytes{ANSI.ENDC}"
            raise PacketTooShortError(error_msg)
        # unpack the entire offer packet
        _, _, server_udp_port, server_tcp_port = struct.unpack('>I B H H', data[:9])
        return {
            'message_type': OFFER_TYPE,
            'server_udp_port': server_udp_port,
            'server_tcp_port': server_tcp_port
        }

    elif msg_type == REQUEST_TYPE:
        # request: total 13 bytes
        if len(data) < 13:
            error_msg = f"{ANSI.FAIL}request packet requires 13 bytes, got {len(data)} bytes{ANSI.ENDC}"
            raise PacketTooShortError(error_msg)
        _, _, file_size = struct.unpack('>I B Q', data[:13])
        return {
            'message_type': REQUEST_TYPE,
            'file_size': file_size
        }

    elif msg_type == PAYLOAD_TYPE:
        # payload: at least 21 bytes (4 + 1 + 8 + 8) + variable payload
        if len(data) < 21:
            error_msg = f"{ANSI.FAIL}payload packet requires at least 21 bytes, got {len(data)} bytes{ANSI.ENDC}"
            raise PacketTooShortError(error_msg)
        _, _, total_segments, current_segment = struct.unpack('>I B Q Q', data[:21])
        payload = data[21:]  # the rest is the actual payload
        return {
            'message_type': PAYLOAD_TYPE,
            'total_segments': total_segments,
            'current_segment': current_segment,
            'payload': payload,
            'payload_size': len(payload)
        }

    else:
        # unknown or unsupported message type
        error_msg = f"{ANSI.FAIL}message type 0x{msg_type:x} is not recognized{ANSI.ENDC}"
        raise UnknownMessageTypeError(error_msg)
