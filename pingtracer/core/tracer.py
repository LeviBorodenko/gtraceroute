import asyncio
from dataclasses import dataclass, field
from pingtracer.core.application.services import RouteHop
from pingtracer.core.transport.services import ICMPReplyWatcher, RequestDispatcher
from pingtracer.core.utils import await_or_cancel_on_event, get_ipv4


@dataclass
class Tracer:
    target_ipv4: str

    taskgroup: asyncio.TaskGroup

    dispatcher: RequestDispatcher
    reply_watcher: ICMPReplyWatcher
    stop_measurement: asyncio.Event = field(default_factory=lambda: asyncio.Event())
    _found_all_hops: asyncio.Event = field(default_factory=lambda: asyncio.Event())
    _hops: list[RouteHop] = field(default_factory=lambda: [])

    @property
    def hops(self) -> list[RouteHop]:
        return [hop for hop in self._hops if hop.hop_ipv4 is not None]

    async def hop_probing(self, hop: int):
        route_hop = RouteHop(self.target_ipv4, hop, self._found_all_hops)
        self._hops.append(route_hop)
        while not self.stop_measurement.is_set():
            await route_hop.measure(self.dispatcher, self.reply_watcher)

    async def analyze_route(self, max_hops: int = 32) -> asyncio.Event:
        self.taskgroup.create_task(
            self.reply_watcher.icmp_fetching(self.stop_measurement)
        )
        for hop in range(1, max_hops + 1):
            if self._found_all_hops.is_set():
                break
            self.taskgroup.create_task(
                await_or_cancel_on_event(self.hop_probing(hop), self.stop_measurement)
            )
            await asyncio.sleep(0.25)
        return self.stop_measurement


async def test_route_tracer():
    dispatcher = RequestDispatcher()
    reply_watcher = ICMPReplyWatcher()
    target_ipv4 = get_ipv4("facebook.com")
    async with asyncio.TaskGroup() as bg_tasks:
        tracer = Tracer(
            target_ipv4,
            bg_tasks,
            dispatcher,
            reply_watcher,
        )
        stop_measurement = await tracer.analyze_route()
        print("****************************")
        await asyncio.sleep(10)
        stop_measurement.set()
        for hop in tracer.hops:
            print(hop)
            print("__________________")


def test_run():
    asyncio.run(test_route_tracer(), debug=True)
