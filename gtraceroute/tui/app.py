from textual.app import App, ComposeResult
from textual.containers import Container
from textual.css.query import NoMatches
from textual.widgets import Input, LoadingIndicator
from gtraceroute.tui.widgets.target_input import TargetInput
from gtraceroute.tui.widgets.target_list import TargetList
from gtraceroute.tui.widgets.tracer_widget import TracerWidget


class gTraceroute(App):
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

        sidebar = self.query_one(TargetList)
        sidebar.add_target(event.target_name, event.target_ipv4)

    async def on_option_list_option_selected(self, event: TargetList.OptionSelected):
        target_ipv4 = event.option.id

        self.query_one(TracerWidget).remove()
        new_tracer_widget = TracerWidget(str(target_ipv4), id="tracer-widget")
        self.query_one("TargetInput Input", Input).value = str(target_ipv4)
        await self.query_one("#content-container", Container).mount(new_tracer_widget)

    def compose(self) -> ComposeResult:
        with Container(id="app-container"):
            yield TargetInput(id="domain-input")
            with Container(id="content-container"):
                yield TargetList()
                yield LoadingIndicator(id="tracer-widget-placeholder")


if __name__ == "__main__":
    app = gTraceroute()
    app.run()
