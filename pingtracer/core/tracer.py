import asyncio
from dataclasses import dataclass, field
from pingtracer.core.application.services import RouteHop
from pingtracer.core.transport.services import ICMPReplyWatcher, RequestDispatcher
from pingtracer.core.utils import await_or_cancel_on_event, get_ipv4


@dataclass
class Tracer:
    target_ipv4: str

    dispatcher: RequestDispatcher = field(default_factory=lambda: RequestDispatcher())
    reply_watcher: ICMPReplyWatcher = field(default_factory=lambda: ICMPReplyWatcher())
    stop: asyncio.Event = field(default_factory=lambda: asyncio.Event())
    _found_all_hops: asyncio.Event = field(default_factory=lambda: asyncio.Event())
    _hops: list[RouteHop] = field(default_factory=lambda: [])

    @property
    def hops(self) -> list[RouteHop]:
        return [hop for hop in self._hops if hop.hop_ipv4 is not None]

    async def hop_probing(self, hop: int):
        route_hop = RouteHop(self.target_ipv4, hop, self._found_all_hops)
        self._hops.append(route_hop)
        while not self.stop.is_set():
            await route_hop.measure(self.dispatcher, self.reply_watcher)

    async def trace_route(self, max_hops: int = 32) -> asyncio.Event:
        asyncio.create_task(self.reply_watcher.icmp_fetching(self.stop))
        for hop in range(1, max_hops + 1):
            if self._found_all_hops.is_set():
                break
            asyncio.create_task(
                await_or_cancel_on_event(self.hop_probing(hop), self.stop)
            )
            await asyncio.sleep(0.25)
        return self.stop


async def test_route_tracer():
    target_ipv4 = get_ipv4("facebook.com")
    stop_event = asyncio.Event()

    tracer = Tracer(target_ipv4, stop=stop_event)
    stop_measurement = await tracer.trace_route()
    print("****************************")
    await asyncio.sleep(10)
    stop_measurement.set()
    for hop in tracer.hops:
        print(hop)
        print("__________________")


def test_run():
    asyncio.run(test_route_tracer(), debug=True)
