from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.message import Message
from pingtracer.core.application.services import RouteHop
from pingtracer.core.tracer import Tracer
from pingtracer.core.utils import get_ipv4
from textual.widgets import DataTable, Footer, Header, Static


tracer = Tracer()


class TraceTable(Widget):
    hops: reactive[list[RouteHop]] = reactive([], layout=True, always_update=True)

    COLUMNS = (
        "Hop",
        "IPv4",
        "RTT (mean)",
        "RTT (current)",
        "RTT (std)",
        "packets sent",
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

    @staticmethod
    def get_index_from_hop(hop_number: int, hops: list[RouteHop]) -> int:
        for idx, hop in enumerate(hops):
            if hop_number == hop.hop:
                return idx
        raise IndexError(f"Cannot find hop #{hop_number} in {hops}!")

    def watch_hops(self, updated_hops: list[RouteHop]):
        updated_rows = TraceTable.get_rows_from_hops(updated_hops)
        cursor_row = self.table.cursor_row
        hover_coords = self.table.hover_coordinate
        self.table.clear()
        for updated_row in updated_rows:
            self.table.add_row(*updated_row, key=updated_row[0])
        self.table.sort("hop")
        self.table.move_cursor(row=cursor_row)
        self.table.hover_coordinate = hover_coords

    class HopSelected(Message):
        hop: int

        def __init__(self, hop: int) -> None:
            self.hop = hop
            super().__init__()

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        hop = self.table.get_row(event.row_key)[0]
        self.post_message(self.HopSelected(hop))

    def compose(self) -> ComposeResult:
        self.table = DataTable()
        self.table.cursor_type = "row"
        with VerticalScroll():
            yield self.table

    def on_mount(self):
        self.table.add_column(self.COLUMNS[0], key="hop")
        self.table.add_columns(*self.COLUMNS[1:])


class PingTracer(App):
    CSS_PATH = "app.css"

    @work
    async def start_tracing(self, host: str):
        target_ipv4 = get_ipv4(host)
        self.polling_timer = self.set_interval(0.5, self.poll_tracing_status)
        await tracer.trace_route(target_ipv4, return_early=False)

    async def poll_tracing_status(self):
        self.trace_table.hops = tracer.hops

    async def on_mount(self):
        self.start_tracing("google.com")

    # def on_trace_table_hop_selected(self, event: TraceTable.HopSelected):
    #     self.static.update(f"Selected Hop #{event.hop}")

    def compose(self) -> ComposeResult:
        self.trace_table = TraceTable()
        self.static = Static()
        yield Header(show_clock=True)
        with Container():
            yield Static("Select", id="select-wrapper")
            yield self.trace_table
            yield Static("Plot", id="plot-wrapper")
        yield Footer()


if __name__ == "__main__":
    app = PingTracer()
    app.run()
