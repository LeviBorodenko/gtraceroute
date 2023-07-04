from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget

from pingtracer.core.application.services import RouteHop
from pingtracer.tui.widgets.hop_list_item import HopListItem


def get_unique_by_hop_ipv4(hops: list[RouteHop]) -> list[RouteHop]:
    seen_ipv4s = set()
    unique_objs = []

    for hop in hops:
        if hop.hop_ipv4 not in seen_ipv4s:
            seen_ipv4s.add(hop.hop_ipv4)
            unique_objs.append(hop)

    return unique_objs


class HopList(Widget):
    hops: reactive[list[RouteHop]] = reactive([], always_update=True)

    async def watch_hops(self, new_hops: list[RouteHop]):

        # sometimes the tracer can return the final hop multiple times due to lag
        new_hops = get_unique_by_hop_ipv4(new_hops)
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
                await container.mount(
                    HopListItem(new_hop),
                    # append to end or after the previous hop
                    after=min(new_hop.hop, len(hop_list_item_by_hop)) - 1,
                )

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="hop-list")
