from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container
from pingtracer.core.tracer import Tracer
from pingtracer.core.utils import get_ipv4
from textual.widgets import Footer, Header, Static
from pingtracer.tui.widgets.search import DomainNameInput
from pingtracer.tui.widgets.visualisation import TraceTable

tracer = Tracer()


class PingTracer(App):
    CSS_PATH = "app.css"

    # @work
    # async def start_tracing(self, host: str):
    #     target_ipv4 = get_ipv4(host)
    #     self.polling_timer = self.set_interval(0.5, self.poll_tracing_status)
    #     await tracer.trace_route(target_ipv4, return_early=False)

    # async def poll_tracing_status(self):
    #     self.trace_table.hops = tracer.hops
    #
    # async def on_mount(self):
    #     self.start_tracing("google.com")

    # def on_trace_table_hop_selected(self, event: TraceTable.HopSelected):
    #     self.static.update(f"Selected Hop #{event.hop}")

    def compose(self) -> ComposeResult:
        # self.trace_table = TraceTable()
        yield Header(show_clock=True)
        self.domain_name_input = DomainNameInput()
        yield self.domain_name_input
        yield Footer()


if __name__ == "__main__":
    app = PingTracer()
    app.run()
