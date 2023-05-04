import socket
import time
import struct
from random import randbytes

HOST = "web.de"
PORT = 12345
ICMP_PROTO = socket.getprotobyname("icmp")


def get_ipv4(host: str) -> str:
    addr_info = socket.getaddrinfo(host, None, socket.AF_INET)
    ipv4_info = [info[-1][0] for info in addr_info if info[0] == socket.AF_INET]

    if len(ipv4_info) != 1:
        raise NotImplementedError(f"Cannot extract ipv4 from {host}. Got {addr_info}")
    return ipv4_info[0]


def probe_route(host: str, hops: int):
    message = randbytes(8)
    target_ipv4 = get_ipv4(host)
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, hops)
    icmp_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, ICMP_PROTO)

    time_bs = time.time()
    print("Sending UDP Payload.")
    udp_socket.sendto(message, (target_ipv4, PORT))

    while True:
        data, addr = icmp_socket.recvfrom(1024)
        time_icmp = time.time()
        print(f"Received ICMP from {addr}")
        icmp_message = data[-8:]
        if icmp_message != message:
            print("Received ICMP message does not match. Discarding.")
            continue

        icmp_header = data[20:28]
        icmp_type, icmp_code, _, _ = struct.unpack("BBHi", icmp_header)
        print(
            f"ICMP ({icmp_type=}, {icmp_code=}) received after {time_icmp - time_bs}ms"
        )
        break


if __name__ == "__main__":
    for i in range(1, 20):
        probe_route("kkos.net", i)
