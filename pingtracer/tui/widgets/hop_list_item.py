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

    def compose(self) -> ComposeResult:
        avg_rtt = self.hop.rtt.exp_avg or float("inf")
        std_rtt = self.hop.rtt.exp_std or float("inf")
        packet_loss = (
            100
            * self.hop.n_failed_measurements
            / (self.hop.n_failed_measurements + self.hop.n_successful_measurements)
        )
        with VerticalScroll(classes="hop-list-item-wrapper"):
            with Horizontal(classes="hop-list-item-label-wrapper"):
                yield Label(f"#{self.hop.hop} ")
                yield Label(f"{self.hop.hop_ipv4} ")
                yield Static(f"RTT: {avg_rtt:.2f}ms +/- {std_rtt:.2f}")
                yield Static(f"Loss: {packet_loss:.2f}")
            yield HopSparkline(self.hop)
