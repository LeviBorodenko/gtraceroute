from textual.widgets import OptionList
from textual.widgets.option_list import Option, OptionDoesNotExist, Separator


class TargetList(OptionList):
    def add_target(self, target_name: str, target_ipv4: str):
        try:
            self.get_option(target_ipv4)
        except OptionDoesNotExist:
            renderable = f"[b]{target_name}[/b] ({target_ipv4})"
            option = Option(
                renderable,
                id=target_ipv4,
            )
            self.add_options((option, Separator()))
