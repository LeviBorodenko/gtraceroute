from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Placeholder

from pingtracer.core.application.services import RouteHop
from pingtracer.tui.widgets.hop_list_item import HopListItem


class HopList(Widget):
    def __init__(
        self,
        *children: Widget,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            *children, name=name, id=id, classes=classes, disabled=disabled
        )

    hops: reactive[list[RouteHop]] = reactive([], always_update=True)

    def watch_hops(self, new_hops: list[RouteHop]):
        self.action_update_hops(new_hops)
        print("UPDATED HOPS")

    def action_monitor_hops(self):
        self.action_update_hops(self.hops)

    def action_update_hops(self, new_hops: list[RouteHop]):
        container = self.query_one("#hop-list", VerticalScroll)
        container.remove_children()
        for hop in new_hops:
            container.mount(HopListItem(hop))

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="hop-list"):
            yield Placeholder()
