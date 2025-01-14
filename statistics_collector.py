def collect_statistics(results):
    """
    Collect and print statistics from the test results.
    """
    tcp_results = [r for r in results if r and r["type"] == "TCP"]
    udp_results = [r for r in results if r and r["type"] == "UDP"]

    # TCP statistics
    if tcp_results:
        print("\n[TCP Statistics]")
        total_bytes = sum(r["bytes_received"] for r in tcp_results)
        total_duration = sum(r["duration"] for r in tcp_results)
        average_speed = sum(r["speed"] for r in tcp_results) / len(tcp_results)
        print(f"Total bytes transferred: {total_bytes} bytes")
        print(f"Total transfer time: {total_duration:.2f} seconds")
        print(f"Average transfer speed: {average_speed:.2f} bits/sec")

    # UDP statistics
    if udp_results:
        print("\n[UDP Statistics]")
        total_bytes = sum(r["bytes_received"] for r in udp_results)
        total_duration = sum(r["duration"] for r in udp_results)
        average_speed = sum(r["speed"] for r in udp_results) / len(udp_results)
        average_success_rate = sum(r["success_rate"] for r in udp_results) / len(udp_results)
        print(f"Total bytes transferred: {total_bytes} bytes")
        print(f"Total transfer time: {total_duration:.2f} seconds")
        print(f"Average transfer speed: {average_speed:.2f} bits/sec")
        print(f"Average success rate: {average_success_rate:.2f}%")

    # Overall statistics
    total_results = tcp_results + udp_results
    if total_results:
        print("\n[Overall Statistics]")
        total_bytes = sum(r["bytes_received"] for r in total_results)
        total_duration = sum(r["duration"] for r in total_results)
        average_speed = sum(r["speed"] for r in total_results) / len(total_results)
        print(f"Total bytes transferred: {total_bytes} bytes")
        print(f"Total transfer time: {total_duration:.2f} seconds")
        print(f"Average transfer speed: {average_speed:.2f} bits/sec")

def log_result(result):
    """
    Print detailed information for a single test result.
    """
    if result["type"] == "TCP":
        print(f"[TCP] {result['bytes_received']} bytes in {result['duration']:.2f} seconds ({result['speed']:.2f} bits/sec).")
    elif result["type"] == "UDP":
        print(f"[UDP] {result['bytes_received']} bytes in {result['duration']:.2f} seconds "
              f"({result['speed']:.2f} bits/sec), success rate: {result['success_rate']:.2f}%.")
