from collections import deque
import socket
import asyncio
from typing import Deque

from pingtracer.core.transport.entities import ProbeReply, ProbeRequest
from pingtracer.core.utils import async_recv, async_sendto, await_or_cancel_on_event


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

    async def await_probe_reply(self, stop_awaiting_bytes: asyncio.Event):
        probe_bytes = await await_or_cancel_on_event(
            async_recv(self.icmp_socket), stop_awaiting_bytes
        )
        if probe_bytes is None:
            return

        reply = ProbeReply.from_bytes(probe_bytes)
        self.reply_buffer.append(reply)

    async def icmp_fetching(self, stop_fetching: asyncio.Event):
        while not stop_fetching.is_set():
            await self.await_probe_reply(stop_fetching)


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
