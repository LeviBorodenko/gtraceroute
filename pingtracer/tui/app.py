from textual import work
from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll, Vertical, Container, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header, Placeholder
from pingtracer.core.transport.services import ICMPReplyWatcher, RequestDispatcher
from pingtracer.tui.widgets.search import DomainNameInput
from pingtracer.tui.widgets.tracer_widget import TracerWidget

dispatcher = RequestDispatcher()
icmp_watcher = ICMPReplyWatcher()


class PingTracer(App):
    CSS_PATH = "app.css"

    async def on_domain_name_input_submitted(self, event: DomainNameInput.Submitted):
        self.query_one("Placeholder", Placeholder).remove()
        new_tracer_widget = TracerWidget(event.target_ipv4, id="tracer-widget")
        await self.query_one("#app-container", Vertical).mount(new_tracer_widget)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="app-container"):
            yield DomainNameInput(id="domain-input")
            yield Placeholder()


if __name__ == "__main__":
    app = PingTracer()
    app.run()
