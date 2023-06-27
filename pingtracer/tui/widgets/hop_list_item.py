from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, LoadingIndicator, Placeholder, Pretty, Static

from pingtracer.core.application.services import RouteHop
from pingtracer.tui.widgets.hop_sparkline import HopSparkline


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

    def action_update_hop(self, new_hop: RouteHop):
        self.hop_statistic.update(HopListItem.statistic_str_from_hop(new_hop))
        self.sparkline.update(new_hop)

    @staticmethod
    def statistic_str_from_hop(hop: RouteHop) -> str:
        avg_rtt = hop.rtt.exp_avg or float("inf")
        std_rtt = hop.rtt.exp_std or float("inf")
        packet_loss = (
            100
            * hop.n_failed_measurements
            / (hop.n_failed_measurements + hop.n_successful_measurements)
        )
        return f"#{hop.hop}@{hop.hop_ipv4}: RTT: {avg_rtt:.2f}ms +/- {std_rtt:.2f} | Loss: {packet_loss:.2f}%"

    def compose(self) -> ComposeResult:
        with Vertical(classes="hop-list-item-wrapper"):
            self.hop_statistic = Static(HopListItem.statistic_str_from_hop(self.hop))
            yield self.hop_statistic

            self.sparkline = HopSparkline(self.hop)
            yield self.sparkline
