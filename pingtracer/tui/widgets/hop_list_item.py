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
        avg_rtt = new_hop.rtt.exp_avg or float("inf")
        std_rtt = new_hop.rtt.exp_std or float("inf")
        packet_loss = (
            100
            * new_hop.n_failed_measurements
            / (new_hop.n_failed_measurements + new_hop.n_successful_measurements)
        )
        self.hop_static.update(f"#{new_hop.hop}")
        self.ip_static.update(f"{new_hop.hop_ipv4}")
        self.rtt_static.update(f"RTT: {avg_rtt:.2f}ms +/- {std_rtt:.2f}")
        self.loss_static.update(f"Loss: {packet_loss:.2f}")
        self.sparkline.update_data()

    def compose(self) -> ComposeResult:
        avg_rtt = self.hop.rtt.exp_avg or float("inf")
        std_rtt = self.hop.rtt.exp_std or float("inf")
        packet_loss = (
            100
            * self.hop.n_failed_measurements
            / (self.hop.n_failed_measurements + self.hop.n_successful_measurements)
        )
        with VerticalScroll(classes="hop-list-item-wrapper"):
            with Vertical(classes="hop-list-item-label-wrapper"):
                self.hop_static = Static(f"#{self.hop.hop}", shrink=True)
                yield self.hop_static
                self.ip_static = Static(f"{self.hop.hop_ipv4}", shrink=True)
                yield self.ip_static
                self.rtt_static = Static(
                    f"RTT: {avg_rtt:.2f}ms +/- {std_rtt:.2f}", shrink=True
                )
                yield self.rtt_static
                self.loss_static = Static(f"Loss: {packet_loss:.2f}", shrink=True)
                yield self.loss_static

            self.sparkline = HopSparkline(self.hop)
            yield self.sparkline
