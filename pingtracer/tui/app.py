import asyncio
from textual import work
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.worker import Worker
from pingtracer.core.application.services import RouteHop
from pingtracer.core.tracer import Tracer
from pingtracer.core.utils import get_ipv4
from textual.widgets import DataTable, Static


tracer = Tracer()


class TraceTable(Widget):
    hops: reactive[list[RouteHop]] = reactive([], layout=True, always_update=True)

    COLUMNS = (
        "Hop",
        "IPv4",
        "RTT (mean) [ms]",
        "RTT (current) [ms]",
        "RTT (std) [ms]",
        "packets send",
        "packet loss (%)",
    )

    @staticmethod
    def get_rows_from_hops(hops: list[RouteHop]) -> list[tuple]:
        rows = []
        for hop in hops:
            row = (
                hop.hop,
                hop.hop_ipv4,
                hop.rtt.exp_avg,
                hop.rtt.buffer[-1],
                hop.rtt.exp_std,
                hop.n_failed_measurements + hop.n_successful_measurements,
                hop.n_failed_measurements
                / (hop.n_failed_measurements + hop.n_successful_measurements),
            )
            rows.append(row)
        return rows

    def watch_hops(self, updated_hops: list[RouteHop]):
        updates_rows = TraceTable.get_rows_from_hops(updated_hops)
        self.table.clear()
        self.table.add_rows(updates_rows)

    def compose(self) -> ComposeResult:
        self.table = DataTable()
        self.table.cursor_type = "row"
        yield self.table

    def on_mount(self):
        self.table.add_columns(*self.COLUMNS)


class PingTracer(App):
    @work
    async def start_tracing(self, host: str):
        target_ipv4 = get_ipv4(host)
        self.polling_timer = self.set_interval(0.5, self.poll_tracing_status)
        await tracer.trace_route(target_ipv4, return_early=False)

    async def poll_tracing_status(self):
        self.trace_table.hops = tracer.hops

    async def on_mount(self):
        self.start_tracing("google.com")

    def compose(self) -> ComposeResult:
        self.trace_table = TraceTable()
        self.static = Static()
        yield self.trace_table
        yield self.static


if __name__ == "__main__":
    app = PingTracer()
    app.run()
