import socket
import time
import struct
from random import randbytes
from dataclasses import dataclass


def get_ipv4(host: str) -> str:
    addr_info = socket.getaddrinfo(host, None, socket.AF_INET, proto=socket.SOCK_DGRAM)
    ipv4_info = [info[-1][0] for info in addr_info if info[0] == socket.AF_INET]

    if len(ipv4_info) != 1:
        raise NotImplementedError(f"Cannot extract ipv4 from {host}. Got {addr_info}")
    return ipv4_info[0]


@dataclass
class IPv4Header:
    source_ip: str
    dst_ip: str
    ttl: int
    protocol: int

    @staticmethod
    def from_bytes(header_bytes: bytes) -> "IPv4Header":
        ipv4_header = struct.unpack(">BBHHHBBH4s4s", header_bytes)
        ttl = ipv4_header[5]
        proto = ipv4_header[6]
        source_ip = socket.inet_ntoa(ipv4_header[-2])
        dst_ip = socket.inet_ntoa(ipv4_header[-1])
        return IPv4Header(source_ip, dst_ip, ttl, proto)


@dataclass
class ICMPHeader:
    type: int
    code: int

    @staticmethod
    def from_bytes(header_bytes: bytes) -> "ICMPHeader":
        icmp_type, icmp_code, _ = struct.unpack(">BBH", header_bytes)
        return ICMPHeader(icmp_type, icmp_code)


@dataclass
class UDPHeader:
    source_port: int
    dst_port: int

    @staticmethod
    def from_bytes(header_bytes: bytes) -> "UDPHeader":
        source_port, dst_port, _, _ = struct.unpack(">HHHH", header_bytes)
        return UDPHeader(source_port, dst_port)


def probe_route(host: str, hops: int, port=12346):
    udp_payload = randbytes(8)
    target_ipv4 = get_ipv4(host)
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, hops)

    ICMP_PROTO = socket.getprotobyname("icmp")
    icmp_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, ICMP_PROTO)
    icmp_socket.settimeout(5)

    time_bs = time.time()
    # print(f"Sending UDP Payload ({udp_payload}) to {target_ipv4}.")
    udp_socket.sendto(udp_payload, (target_ipv4, port))

    while True:
        try:
            data, _ = icmp_socket.recvfrom(1024)
        except socket.timeout:
            print(f"[Hops: {hops}] Did not receive any ICMP return.")
            break

        rtt = time.time() - time_bs
        ipv4_header = IPv4Header.from_bytes(data[:20])
        print(
            f"[Hops: {hops}, {rtt:.2f}ms] Received IPv4 package in ICMP socket: {ipv4_header}..."
        )
        if ipv4_header.source_ip == target_ipv4:
            print("ICMP comes from the target!")
            break

        assert ipv4_header.protocol == 1

        icmp_header = ICMPHeader.from_bytes(data[20:24])
        print(f"... it contains an ICMP message: {icmp_header}")

        icmp_ref_ipv4_header = IPv4Header.from_bytes(data[28:48])
        print(f"... which references an IPv4 package: {icmp_ref_ipv4_header}")
        if icmp_ref_ipv4_header.dst_ip != target_ipv4:
            print(f"Referenced IPv4 package dst_ip does not match!")
            continue
        if icmp_ref_ipv4_header.ttl != 1:
            print(f"Referenced IPv4 package has TTL={icmp_ref_ipv4_header.ttl}")

        icmp_ref_udp_header = UDPHeader.from_bytes(data[48:56])
        print(f"... which contains a UDP package: {icmp_ref_udp_header}")
        if icmp_ref_udp_header.dst_port != port:
            print("Referenced UDP destination port does not match!")
            continue

        recv_udp_payload = data[56:64]
        if len(recv_udp_payload) == 0:
            print("... which does not contain a UDP payload.")
            break
        elif recv_udp_payload != udp_payload:
            print(
                f"... which contains a UDP payload {recv_udp_payload} that does not match"
            )
            continue
        else:
            print("... which contains the right UDP payload!")
            break


if __name__ == "__main__":
    for i in range(1, 20):
        probe_route("google.com", i)
        print("___________________________________________")
