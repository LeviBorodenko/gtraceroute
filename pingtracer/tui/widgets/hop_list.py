from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget

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
        container = self.query_one("#hop-list", VerticalScroll)
        hop_list_item_by_hop = {
            listitem.hop.hop: listitem
            for listitem in container.query("#hop-list HopListItem").results(
                HopListItem
            )
        }
        for new_hop in new_hops:
            if new_hop.hop in hop_list_item_by_hop:
                hop_list_item_by_hop[new_hop.hop].action_update_hop(new_hop)
            else:
                container.mount(HopListItem(new_hop))

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="hop-list")
