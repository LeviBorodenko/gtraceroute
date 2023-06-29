from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget

from pingtracer.core.application.services import RouteHop
from pingtracer.tui.widgets.hop_list_item import HopListItem


class HopList(Widget):
    hops: reactive[list[RouteHop]] = reactive([], always_update=True)

    def watch_hops(self, new_hops: list[RouteHop]):
        # WE ASSUME THAT THE TARGET IPV4 DOES NOT CHANGE DURING THE LIFETIME OF THIS WIDGET
        # Thus: It has to be recreated for other targets!
        container = self.get_child_by_id("hop-list", VerticalScroll)
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
                container.mount(
                    HopListItem(new_hop),
                    # append to end or after the previous hop
                    after=min(new_hop.hop, len(hop_list_item_by_hop)) - 1,
                )

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="hop-list")
