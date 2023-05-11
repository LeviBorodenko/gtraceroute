import asyncio
from textual.app import App, ComposeResult
from textual.reactive import reactive
import textual.widgets as widgets
from pingtracer.core.tracer import Tracer
from pingtracer.core.utils import get_ipv4


tracer = Tracer()


class PingTracer(App):
    TITLE = "PingTracer v0"
    SUB_TITLE = "LOOOL"
    target_host = reactive("google.com")

    def compose(self) -> ComposeResult:
        yield widgets.Header(show_clock=True)
        yield widgets.Input(placeholder="Trace host")
        yield widgets.DataTable(
            id="trace-result",
        )

    def on_mount(self):
        self.query_one(widgets.DataTable).add_columns(*tracer.trace_status_table[0])

    async def on_input_submitted(self):
        self.query_one("Input", widgets.Input).disabled = True
        target_ipv4 = get_ipv4(self.target_host)
        self.sub_title = f"Tracing {target_ipv4}"
        self.tracer_task = asyncio.create_task(tracer.trace_route(target_ipv4))

    async def on_key(self):
        table = self.query_one(widgets.DataTable)
        table = table.clear()
        table.add_rows(tracer.trace_status_table[1:])
        if tracer._found_all_hops.is_set():
            self.query_one("#trace-result", widgets.DataTable).styles.border = (
                "heavy",
                "green",
            )


if __name__ == "__main__":
    app = PingTracer()
    app.run()
