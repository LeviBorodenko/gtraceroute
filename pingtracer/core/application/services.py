import asyncio
from dataclasses import dataclass

from pingtracer.core.transport.entities import ProbeReply, ProbeRequest
from pingtracer.core.transport.services import ICMPReplyWatcher, RequestDispatcher


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
