import socket
import asyncio

PROBE_BASE_PORT = 33434
PROBE_UDP_PAYLOAD_SIZE = 8


def get_ipv4(host: str) -> str:
    addr_info = socket.getaddrinfo(host, None, socket.AF_INET, proto=socket.SOCK_DGRAM)
    ipv4_info = [info[-1][0] for info in addr_info if info[0] == socket.AF_INET]

    if len(ipv4_info) != 1:
        raise NotImplementedError(f"Cannot extract ipv4 from {host}. Got {addr_info}")
    return ipv4_info[0]


async def async_recv(sock: socket.socket, timeout: int | None = None) -> bytes:
    async with asyncio.timeout(timeout):
        return await asyncio.get_event_loop().sock_recv(sock, 1024)


async def async_sendto(sock: socket.socket, udp_payload: bytes, addr: tuple[str, int]):
    await asyncio.get_event_loop().sock_sendto(sock, udp_payload, addr)


from typing import Optional, Coroutine, TypeVar, Any

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
