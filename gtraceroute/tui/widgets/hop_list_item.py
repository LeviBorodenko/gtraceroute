from time import time
from typing import ClassVar
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from gtraceroute.core.application.services import RouteHop
from gtraceroute.tui.widgets.hop_sparkline import HopSparkline


class HopListItem(Widget):
    hop: reactive[RouteHop]

    def __init__(
        self,
        hop: RouteHop,
        *children: Widget,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        self.hop = hop
        super().__init__(
            *children, name=name, id=id, classes=classes, disabled=disabled
        )

    CONNECTION_TIMEOUT_S: ClassVar[float] = 1

    def action_update_hop(self, new_hop: RouteHop):
        self.hop_statistic.update(HopListItem.statistic_str_from_hop(new_hop))
        self.sparkline.update(new_hop)
        time_last_ob = new_hop.rtt.time_last_ob or 0
        self.set_class(
            is_timeout := time() - time_last_ob > HopListItem.CONNECTION_TIMEOUT_S,
            "warn-state",
        )
        self.border_title = "Package Loss" if is_timeout else None

    @staticmethod
    def statistic_str_from_hop(hop: RouteHop) -> str:
        avg_rtt = hop.rtt.exp_avg or float("inf")
        std_rtt = hop.rtt.exp_std or 0
        packet_loss = (
            100
            * hop.n_failed_measurements
            / (hop.n_failed_measurements + hop.n_successful_measurements)
        )
        hop_ipv4 = hop.hop_ipv4 or "xxx.xxx.xxx.xxx"

        first_col = f"#{hop.hop}@{hop_ipv4:<15}"
        second_col = f"RTT: {avg_rtt:.2f}ms +/- {std_rtt:.2f}"
        third_col = f"Loss: {packet_loss:.2f}%"
        return f"{first_col:>19} | {second_col:<23} | {third_col:<13}"

    def compose(self) -> ComposeResult:
        self.hop_statistic = Static(
            HopListItem.statistic_str_from_hop(self.hop), shrink=True
        )
        yield self.hop_statistic
        self.sparkline = HopSparkline(self.hop)
        yield self.sparkline
