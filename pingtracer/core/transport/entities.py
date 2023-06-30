import socket
import time
import struct
from random import randbytes
from dataclasses import dataclass, field

from pingtracer.core.utils import InvalidProbeReplyException

PROBE_BASE_PORT = 33434
PROBE_UDP_PAYLOAD_SIZE = 8


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


@dataclass
class ProbeRequest:
    ipv4: str

    @property
    def ipv4_bytes(self) -> bytes:
        return socket.inet_pton(socket.AF_INET, self.ipv4)

    ttl: int

    @property
    def port(self) -> int:
        return PROBE_BASE_PORT + self.ttl

    udp_payload: bytes = field(
        default_factory=lambda: randbytes(PROBE_UDP_PAYLOAD_SIZE)
    )
    request_creation_ts: float = field(default_factory=lambda: time.time())
    dispatch_ts: float = field(default_factory=lambda: time.time())

    def update_dispatch_ts(self):
        self.dispatch_ts = time.time()

    def matches(self, reply: "ProbeReply") -> bool:
        if reply.ref_udp_payload == self.udp_payload:
            return True
        elif (
            self.ipv4 == reply.ref_ipv4_header.dst_ip
            and self.port == reply.ref_udp_header.dst_port
        ):
            return True
        return False


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
