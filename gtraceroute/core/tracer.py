import asyncio
from dataclasses import dataclass, field
from gtraceroute.core.application.services import RouteHop
from gtraceroute.core.transport.services import ICMPReplyWatcher, RequestDispatcher
from gtraceroute.core.utils import await_or_cancel_on_event, get_ipv4


@dataclass
class Tracer:
    dispatcher: RequestDispatcher = field(default_factory=lambda: RequestDispatcher())
    reply_watcher: ICMPReplyWatcher = field(default_factory=lambda: ICMPReplyWatcher())
    stop: asyncio.Event = field(default_factory=lambda: asyncio.Event())
    _found_all_hops: asyncio.Event = field(default_factory=lambda: asyncio.Event())
    _hops: list[RouteHop] = field(default_factory=lambda: [])

    @property
    def hops(self) -> list[RouteHop]:
        hops = []
        for hop in self._hops:
            if hop.hop_ipv4 is None:
                continue
            elif hop.hop_ipv4 == hop.target_ipv4:
                hops.append(hop)
                break
            hops.append(hop)

        return hops

    async def hop_probing(self, target_ipv4: str, hop: int):
        route_hop = RouteHop(target_ipv4, hop, self._found_all_hops)
        self._hops.append(route_hop)
        while not self.stop.is_set():
            await route_hop.measure(self.dispatcher, self.reply_watcher)

    async def trace_route(
        self, target_ipv4: str, max_hops: int = 32, return_early: bool = False
    ) -> asyncio.Event:
        self._hops = []
        self.stop.clear()
        self._found_all_hops.clear()

        asyncio.create_task(self.reply_watcher.icmp_fetching(self.stop))
        for hop in range(1, max_hops + 1):
            if self._found_all_hops.is_set():
                break
            asyncio.create_task(
                await_or_cancel_on_event(self.hop_probing(target_ipv4, hop), self.stop)
            )
            await asyncio.sleep(0.5)

        if not return_early:
            await self.stop.wait()
        return self.stop


async def test_route_tracer():
    target_ipv4 = get_ipv4("facebook.com")
    stop_event = asyncio.Event()

    tracer = Tracer(stop=stop_event)
    stop_measurement = await tracer.trace_route(target_ipv4)
    print("****************************")
    await asyncio.sleep(10)
    stop_measurement.set()
    for hop in tracer.hops:
        print(hop)
        print("__________________")


def test_run():
    asyncio.run(test_route_tracer(), debug=True)
