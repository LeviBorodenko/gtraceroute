from textual.app import App, ComposeResult
from textual.containers import Container
from textual.css.query import NoMatches
from textual.widgets import LoadingIndicator
from pingtracer.tui.widgets.target_input import TargetInput
from pingtracer.tui.widgets.target_list import TargetList
from pingtracer.tui.widgets.tracer_widget import TracerWidget


class PingTracer(App):
    CSS_PATH = "app.css"

    async def on_target_input_submitted(self, event: TargetInput.Submitted):
        try:
            self.query_one(TracerWidget).remove()
        except NoMatches:
            pass
        try:
            self.query_one("#tracer-widget-placeholder").remove()
        except NoMatches:
            pass
        new_tracer_widget = TracerWidget(event.target_ipv4, id="tracer-widget")
        await self.query_one("#content-container", Container).mount(new_tracer_widget)

        self.query_one(TargetList).add_target("test", event.target_ipv4)

    def compose(self) -> ComposeResult:
        with Container(id="app-container"):
            yield TargetInput(id="domain-input")
            with Container(id="content-container"):
                yield TargetList()
                yield LoadingIndicator(id="tracer-widget-placeholder")


if __name__ == "__main__":
    app = PingTracer()
    app.run()
