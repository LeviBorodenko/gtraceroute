import enum
import socket
import time
import struct
from random import randbytes
from dataclasses import dataclass, field

PROBE_BASE_PORT = 12345
PROBE_UDP_PAYLOAD_SIZE = 8


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


class InvalidProbeReplyException(Exception):
    pass


class ProbeStatus(enum.Enum):
    PENDING = 0
    IN_PROGRESS = 1
    SUCCESSFUL = 2
    FAILED = 3


@dataclass
class ProbeRequest:
    ipv4: str
    ttl: int
    port: int = PROBE_BASE_PORT
    udp_payload: bytes = field(
        default_factory=lambda: randbytes(PROBE_UDP_PAYLOAD_SIZE)
    )
    request_creation_ts: float = field(default_factory=lambda: time.time())
    status: ProbeStatus = ProbeStatus.PENDING
    retry_count: int = 0
    probe_dispatch_ts: float | None = None

    @staticmethod
    def generate_ttl_sweep(target_ipv4: str, max_ttl: int = 16) -> list["ProbeRequest"]:
        sweep = []
        for i in range(1, max_ttl + 1):
            sweep.append(ProbeRequest(target_ipv4, i))
        return sweep


@dataclass
class ProbeReply:
    receive_ts: float
    ipv4_header: IPv4Header

    icmp_header: ICMPHeader
    ref_ipv4_header: IPv4Header
    ref_udp_header: UDPHeader
    ref_udp_payload: bytes | None

    @staticmethod
    def from_bytes(
        icmp_packet: bytes,
        receive_ts: float | None = None,
        payload_byte_size: int = PROBE_UDP_PAYLOAD_SIZE,
    ) -> "ProbeReply":
        receive_ts = receive_ts or time.time()

        ipv4_header = IPv4Header.from_bytes(icmp_packet[:20])
        if ipv4_header.protocol != 1:
            raise InvalidProbeReplyException(
                "ICMP Packet does not have the correct protocol in its outer IPv4 header. "
                f"Got {ipv4_header.protocol=}."
            )

        icmp_header = ICMPHeader.from_bytes(icmp_packet[20:24])

        ref_ipv4_header = IPv4Header.from_bytes(icmp_packet[28:48])
        if ref_ipv4_header.protocol != 17:
            raise InvalidProbeReplyException(
                "ICMP packet does not contain a UDP packet."
            )
        ref_udp_header = UDPHeader.from_bytes(icmp_packet[48:56])
        ref_udp_payload = icmp_packet[56 : (56 + payload_byte_size)]
        ref_udp_payload = None if len(ref_udp_payload) == 0 else ref_udp_payload
        return ProbeReply(
            receive_ts,
            ipv4_header,
            icmp_header,
            ref_ipv4_header,
            ref_udp_header,
            ref_udp_payload,
        )


def main():
    target_ipv4 = get_ipv4("google.com")
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    ICMP_PROTO = socket.getprotobyname("icmp")
    icmp_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, ICMP_PROTO)
    icmp_socket.settimeout(5)

    sweep = ProbeRequest.generate_ttl_sweep(target_ipv4, 12)

    for probe in sweep:
        udp_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, probe.ttl)
        time_bs = time.time()
        udp_socket.sendto(probe.udp_payload, (probe.ipv4, probe.port))
        probe.status = ProbeStatus.IN_PROGRESS
        probe.probe_dispatch_ts = time_bs

    while True:
        try:
            data = icmp_socket.recv(1024)
            probe_reply = ProbeReply.from_bytes(data)
            print(probe_reply)
            print("_______________________")
        except socket.timeout:
            print("No ICMP packet arrived before timeout. Stopping sweep.")
            break
        except InvalidProbeReplyException as e:
            raise e

    # rtt = time.time() - time_bs
    # ipv4_header = IPv4Header.from_bytes(data[:20])
    # print(
    #     f"[Hops: {hops}, {rtt:.2f}ms] Received IPv4 package in ICMP socket: {ipv4_header}..."
    # )
    # if ipv4_header.source_ip == target_ipv4:
    #     print("ICMP comes from the target!")
    #     break
    #
    # assert ipv4_header.protocol == 1
    #
    # icmp_header = ICMPHeader.from_bytes(data[20:24])
    # print(f"... it contains an ICMP message: {icmp_header}")
    #
    # icmp_ref_ipv4_header = IPv4Header.from_bytes(data[28:48])
    # print(f"... which references an IPv4 package: {icmp_ref_ipv4_header}")
    # if icmp_ref_ipv4_header.dst_ip != target_ipv4:
    #     print(f"Referenced IPv4 package dst_ip does not match!")
    #     continue
    # if icmp_ref_ipv4_header.ttl != 1:
    #     print(f"Referenced IPv4 package has TTL={icmp_ref_ipv4_header.ttl}")
    #
    # icmp_ref_udp_header = UDPHeader.from_bytes(data[48:56])
    # print(f"... which contains a UDP package: {icmp_ref_udp_header}")
    # if icmp_ref_udp_header.dst_port != port:
    #     print("Referenced UDP destination port does not match!")
    #     continue
    #
    # recv_udp_payload = data[56:64]
    # if len(recv_udp_payload) == 0:
    #     print("... which does not contain a UDP payload.")
    #     break
    # elif recv_udp_payload != udp_payload:
    #     print(
    #         f"... which contains a UDP payload {recv_udp_payload} that does not match"
    #     )
    #     continue
    # else:
    #     print("... which contains the right UDP payload!")
    #     break


if __name__ == "__main__":
    main()
