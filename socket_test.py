from collections import deque
import socket
import time
import struct
import asyncio
from random import randbytes
from dataclasses import dataclass, field
from typing import AsyncGenerator, Deque

PROBE_BASE_PORT = 33434
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
    request_creation_ts: float = field(default_factory=lambda: time.time())
    dispatch_ts: float = field(default_factory=lambda: time.time())

    def update_dispatch_ts(self):
        self.dispatch_ts = time.time()

    @staticmethod
    def matches(request: "ProbeRequest", reply: "ProbeReply") -> bool:
        if reply.ref_udp_payload == request.udp_payload:
            return True
        elif (
            request.ipv4 == reply.ref_ipv4_header.dst_ip
            and request.port == reply.ref_udp_header.dst_port
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


async def async_recv(sock: socket.socket) -> bytes:
    return await asyncio.get_event_loop().sock_recv(sock, 1024)


async def async_sendto(sock: socket.socket, udp_payload: bytes, addr: tuple[str, int]):
    await asyncio.get_event_loop().sock_sendto(sock, udp_payload, addr)


class ICMPReplyWatcher:
    icmp_socket: socket.socket
    dispatched_probe_requests: list[ProbeRequest] = []

    reply_buffer: Deque[ProbeReply]

    def __init__(self, buffer_size: int = 100) -> None:
        self.reply_buffer = deque([], maxlen=buffer_size)
        icmp_socket = socket.socket(
            socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("icmp")
        )
        icmp_socket.setblocking(False)
        self.icmp_socket = icmp_socket

    async def await_probe_reply(self):
        probe_bytes = await async_recv(self.icmp_socket)
        probe_reply = ProbeReply.from_bytes(probe_bytes)
        self.reply_buffer.append(probe_reply)
        print(f"Received {probe_reply}")

    async def icmp_fetching(self):
        print("Beginning icmp fetching.")
        while True:
            await self.await_probe_reply()


class ProbeDispatcher:
    udp_socket: socket.socket

    def __init__(self) -> None:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setblocking(False)
        self.udp_socket = udp_socket

    async def dispatch(self, probe: ProbeRequest):
        self.udp_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, probe.ttl)
        probe.update_dispatch_ts()
        await async_sendto(self.udp_socket, probe.udp_payload, (probe.ipv4, probe.port))


class RouteHop:
    target_ipv4: str
    hop: int
    estimated_rtt: float | None = None

    dispatcher: ProbeDispatcher
    reply_watcher: ICMPReplyWatcher

    def __init__(
        self,
        target_ipv4: str,
        hop: int,
        dispatcher: ProbeDispatcher,
        reply_watcher: ICMPReplyWatcher,
    ) -> None:
        self.target_ipv4 = target_ipv4
        self.hop = hop
        self.dispatcher = dispatcher
        self.reply_watcher = reply_watcher

    def poll_for_matching_reply(self, probe: ProbeRequest) -> ProbeReply | None:
        match = None
        for reply in self.reply_watcher.reply_buffer:
            if ProbeRequest.matches(probe, reply):
                match = reply

        # remove from buffer
        if match is not None:
            self.reply_watcher.reply_buffer.remove(match)

        return match

    async def measure(self):
        probe = ProbeRequest(
            ipv4=self.target_ipv4, ttl=self.hop, port=PROBE_BASE_PORT + self.hop
        )
        await self.dispatcher.dispatch(probe)

        probe_reply = None
        while probe_reply is None:
            probe_reply = self.poll_for_matching_reply(probe)
            await asyncio.sleep(0.25)

        rtt = probe_reply.receive_ts - probe.dispatch_ts
        print(f"[HOP{self.hop}, {rtt:.3f}ms]")
        print(self.reply_watcher.reply_buffer)
        self.estimated_rtt = rtt


async def async_main():

    dispatcher = ProbeDispatcher()
    reply_watcher = ICMPReplyWatcher()
    target_ipv4 = get_ipv4("kkos.net")
    hops = [
        RouteHop(target_ipv4, hop, dispatcher, reply_watcher) for hop in range(1, 20)
    ]
    async with asyncio.TaskGroup() as bg_tasks:
        bg_tasks.create_task(reply_watcher.icmp_fetching())
        for hop in hops:
            bg_tasks.create_task(hop.measure())


if __name__ == "__main__":
    asyncio.run(async_main(), debug=True)
