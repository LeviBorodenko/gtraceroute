from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.validation import Function
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static
from gtraceroute.core.utils import InvalidAddressException, get_ipv4


def is_domain_name(candidate: str) -> bool:
    try:
        get_ipv4(candidate)
    except InvalidAddressException:
        return False
    return True


class TargetInput(Widget):
    input: Input = Input(
        placeholder="Enter Name or IP here",
        validators=[Function(is_domain_name, "Input is not a valid domain name.")],
    )
    target_ipv4: reactive[str | None]
    trace_btn: Button = Button("Trace", variant="default", id="trace-btn")

    class Submitted(Message):
        target_ipv4: str
        target_name: str

        def __init__(self, target_name: str, target_ipv4: str) -> None:
            self.target_ipv4 = target_ipv4
            self.target_name = target_name
            super().__init__()

    @work
    def on_input_changed(self, event: Input.Changed):
        btn = self.trace_btn
        if event.validation_result and event.validation_result.is_valid:
            target_ipv4 = get_ipv4(event.value)
            self.target_ipv4 = target_ipv4
            btn.disabled = False
            btn.label = f"Trace {target_ipv4}"
            btn.success()
        else:
            btn.disabled = True
            btn.label = "Trace"

    def on_input_submitted(self):
        assert self.target_ipv4 is not None
        self.post_message(TargetInput.Submitted(self.input.value, self.target_ipv4))

    def on_button_pressed(self):
        assert self.target_ipv4 is not None
        self.post_message(TargetInput.Submitted(self.input.value, self.target_ipv4))

    def compose(self) -> ComposeResult:
        yield Static("[bold][red]g[/red]traceroute[/bold] v0", id="greeter")
        with Horizontal(id="action-container"):
            yield Label("Target:")
            yield self.input
            self.trace_btn.disabled = True
            yield self.trace_btn
