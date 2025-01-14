import socket
import struct
import time
import packetParser
from Exceptions import *
from ANSI import ANSI
from constants import *

BROADCAST_PORT = 13117
UDP_BUFFER_SIZE = 65535

def get_user_input():
    """
    prompt the user for:
      - file size (in bytes)
      - number of tcp connections
      - number of udp connections
    """
    while True:
        try:
            file_size = int(input(f"{ANSI.BOLD}Enter file size to request (in bytes): {ANSI.ENDC}"))
            num_tcp = int(input(f"{ANSI.BOLD}Enter number of TCP connections: {ANSI.ENDC}"))
            num_udp = int(input(f"{ANSI.BOLD}Enter number of UDP connections: {ANSI.ENDC}"))
            if file_size > 0 and num_tcp >= 0 and num_udp >= 0:
                return file_size, num_tcp, num_udp
            else:
                print(f"{ANSI.WARNING}All inputs must be positive integers{ANSI.ENDC}")
        except ValueError:
            print(f"{ANSI.FAIL}Invalid input. Please enter positive integers{ANSI.ENDC}")


def listen_for_offer():
    """
    listen for "offer" messages from the server on the broadcast port
    validate the magic cookie and message type, and extract the udp and tcp ports
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', BROADCAST_PORT))
    print(f"{ANSI.OKBLUE}[Client] Listening for offer messages on port {BROADCAST_PORT}{ANSI.ENDC}")

    while True:
        try:
            data, addr = sock.recvfrom(UDP_BUFFER_SIZE)
            result = packetParser.parse_udp_packet(data)

            if result['message_type'] == OFFER_TYPE:
                print(f"{ANSI.OKGREEN}[Client] Received offer from {addr[0]}: UDP port={result['server_udp_port']}, TCP port={result['server_tcp_port']}{ANSI.ENDC}")
                sock.close()
                return addr[0], result['server_udp_port'], result['server_tcp_port']

        except (PacketParsingError, CookieMismatchError, UnknownMessageTypeError) as e:
            print(f"{ANSI.FAIL}[Client] Error parsing offer message: {e}{ANSI.ENDC}")
        except Exception as e:
            print(f"{ANSI.FAIL}[Client] unexpected error: {e}{ANSI.ENDC}")


def tcp_speed_test(server_ip, tcp_port, file_size, results, index):
    """
    connect to the server over tcp, request the file size, and measure the transfer time
    store the results in the shared `results` list
    """
    try:
        start_time = time.time()

        # connect to the server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_ip, tcp_port))

        # send the requested file size
        sock.sendall(f"{file_size}\n".encode())

        # receive the file
        bytes_received = 0
        while bytes_received < file_size:
            data = sock.recv(65536)  # receive in 64 kb chunks
            if not data:
                break
            bytes_received += len(data)

        # measure the transfer time
        end_time = time.time()
        duration = end_time - start_time
        speed = (bytes_received * 8) / duration  # speed in bits/sec

        results[index] = {
            "type": "TCP",
            "bytes_received": bytes_received,
            "duration": duration,
            "speed": speed
        }

        print(f"{ANSI.HEADER}[TCP {index + 1}] Transfer completed: {bytes_received} bytes in {duration:.2f} seconds ({speed:.2f} bits/sec){ANSI.ENDC}")

    except Exception as e:
        print(f"{ANSI.FAIL}[TCP {index + 1}] ERROR: {e}{ANSI.ENDC}")
        results[index] = None
    finally:
        sock.close()


def udp_speed_test(server_ip, udp_port, file_size, results, index):
    """
    send a "request" message to the server over udp, then receive payload packets
    measure the transfer time and calculate packet loss
    """
    try:
        start_time = time.time()

        # create a udp socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)

        # send a "request" message
        request_packet = struct.pack('>I B Q', MAGIC_COOKIE, REQUEST_TYPE, file_size)
        sock.sendto(request_packet, (server_ip, udp_port))

        # receive payload packets
        bytes_received = 0
        segments_received = set()
        total_segments = None

        while True:
            try:
                data, addr = sock.recvfrom(UDP_BUFFER_SIZE)
                result = packetParser.parse_udp_packet(data)

                if result['message_type'] == PAYLOAD_TYPE:
                    if total_segments is None:
                        total_segments = result['total_segments']

                    current_segment = result['current_segment']
                    segments_received.add(current_segment)
                    bytes_received += len(result['payload'])

            except socket.timeout:
                # stop receiving if no data arrives for 1 second
                break

        # measure the transfer time
        end_time = time.time()
        duration = end_time - start_time
        speed = (bytes_received * 8) / duration if duration > 0 else 0  # speed in bits/sec

        # calculate packet loss
        if total_segments:
            packets_received = len(segments_received)
            success_rate = (packets_received / total_segments) * 100
        else:
            success_rate = 0.0

        results[index] = {
            "type": "UDP",
            "bytes_received": bytes_received,
            "duration": duration,
            "speed": speed,
            "success_rate": success_rate
        }

        print(f"{ANSI.OKCYAN}[UDP {index + 1}] Transfer completed: {bytes_received} bytes in {duration:.2f} seconds ({speed:.2f} bits/sec), success rate: {success_rate:.2f}%{ANSI.ENDC}")

    except Exception as e:
        print(f"{ANSI.FAIL}[UDP {index + 1}] ERROR: {e}{ANSI.ENDC}")
        results[index] = None
    finally:
        sock.close()
