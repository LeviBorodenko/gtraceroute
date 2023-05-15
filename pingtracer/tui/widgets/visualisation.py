from textual.containers import Container
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.message import Message
from pingtracer.core.application.services import RouteHop
from textual.widgets import DataTable


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

    def __init__(self, *args, **kwargs):
        self.table = DataTable(*args, **kwargs)
        super().__init__()

    def watch_hops(self, old_hops: list[RouteHop], updated_hops: list[RouteHop]):
        updated_rows = TraceTable.get_rows_from_hops(updated_hops)
        cursor_row = self.table.cursor_row
        hover_coords = self.table.hover_coordinate
        self.table.clear()
        for updated_row in updated_rows:
            self.table.add_row(*updated_row, key=updated_row[0])
        self.table.sort("hop")
        if (
            len(old_hops) > 0
            and len(updated_hops) > 0
            and old_hops[0].target_ipv4 == updated_hops[0].target_ipv4
        ):
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
        self.table.styles.width = "auto"
        self.table.cursor_type = "row"
        with Container() as c:
            yield self.table
            c.styles.align = ("center", "middle")
            c.styles.height = "auto"

    def on_mount(self):
        self.table.add_column(self.COLUMNS[0], key="hop")
        self.table.add_columns(*self.COLUMNS[1:])
