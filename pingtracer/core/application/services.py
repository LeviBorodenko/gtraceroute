import asyncio
from dataclasses import dataclass, field

from pingtracer.core.transport.entities import ProbeReply, ProbeRequest
from pingtracer.core.transport.services import ICMPReplyWatcher, RequestDispatcher
from pingtracer.core.utils import RTTMonitor


@dataclass
class RouteHop:
    target_ipv4: str

    hop: int
    _found_all_hops: asyncio.Event
    n_successful_measurements: int = 0
    n_failed_measurements: int = 0

    hop_ipv4: str | None = None
    rtt: RTTMonitor = field(default_factory=lambda: RTTMonitor())

    def __eq__(self, __value: "RouteHop") -> bool:
        return (
            self.hop == __value.hop
            and self.target_ipv4 == __value.target_ipv4
            and self.rtt.exp_avg == __value.rtt.exp_avg
        )

    def update_rtt_estimates(self, request: ProbeRequest, reply: ProbeReply):
        rtt = reply.receive_ts - request.dispatch_ts
        self.rtt.observe(1000 * rtt)
        self.hop_ipv4 = reply.ipv4_header.source_ip

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
        timeout: int = 1,
    ):
        try:
            async with asyncio.timeout(timeout):
                request = ProbeRequest(ipv4=self.target_ipv4, ttl=self.hop)
                await dispatcher.dispatch(request)

                reply = None
                while reply is None:
                    reply = self.poll_for_matching_reply(request, reply_watcher)
                    await asyncio.sleep(0.25)

                self.update_rtt_estimates(request, reply)

                if not self._found_all_hops.is_set() and (
                    reply.icmp_header.type == 3
                    or reply.ipv4_header.source_ip == self.target_ipv4
                ):
                    self._found_all_hops.set()
        except TimeoutError:
            self.n_failed_measurements += 1
        self.n_successful_measurements += 1
