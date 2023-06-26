from textual import work
from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll, Vertical, Container, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header, Placeholder
from pingtracer.core.tracer import Tracer
from pingtracer.core.transport.services import ICMPReplyWatcher, RequestDispatcher
from pingtracer.tui.widgets.hop_list import HopList
from pingtracer.tui.widgets.search import DomainNameInput

dispatcher = RequestDispatcher()
icmp_watcher = ICMPReplyWatcher()


class PingTracer(App):
    CSS_PATH = "app.css"
    target_ipv4 = reactive(None)
    hop_list: HopList = HopList()
    domain_input = DomainNameInput(id="domain-input")
    tracer: Tracer

    def watch_target_ipv4(self, new_target_ipv4: str):
        if new_target_ipv4 is not None:
            self.start_tracing(new_target_ipv4)

    @work(exclusive=True)
    async def start_tracing(self, target_ipv4: str):
        self.tracer = Tracer(dispatcher, icmp_watcher)
        self.polling_timer = self.set_interval(0.5, self.poll_tracing_status)
        await self.tracer.trace_route(target_ipv4, return_early=False)

    async def poll_tracing_status(self):
        self.hop_list.hops = self.tracer.hops
        # if self.tracer._found_all_hops.is_set():
        #     self.polling_timer.stop()

    # def on_trace_table_hop_selected(self, event: TraceTable.HopSelected):
    #     hop_idx = min(max(0, event.hop - 1), len(self.hop_list.hops) - 1)
    #     hop = self.hop_list.hops[hop_idx]
    #     self.query_one("#chart-container", Container).mount(
    #         HopSparkline(hop, summary_function=max)
    #     )

    def on_domain_name_input_submitted(self, event: DomainNameInput.Submitted):
        self.target_ipv4 = event.target_ipv4

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="app-container"):
            yield Placeholder(id="sidebar")
            with Container(id="content-container"):
                yield self.domain_input
                yield self.hop_list
        yield Footer()


if __name__ == "__main__":
    app = PingTracer()
    app.run()
