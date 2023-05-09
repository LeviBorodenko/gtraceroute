import asyncio
from dataclasses import asdict, dataclass, field
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
    found_all_hops: asyncio.Event = field(default_factory=lambda: asyncio.Event())
    hops: list[RouteHop] = field(default_factory=lambda: [])

    async def hop_probing_routine(self, hop: int):
        route_hop = RouteHop(self.target_ipv4, hop, self.found_all_hops)
        self.hops.append(route_hop)
        while not self.stop_measurement.is_set():
            await route_hop.measure(self.dispatcher, self.reply_watcher)

    async def analyze_route(self, max_hops: int = 32) -> asyncio.Event:
        self.taskgroup.create_task(
            self.reply_watcher.icmp_fetching(self.stop_measurement)
        )
        for hop in range(1, max_hops + 1):
            if self.found_all_hops.is_set():
                break
            self.taskgroup.create_task(
                await_or_cancel_on_event(
                    self.hop_probing_routine(hop), self.stop_measurement
                )
            )
            await asyncio.sleep(0.25)
        return self.stop_measurement


async def test_route_tracer():
    dispatcher = RequestDispatcher()
    reply_watcher = ICMPReplyWatcher()
    target_ipv4 = get_ipv4("facebook.com")
    async with asyncio.TaskGroup() as bg_tasks:
        route = Tracer(
            target_ipv4,
            bg_tasks,
            dispatcher,
            reply_watcher,
        )
        stop_measurement = await route.analyze_route()
        stop_measurement.set()
        for hop in route.hops:
            print(hop)


def test_run():
    asyncio.run(test_route_tracer(), debug=True)
