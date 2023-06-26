from collections.abc import Callable, Sequence
from textual.widgets import Placeholder, Sparkline
from pingtracer.core.application.services import RouteHop


class HopSparkline(Sparkline):
    hop: RouteHop

    def __init__(
        self,
        hop: RouteHop,
        *,
        summary_function: Callable[[Sequence[float]], float] | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        self.hop = hop
        super().__init__(
            list(hop.rtt.buffer),
            summary_function=summary_function,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        # self.set_interval(update_interval, self.update_data)

    def update_data(self):
        self.data = list(self.hop.rtt.buffer)
