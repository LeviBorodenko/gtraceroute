import asyncio
from textual.app import App, ComposeResult
import textual.widgets as widgets
from pingtracer.core.tracer import Tracer
from pingtracer.core.utils import get_ipv4


tracer = Tracer(get_ipv4("google.com"))


class PingTracer(App):
    def compose(self) -> ComposeResult:
        yield widgets.Header(show_clock=True)
        yield widgets.Pretty([], id="pretty")

    async def on_mount(self):
        self.tracer_task = asyncio.create_task(tracer.trace_route())

    def on_key(self):
        self.query_one("#pretty").update(tracer.hops)


if __name__ == "__main__":
    app = PingTracer()
    app.run()
