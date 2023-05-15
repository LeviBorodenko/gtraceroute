from textual import work
from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll, Vertical, Container, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header
from pingtracer.core.tracer import Tracer
from pingtracer.tui.widgets.search import DomainNameInput
from pingtracer.tui.widgets.visualisation import TraceTable

tracer = Tracer()


class PingTracer(App):
    CSS_PATH = "app.css"
    target_ipv4 = reactive(None)
    trace_table = TraceTable(id="trace-table")
    domain_input = DomainNameInput(id="domain-input")

    def watch_target_ipv4(self, _, new_target_ipv4: str):
        self.start_tracing(new_target_ipv4)

    @work(exclusive=True)
    async def start_tracing(self, target_ipv4: str):
        self.polling_timer = self.set_interval(0.5, self.poll_tracing_status)
        await tracer.trace_route(target_ipv4, return_early=False)

    async def poll_tracing_status(self):
        self.trace_table.hops = tracer.hops

    #
    # async def on_mount(self):
    #     self.start_tracing("google.com")

    # def on_trace_table_hop_selected(self, event: TraceTable.HopSelected):
    #     self.static.update(f"Selected Hop #{event.hop}")

    def on_domain_name_input_submitted(self, event: DomainNameInput.Submitted):
        self.target_ipv4 = event.target_ipv4

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="trace-container"):
            yield self.domain_input
            yield self.trace_table
        yield Footer()


if __name__ == "__main__":
    app = PingTracer()
    app.run()
