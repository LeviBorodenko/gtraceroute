from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import LoadingIndicator, Placeholder, Pretty, Static

from pingtracer.core.application.services import RouteHop


class HopListItem(Widget):
    hop: RouteHop

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
        self.set_interval(1, self.update_data)

    def update_data(self):
        rtts = list(self.hop.rtt.buffer)
        avg_rtt = self.hop.rtt.exp_avg or float("inf")
        std_rtt = self.hop.rtt.exp_std or float("inf")
        packet_loss = (
            100
            * self.hop.n_failed_measurements
            / (self.hop.n_failed_measurements + self.hop.n_successful_measurements)
        )

        self.remove_children()
        self.mount(Pretty(self.hop))

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()
