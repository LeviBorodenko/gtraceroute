import re
from typing import ClassVar
from textual import work
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input
from pingtracer.core.utils import get_ipv4


class DomainNameInput(Widget):
    VALID_DOMAIN_NAME_RE: ClassVar[re.Pattern] = re.compile(
        r"^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$"
    )

    @staticmethod
    def is_domain_name(candidate: str) -> bool:
        return DomainNameInput.VALID_DOMAIN_NAME_RE.match(candidate.lower()) is not None

    def __init__(self, *args, **kwargs) -> None:
        self.input = Input(*args, **kwargs)
        super().__init__()

    def on_input_changed(self, event: Input.Changed):
        new_input = event.value
        if not DomainNameInput.is_domain_name(new_input):
            self.input.styles.border = ("solid", "red")
        else:
            self.input.styles.border = ("solid", "green")

    class Submitted(Message):
        target_ipv4: str

        def __init__(self, target_ipv4: str) -> None:
            self.target_ipv4 = target_ipv4
            super().__init__()

    @work
    def on_input_submitted(self, event: Input.Submitted):
        if not DomainNameInput.is_domain_name(event.value):
            return
        target_ipv4 = get_ipv4(event.value)
        self.post_message(DomainNameInput.Submitted(target_ipv4))

    def compose(self) -> ComposeResult:
        self.input = Input(
            placeholder="Enter Target",
        )
        yield self.input
