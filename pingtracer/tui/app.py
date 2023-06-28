from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll, Vertical, Container, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import Footer, Header, LoadingIndicator, Placeholder
from pingtracer.core.transport.services import ICMPReplyWatcher, RequestDispatcher
from pingtracer.tui.widgets.search import DomainNameInput
from pingtracer.tui.widgets.tracer_widget import TracerWidget

dispatcher = RequestDispatcher()
icmp_watcher = ICMPReplyWatcher()


class PingTracer(App):
    CSS_PATH = "app.css"

    async def on_domain_name_input_submitted(self, event: DomainNameInput.Submitted):
        try:
            self.query_one(TracerWidget).remove()
        except NoMatches:
            pass
        try:
            self.query_one("#tracer-widget-placeholder").remove()
        except NoMatches:
            pass
        new_tracer_widget = TracerWidget(event.target_ipv4, id="tracer-widget")
        await self.query_one("#app-container", Vertical).mount(new_tracer_widget)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="app-container"):
            yield DomainNameInput(id="domain-input")
            yield LoadingIndicator(id="tracer-widget-placeholder")


if __name__ == "__main__":
    app = PingTracer()
    app.run()
