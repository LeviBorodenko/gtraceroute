from collections import deque
from dataclasses import dataclass, field
from functools import cache
import socket
import asyncio
from time import time
from typing import Optional, Coroutine, TypeVar, Any
import ipaddress

PROBE_BASE_PORT = 33434
PROBE_UDP_PAYLOAD_SIZE = 8


def is_ipv4_address(string: str) -> bool:
    try:
        ipaddress.IPv4Address(string)
        return True
    except ipaddress.AddressValueError:
        return False


@cache
def get_ipv4(host: str) -> str:
    try:
        addr_info = socket.getaddrinfo(
            host, None, socket.AF_INET, proto=socket.SOCK_DGRAM
        )
        ipv4_info = [info[-1][0] for info in addr_info if info[0] == socket.AF_INET]
        return ipv4_info[0]
    except Exception:
        raise InvalidAddressException(f"No IPv4 for {host}.")


async def async_recv(sock: socket.socket, timeout: int | None = None) -> bytes:
    async with asyncio.timeout(timeout):
        return await asyncio.get_event_loop().sock_recv(sock, 1024)


async def async_sendto(sock: socket.socket, udp_payload: bytes, addr: tuple[str, int]):
    await asyncio.get_event_loop().sock_sendto(sock, udp_payload, addr)


T = TypeVar("T")


async def await_or_cancel_on_event(
    coro: Coroutine[Any, Any, T], event: asyncio.Event
) -> Optional[T]:
    async def _await_event():
        await event.wait()
        return None

    task = asyncio.create_task(coro)
    done, pending = await asyncio.wait(
        {task, asyncio.create_task(_await_event())}, return_when=asyncio.FIRST_COMPLETED
    )

    for pending_task in pending:
        pending_task.cancel()

    result = await asyncio.gather(*done, return_exceptions=True)
    return result[0]


class InvalidProbeReplyException(Exception):
    pass


class InvalidAddressException(Exception):
    pass


@dataclass
class RTTMonitor:
    ALPHA: float = 0.125
    BETA: float = 0.25
    buffer: deque[float] = field(default_factory=lambda: deque([0] * 25, 100))
    exp_avg: float | None = None
    exp_std: float | None = None
    no_obs: bool = True
    time_last_ob: float | None = None

    def observe(self, rtt: float):
        self.time_last_ob = time()
        self.no_obs = False
        self.buffer.append(rtt)
        self.exp_avg = (
            (1 - RTTMonitor.ALPHA) * self.exp_avg + RTTMonitor.ALPHA * rtt
            if self.exp_avg is not None
            else rtt
        )
        diff = abs(self.exp_avg - rtt)
        self.exp_std = (
            (1 - RTTMonitor.BETA) * self.exp_std + RTTMonitor.BETA * diff
            if self.exp_std is not None
            else diff
        )
