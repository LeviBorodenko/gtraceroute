from collections import deque
import socket
import time
import struct
import asyncio
from random import randbytes
from dataclasses import dataclass, field
from typing import Deque

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
        reply = ProbeReply.from_bytes(probe_bytes)
        self.reply_buffer.append(reply)

    async def icmp_fetching(self, stop_fetching: asyncio.Event):
        while not stop_fetching.is_set():
            await self.await_probe_reply()


class RequestDispatcher:
    udp_socket: socket.socket

    def __init__(self) -> None:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setblocking(False)
        self.udp_socket = udp_socket

    async def dispatch(self, request: ProbeRequest):
        self.udp_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, request.ttl)
        request.update_dispatch_ts()
        await async_sendto(
            self.udp_socket, request.udp_payload, (request.ipv4, request.port)
        )


@dataclass
class RouteHop:
    target_ipv4: str

    hop: int
    found_all_hops: asyncio.Event
    estimated_rtt: float | None = None
    last_known_rtt: float = float("inf")
    n_successful_measurements: int = 0
    n_failed_measurements: int = 0

    hop_ipv4: str | None = None

    def update_stats(self, request: ProbeRequest, reply: ProbeReply):
        rtt = reply.receive_ts - request.dispatch_ts
        self.hop_ipv4 = reply.ipv4_header.source_ip
        self.last_known_rtt = rtt
        self.n_successful_measurements += 1
        self.estimated_rtt = (
            0.875 * self.estimated_rtt + 0.125 * rtt
            if self.estimated_rtt is not None
            else rtt
        )

    @property
    def status(self) -> str:
        if self.estimated_rtt is None or self.hop_ipv4 is None:
            return f"[Hop #{self.hop}] *"
        return (
            f"[Hop #{self.hop}, {self.hop_ipv4}] RTT: {1000*self.estimated_rtt:.3f}ms ({1000*self.last_known_rtt:.3f}ms),"
            f" #Probes: {self.n_successful_measurements}/{self.n_failed_measurements}"
        )

    def poll_for_matching_reply(
        self, request: ProbeRequest, reply_watcher: ICMPReplyWatcher
    ) -> ProbeReply | None:
        match = None
        for reply in reply_watcher.reply_buffer:
            if request.matches(reply):
                match = reply
                break

        # remove from buffer
        if match is not None:
            reply_watcher.reply_buffer.remove(match)

        return match

    async def measure(
        self,
        dispatcher: RequestDispatcher,
        reply_watcher: ICMPReplyWatcher,
        timeout: int = 10,
    ):
        try:
            async with asyncio.timeout(timeout):
                request = ProbeRequest(ipv4=self.target_ipv4, ttl=self.hop)
                await dispatcher.dispatch(request)

                reply = None
                while reply is None:
                    reply = self.poll_for_matching_reply(request, reply_watcher)
                    await asyncio.sleep(0.25)

                self.update_stats(request, reply)

                if not self.found_all_hops.is_set() and (
                    reply.icmp_header.type == 3
                    or reply.ipv4_header.source_ip == self.target_ipv4
                ):
                    self.found_all_hops.set()
        except TimeoutError:
            self.n_failed_measurements += 1


@dataclass
class Route:
    target_ipv4: str

    taskgroup: asyncio.TaskGroup

    dispatcher: RequestDispatcher
    reply_watcher: ICMPReplyWatcher
    stop_measurement: asyncio.Event = field(default_factory=lambda: asyncio.Event())
    found_all_hops: asyncio.Event = field(default_factory=lambda: asyncio.Event())
    hops: list[RouteHop] = field(default_factory=lambda: [])

    async def hop_probing_routine(self, hop: int):
        assert not self.stop_measurement.is_set()
        if self.found_all_hops.is_set():
            print(f"No need for hop #{hop}")
            return

        route_hop = RouteHop(self.target_ipv4, hop, self.found_all_hops)
        self.hops.append(route_hop)
        while not self.stop_measurement.is_set():
            await route_hop.measure(self.dispatcher, self.reply_watcher)

    async def print_status(self):
        while not self.stop_measurement.is_set():
            print("_______________")
            for hop in self.hops:
                print(hop.status)
                if hop.hop_ipv4 == self.target_ipv4:
                    break
            print(f"ROUTE: Buffer size {len(self.reply_watcher.reply_buffer)}")
            print("_______________")
            await asyncio.sleep(1)

    async def analyze_route(self, max_hops: int = 32) -> asyncio.Event:
        self.taskgroup.create_task(
            self.reply_watcher.icmp_fetching(self.stop_measurement)
        )
        self.taskgroup.create_task(self.print_status())
        for hop in range(1, max_hops + 1):
            if self.found_all_hops.is_set() or self.stop_measurement.is_set():
                break
            self.taskgroup.create_task(self.hop_probing_routine(hop))
            await asyncio.sleep(0.25)
        return self.stop_measurement


async def async_main():

    dispatcher = RequestDispatcher()
    reply_watcher = ICMPReplyWatcher()
    target_ipv4 = get_ipv4("facebook.com")
    async with asyncio.TaskGroup() as bg_tasks:
        route = Route(
            target_ipv4,
            bg_tasks,
            dispatcher,
            reply_watcher,
        )
        stop_measurement = await route.analyze_route()
        print("********************************")
        await asyncio.sleep(5)
        stop_measurement.set()


if __name__ == "__main__":
    asyncio.run(async_main(), debug=True)
