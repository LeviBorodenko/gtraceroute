from textual import work
from textual.app import ComposeResult
from textual.widget import Widget
from gtraceroute.core.tracer import Tracer
from gtraceroute.tui.widgets.hop_list import HopList
from gtraceroute.tui import dispatcher, icmp_watcher


class TracerWidget(Widget):
    hop_list: HopList
    tracer: Tracer

    def __init__(
        self,
        target_ipv4: str,
        polling_rate: float = 0.5,
        *children: Widget,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            *children, name=name, id=id, classes=classes, disabled=disabled
        )
        self.start_tracing(target_ipv4, polling_rate)

    @work(exclusive=True)
    async def start_tracing(self, target_ipv4: str, polling_rate: float):
        self.tracer = Tracer(dispatcher, icmp_watcher)
        self.polling_timer = self.set_interval(polling_rate, self.poll_tracing_status)
        await self.tracer.trace_route(target_ipv4, return_early=False)

    async def poll_tracing_status(self):
        self.hop_list.hops = self.tracer.hops

    def on_unmount(self):
        self.polling_timer.stop()

    def compose(self) -> ComposeResult:
        self.hop_list = HopList()
        yield self.hop_list
