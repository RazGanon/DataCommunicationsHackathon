import socket
import struct
import threading
import time
import packetBuilder
import packetParser
from Exceptions import *
from ANSI import ANSI
from constants import *
BROADCAST_PORT = 13117
OFFER_INTERVAL = 1.0
UDP_CHUNK_SIZE = 1400
TCP_CHUNK_SIZE = 65536

# -----------------------------------------------------------------------------
# 1) Thread: Broadcast "offer" messages every second
# -----------------------------------------------------------------------------
def broadcast_offers(stop_event, udp_port, tcp_port):
    """
    broadcasts an "offer" message via udp every offer_interval seconds
    includes the dynamic tcp and udp ports in the message
    """
    broadcaster = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # build the offer packet dynamically
    offer_message = packetBuilder.build_offer_msg(udp_port, tcp_port)
    print(f"{ANSI.OKCYAN}[UDP] Broadcasting offers on port {BROADCAST_PORT}{ANSI.ENDC}")

    while not stop_event.is_set():
        try:
            broadcaster.sendto(offer_message, ('<broadcast>', BROADCAST_PORT))
        except Exception as e:
            print(f"{ANSI.FAIL}[broadcast thread] Error sending offer: {e}{ANSI.ENDC}")

        time.sleep(OFFER_INTERVAL)

    broadcaster.close()
    print(f"{ANSI.OKCYAN}[UDP] Broadcast thread stopped{ANSI.ENDC}")

# -----------------------------------------------------------------------------
# 2) UDP Server
# -----------------------------------------------------------------------------
def handle_udp_request(data, addr, udp_socket):
    """
    handle a single udp datagram in a separate thread
    parses the datagram to determine its type and sends payloads if it is a request
    """
    try:
        # parse the udp packet
        result = packetParser.parse_udp_packet(data)

        msg_type = result['message_type']
        if msg_type == REQUEST_TYPE:
            file_size = result['file_size']
            print(f"{ANSI.OKCYAN}[UDP] {addr} Requested {file_size} bytes{ANSI.ENDC}")

            total_segments = (file_size + UDP_CHUNK_SIZE - 1) // UDP_CHUNK_SIZE
            bytes_sent = 0
            segment_index = 0
            dummy_data = b'X' * UDP_CHUNK_SIZE

            while bytes_sent < file_size:
                remaining = file_size - bytes_sent
                chunk = dummy_data[:min(UDP_CHUNK_SIZE, remaining)]

                payload_header = struct.pack(
                    '>I B Q Q',
                    MAGIC_COOKIE,
                    PAYLOAD_TYPE,
                    total_segments,
                    segment_index
                )
                packet = payload_header + chunk
                udp_socket.sendto(packet, addr)
                bytes_sent += len(chunk)
                segment_index += 1

            print(f"{ANSI.OKCYAN}[UDP] Finished sending {bytes_sent} bytes to {addr} in {segment_index} segments{ANSI.ENDC}")
        else:
            print(f"{ANSI.OKCYAN}[UDP] Received unexpected message type {msg_type} from {addr}, ignoring{ANSI.ENDC}")

    except (PacketTooShortError, CookieMismatchError, UnknownMessageTypeError) as e:
        print(f"{ANSI.FAIL}[UDP] Parsing error from {addr}: {e}{ANSI.ENDC}")
    except Exception as e:
        print(f"{ANSI.FAIL}[UDP] Unexpected error handling packet from {addr}: {e}{ANSI.ENDC}")


def udp_server_loop(stop_event, udp_port):
    """
    listens for udp datagrams on the provided udp_port and handles each in a thread
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', udp_port))
    sock.settimeout(1.0)

    print(f"{ANSI.OKCYAN}[UDP] Server listening on port {udp_port}{ANSI.ENDC}")

    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(65535)
        except socket.timeout:
            continue
        except Exception as e:
            print(f"{ANSI.FAIL}[UDP] recvfrom error: {e}{ANSI.ENDC}")
            continue

        t = threading.Thread(
            target=handle_udp_request,
            args=(data, addr, sock),
            daemon=True
        )
        t.start()

    sock.close()
    print(f"{ANSI.OKCYAN}[UDP] UDP Server loop stopped{ANSI.ENDC}")

# -----------------------------------------------------------------------------
# 3) TCP Server
# -----------------------------------------------------------------------------
def handle_tcp_connection(client_sock, addr):
    """
    handle a single tcp client
    reads file size as ascii + newline, sends that many bytes back
    """
    print(f"{ANSI.HEADER}[TCP] New connection from {addr}{ANSI.ENDC}")
    try:
        client_sock.settimeout(10)
        file_size_bytes = b''
        while b'\n' not in file_size_bytes:
            chunk = client_sock.recv(1)
            if not chunk:
                raise ConnectionError("Client closed before sending file size")
            file_size_bytes += chunk

        file_size_str = file_size_bytes.strip().decode()
        try:
            file_size = int(file_size_str)
        except ValueError:
            raise PacketParsingError(f"{ANSI.FAIL}Invalid file size '{file_size_str}' from Client{addr}{ANSI.ENDC}")

        print(f"{ANSI.HEADER}[TCP] {addr} requested {file_size} bytes{ANSI.ENDC}")

        bytes_sent = 0
        dummy_data = b'Z' * TCP_CHUNK_SIZE
        while bytes_sent < file_size:
            remaining = file_size - bytes_sent
            to_send = dummy_data[:min(TCP_CHUNK_SIZE, remaining)]
            client_sock.sendall(to_send)
            bytes_sent += len(to_send)

        print(f"{ANSI.HEADER}[TCP] Finished sending {bytes_sent} bytes to {addr}{ANSI.ENDC}")

    except PacketParsingError as e:
        print(f"{ANSI.FAIL}[TCP] Parsing error from {addr}: {e}{ANSI.ENDC}")
    except Exception as e:
        print(f"{ANSI.FAIL}[TCP] Error handling {addr}: {e}{ANSI.ENDC}")
    finally:
        client_sock.close()
        print(f"{ANSI.FAIL}[TCP] Connection with {addr} closed{ANSI.ENDC}")


def tcp_server_loop(stop_event, tcp_port):
    """
    accepts tcp connections on the provided tcp_port and spawns a handler thread for each client
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', tcp_port))
    s.listen(5)
    s.settimeout(1.0)

    print(f"{ANSI.HEADER}[TCP] Server listening on port {tcp_port}{ANSI.ENDC}")

    while not stop_event.is_set():
        try:
            client_sock, addr = s.accept()
        except socket.timeout:
            continue
        except Exception as e:
            print(f"{ANSI.FAIL}[TCP] Accept error: {e}{ANSI.ENDC}")
            continue

        t = threading.Thread(
            target=handle_tcp_connection,
            args=(client_sock, addr),
            daemon=True
        )
        t.start()

    s.close()
    print(f"{ANSI.HEADER}[TCP] TCP Server loop stopped{ANSI.ENDC}")
