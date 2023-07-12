from collections import deque
import socket
import asyncio
from typing import Deque

from gtraceroute.core.transport.entities import ProbeReply, ProbeRequest
from gtraceroute.core.utils import async_recv, async_sendto, await_or_cancel_on_event


class RawSocketPermissionError(Exception):
    def __init__(self):
        super().__init__(
            """
     ERROR: Permission Denied for Creating Raw Socket.

     This application requires a raw socket in order to listen for ICMP (Internet Control Message Protocol)
     packets, which this tool uses probe intermediate routes. The creation of a raw socket is a
     privileged operation typically restricted to superuser accounts due to its potential for misuse.

     If you trust the source of this application and want to proceed, this issue can be resolved by
     running the following command:

     sudo setcap cap_net_raw+ep $(realpath $(which python3))

     What does this command do?
     It uses 'setcap' to assign the 'cap_net_raw' capability to your Python interpreter.

     - 'sudo' is a command that allows programs to be run as the superuser, or another user.
     - 'setcap' is a utility that sets file capabilities. Capabilities are a subdivision of root's
     powers into a larger set of more narrowly focused privileges.
     - 'cap_net_raw' allows the application to use network protocols that require raw sockets like ICMP.
     - '+ep' is the action to be performed. 'e' stands for Effective
     (making it part of the Permitted set that the program can use) and 'p' for Permitted
     (adding this capability to the inheritable set after an exec()).
     - 'realpath' and 'which' are used to get the real path to your Python interpreter.

     Please be aware that giving such permissions has security implications, and should be done after
     understanding and trusting the source of the application. If you are concerned about
     the integrity or security of this tool, remember that its code is open source, and you are
     encouraged to review it before granting these permissions.
         """
        )


class ICMPReplyWatcher:
    icmp_socket: socket.socket
    reply_buffer: Deque[ProbeReply]

    def __init__(self, buffer_size: int = 100) -> None:
        self.reply_buffer = deque([], maxlen=buffer_size)

        try:
            icmp_socket = socket.socket(
                socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("icmp")
            )
        except PermissionError:
            raise RawSocketPermissionError()
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
