import re
from typing import ClassVar
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Input


class DomainNameInput(Widget):
    VALID_DOMAIN_NAME_RE: ClassVar[re.Pattern] = re.compile(
        r"^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$"
    )

    @staticmethod
    def is_domain_name(candidate: str) -> bool:
        return DomainNameInput.VALID_DOMAIN_NAME_RE.match(candidate.lower()) is not None

    def on_input_changed(self, event: Input.Changed):
        new_input = event.value
        if not DomainNameInput.is_domain_name(new_input):
            self.input.styles.border = ("solid", "red")
        else:
            self.input.styles.border = ("solid", "green")

    def compose(self) -> ComposeResult:
        self.input = Input(placeholder="Enter Target")
        yield self.input
