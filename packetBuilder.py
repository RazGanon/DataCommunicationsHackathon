import struct
from constants import *


def build_offer_msg(server_udp_port, server_tcp_port):
    """
    build the 'offer' message (server -> client)

    offer message format:
      4 bytes: magic cookie (0xabcddcba)
      1 byte: message type (0x2)
      2 bytes: server udp port
      2 bytes: server tcp port
    """
    # use big-endian (network byte order) for consistent packet structure
    # format '>I B H H' means:
    #   I = unsigned int (4 bytes) for magic cookie
    #   B = unsigned char (1 byte) for message type
    #   H = unsigned short (2 bytes) for udp and tcp ports
    return struct.pack('>I B H H', MAGIC_COOKIE, OFFER_TYPE, server_udp_port, server_tcp_port)


def build_request_msg(file_size):
    """
    build the 'request' message (client -> server)

    request message format:
      4 bytes: magic cookie (0xabcddcba)
      1 byte: message type (0x3)
      8 bytes: file size
    """
    # format '>I B Q' means:
    #   I = unsigned int (4 bytes) for magic cookie
    #   B = unsigned char (1 byte) for message type
    #   Q = unsigned long (8 bytes) for file size
    return struct.pack('>I B Q', MAGIC_COOKIE, REQUEST_TYPE, file_size)


def build_payload_msg(total_segments, current_segment, payload):
    """
    build the 'payload' message (server -> client)

    payload message format:
      4 bytes: magic cookie (0xabcddcba)
      1 byte: message type (0x4)
      8 bytes: total segment count
      8 bytes: current segment number
      variable: payload
    """
    # create the header using '>I B Q Q' format:
    #   I = unsigned int (4 bytes) for magic cookie
    #   B = unsigned char (1 byte) for message type
    #   Q = unsigned long (8 bytes) for total segments
    #   Q = unsigned long (8 bytes) for current segment number
    header = struct.pack('>I B Q Q', MAGIC_COOKIE, PAYLOAD_TYPE, total_segments, current_segment)

    # append the payload to the header
    return header + payload
