from dataclasses import dataclass
from textual.widgets import OptionList


class TargetList(OptionList):
    def add_target(self, target_name: str, target_ipv4: str):
        renderable = f"[b]{target_name}[/b] ({target_ipv4})"
        self.add_option(renderable)
