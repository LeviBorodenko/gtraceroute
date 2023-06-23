from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Placeholder

from pingtracer.core.application.services import RouteHop
from pingtracer.tui.widgets.hop_list_item import HopListItem


class HopList(Widget):
    hops: reactive[list[RouteHop]] = reactive([])

    def watch_hops(self, new_hops: list[RouteHop]):
        container = self.query_one("#hop-list", VerticalScroll)
        container.remove_children()
        for hop in new_hops:
            container.mount(HopListItem(hop))

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="hop-list"):
            yield Placeholder()
