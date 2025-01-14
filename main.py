import threading
import time
from Server import broadcast_offers, udp_server_loop, tcp_server_loop
from Client import listen_for_offer, tcp_speed_test, udp_speed_test, get_user_input
from ANSI import ANSI

def collect_statistics(results):
    """
    collect and print statistics from the test results
    """
    tcp_results = [r for r in results if r and r["type"] == "TCP"]
    udp_results = [r for r in results if r and r["type"] == "UDP"]

    # tcp statistics
    if tcp_results:
        print(f"{ANSI.HEADER}\n[TCP Statistics]{ANSI.ENDC}")
        total_bytes = sum(r["bytes_received"] for r in tcp_results)
        total_duration = sum(r["duration"] for r in tcp_results)
        average_speed = sum(r["speed"] for r in tcp_results) / len(tcp_results)
        print(f"{ANSI.HEADER}total bytes transferred: {total_bytes} bytes{ANSI.ENDC}")
        print(f"{ANSI.HEADER}total transfer time: {total_duration:.2f} seconds{ANSI.ENDC}")
        print(f"{ANSI.HEADER}average transfer speed: {average_speed:.2f} bits/sec{ANSI.ENDC}")

    # udp statistics
    if udp_results:
        print(f"{ANSI.OKCYAN}\n[UDP Statistics]{ANSI.ENDC}")
        total_bytes = sum(r["bytes_received"] for r in udp_results)
        total_duration = sum(r["duration"] for r in udp_results)
        average_speed = sum(r["speed"] for r in udp_results) / len(udp_results)
        average_success_rate = sum(r["success_rate"] for r in udp_results) / len(udp_results)
        print(f"{ANSI.OKCYAN}total bytes transferred: {total_bytes} bytes{ANSI.ENDC}")
        print(f"{ANSI.OKCYAN}total transfer time: {total_duration:.2f} seconds{ANSI.ENDC}")
        print(f"{ANSI.OKCYAN}average transfer speed: {average_speed:.2f} bits/sec{ANSI.ENDC}")
        print(f"{ANSI.OKCYAN}average success rate: {average_success_rate:.2f}%{ANSI.ENDC}")

    # overall statistics
    total_results = tcp_results + udp_results
    if total_results:
        print(f"{ANSI.BOLD}\n[Overall Statistics]{ANSI.ENDC}")
        total_bytes = sum(r["bytes_received"] for r in total_results)
        total_duration = sum(r["duration"] for r in total_results)
        average_speed = sum(r["speed"] for r in total_results) / len(total_results)
        print(f"{ANSI.BOLD}total bytes transferred: {total_bytes} bytes{ANSI.ENDC}")
        print(f"{ANSI.BOLD}total transfer time: {total_duration:.2f} seconds{ANSI.ENDC}")
        print(f"{ANSI.BOLD}average transfer speed: {average_speed:.2f} bits/sec{ANSI.ENDC}")

def log_result(result):
    """
    print detailed information for a single test result
    """
    if result["type"] == "TCP":
        print(f"{ANSI.HEADER}[tcp] {result['bytes_received']} bytes in {result['duration']:.2f} seconds ({result['speed']:.2f} bits/sec){ANSI.ENDC}")
    elif result["type"] == "UDP":
        print(f"{ANSI.OKCYAN}[udp] {result['bytes_received']} bytes in {result['duration']:.2f} seconds "
              f"({result['speed']:.2f} bits/sec), success rate: {result['success_rate']:.2f}%{ANSI.ENDC}")

def start_server(stop_event, udp_port, tcp_port):
    """
    start the server with specified udp and tcp ports
    includes broadcasting offers, udp, and tcp loops
    """
    broadcast_thread = threading.Thread(
        target=broadcast_offers, args=(stop_event, udp_port, tcp_port), daemon=True
    )
    udp_thread = threading.Thread(
        target=udp_server_loop, args=(stop_event, udp_port), daemon=True
    )
    tcp_thread = threading.Thread(
        target=tcp_server_loop, args=(stop_event, tcp_port), daemon=True
    )

    broadcast_thread.start()
    udp_thread.start()
    tcp_thread.start()

    return [broadcast_thread, udp_thread, tcp_thread]

def run_client():
    """
    keep the client running indefinitely, listening for offers and performing tests
    """
    while True:
        try:
            print(f"{ANSI.OKBLUE}[Client] Listening for offer messages...{ANSI.ENDC}")
            server_ip, udp_port, tcp_port = listen_for_offer()

            file_size, num_tcp, num_udp = get_user_input()

            results = [None] * (num_tcp + num_udp)
            threads = []

            for i in range(num_tcp):
                thread = threading.Thread(
                    target=tcp_speed_test, args=(server_ip, tcp_port, file_size, results, i), daemon=True
                )
                threads.append(thread)
                thread.start()

            for i in range(num_udp):
                thread = threading.Thread(
                    target=udp_speed_test, args=(server_ip, udp_port, file_size, results, num_tcp + i), daemon=True
                )
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            print(f"{ANSI.OKGREEN}[Client] Collecting and printing statistics...{ANSI.ENDC}")
            collect_statistics(results)
            print(f"{ANSI.OKBLUE}[Client] Test completed. Ready for the next round.{ANSI.ENDC}")

        except KeyboardInterrupt:
            print(f"{ANSI.WARNING}[Client] Shutting down...{ANSI.ENDC}")
            break
        except Exception as e:
            print(f"{ANSI.FAIL}[Client] Unexpected error: {e}{ANSI.ENDC}")

def main():
    """
    main function to start the server and client concurrently and handle cleanup
    """
    stop_event = threading.Event()

    udp_port = 50001
    tcp_port = 50002

    try:
        print(f"{ANSI.BOLD}[Main] Starting server...{ANSI.ENDC}")
        server_threads = start_server(stop_event, udp_port, tcp_port)

        client_thread = threading.Thread(target=run_client, daemon=True)
        client_thread.start()

        print(f"{ANSI.OKGREEN}[Main] Server and Client are running. Press CTRL + C to stop.{ANSI.ENDC}")
        while True:
            time.sleep(0.5)

    except KeyboardInterrupt:
        print(f"{ANSI.WARNING}[Main] Shutting down...{ANSI.ENDC}")
    finally:
        stop_event.set()

        for thread in server_threads:
            thread.join()

        print(f"{ANSI.OKGREEN}[Main] All threads stopped. Exiting.{ANSI.ENDC}")

if __name__ == "__main__":
    main()
