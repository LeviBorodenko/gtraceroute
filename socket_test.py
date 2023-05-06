import enum
import socket
import time
import struct
import asyncio
from random import randbytes
from dataclasses import dataclass, field
from typing import AsyncGenerator

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
    NOT_DISPATCHED = 0
    DISPATCHED = 1
    SUCCESSFUL = 2
    FAILED = 3


@dataclass
class ProbeRequest:
    ipv4: str

    @property
    def ipv4_bytes(self) -> bytes:
        return socket.inet_pton(socket.AF_INET, self.ipv4)

    ttl: int
    port: int = PROBE_BASE_PORT
    udp_payload: bytes = field(
        default_factory=lambda: randbytes(PROBE_UDP_PAYLOAD_SIZE)
    )
    probe_request_creation_ts: float = field(default_factory=lambda: time.time())
    status: ProbeStatus = ProbeStatus.NOT_DISPATCHED
    probe_dispatch_ts: float | None = None

    @staticmethod
    def generate_ttl_sweep(host: str, max_ttl: int = 16) -> list["ProbeRequest"]:
        sweep = []
        for i in range(1, max_ttl + 1):
            sweep.append(ProbeRequest(get_ipv4(host), i))
        return sweep


class RouteHop:
    target_ipv4: str
    hop: int
    estimated_rtt: float | None = None

    def __init__(self, target_ipv4: str, hop: int) -> None:
        self.target_ipv4 = target_ipv4
        self.hop = hop


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


async def async_recv(sock: socket.socket) -> bytes:
    data = await asyncio.get_event_loop().sock_recv(sock, 1024)
    return data


async def async_sendto(sock, udp_payload: bytes, addr: tuple[str, int]):
    await asyncio.get_event_loop().sock_sendto(sock, udp_payload, addr)


class ICMPReplyWatcher:
    icmp_socket: socket.socket
    dispatched_probe_requests: list[ProbeRequest] = []

    def __init__(self, timeout: int = 5) -> None:
        icmp_socket = socket.socket(
            socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("icmp")
        )
        icmp_socket.setblocking(False)
        icmp_socket.settimeout(timeout)
        self.icmp_socket = icmp_socket

    async def probe_reply_stream(self) -> AsyncGenerator[ProbeReply, None]:
        while True:
            packet_bytes = await async_recv(self.icmp_socket)
            yield ProbeReply.from_bytes(packet_bytes)


class ProbeDispatcher:
    udp_socket: socket.socket

    def __init__(self) -> None:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setblocking(False)
        self.udp_socket = udp_socket

    async def dispatch(self, probe: ProbeRequest):
        self.udp_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, probe.ttl)
        await async_sendto(self.udp_socket, probe.udp_payload, (probe.ipv4, probe.port))


async def async_main():

    probe_dispatcher = ProbeDispatcher()
    reply_watcher = ICMPReplyWatcher(5)
    sweep = ProbeRequest.generate_ttl_sweep("kkos.net")
    for probe in sweep:
        await probe_dispatcher.dispatch(probe)

    async for reply in reply_watcher.probe_reply_stream():
        print(reply)


# def main():
#     target_ipv4 = get_ipv4("google.com")
#     udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#
#     ICMP_PROTO = socket.getprotobyname("icmp")
#     icmp_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, ICMP_PROTO)
#     icmp_socket.settimeout(5)
#
#     sweep = ProbeRequest.generate_ttl_sweep(target_ipv4, 12)
#
#     for probe in sweep:
#         udp_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, probe.ttl)
#         time_bs = time.time()
#         udp_socket.sendto(probe.udp_payload, (probe.ipv4, probe.port))
#         probe.status = ProbeStatus.DISPATCHED
#         probe.probe_dispatch_ts = time_bs
#
#     while True:
#         try:
#             data = icmp_socket.recv(1024)
#             probe_reply = ProbeReply.from_bytes(data)
#             print(probe_reply)
#             print("_______________________")
#         except socket.timeout:
#             print("No ICMP packet arrived before timeout. Stopping sweep.")
#             break
#         except InvalidProbeReplyException as e:
#             raise e


if __name__ == "__main__":
    asyncio.run(async_main())
