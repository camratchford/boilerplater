from __future__ import annotations

from typing import Any

import click
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.validation import Function
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
)


def _is_choice(t: Any) -> bool:
    return isinstance(t, click.Choice)


def _coerce(value: Any, t: Any) -> Any:
    if t is bool or t is bool:
        return bool(value)
    if t is int:
        return int(value)
    if t is float:
        return float(value)
    if _is_choice(t):
        return str(value)
    return str(value)


class TemplateFormApp(App[dict[str, Any]]):
    CSS = """
    Screen {
        background: $surface;
    }

    #form-container {
        padding: 1 2;
        height: 1fr;
    }

    .field-block {
        height: 3;
        align: left middle;
    }

    .field-label {
        width: 24;
        color: $text-muted;
        text-style: bold;
        content-align: left middle;
        height: 3;
    }

    .type-hint {
        width: 16;
        color: $text-disabled;
        text-style: italic;
        content-align: left middle;
        height: 3;
    }

    .field-block Input {
        width: 1fr;
    }

    .field-block Select {
        width: 1fr;
    }

    .field-block Checkbox {
        width: auto;
    }

    #button-bar {
        align: right middle;
        height: 3;
        padding: 0 2;
    }

    #btn-submit {
        margin-left: 1;
    }

    .error-msg {
        color: $error;
        text-style: bold;
        height: auto;
        padding: 0 0 1 0;
    }
    """

    BINDINGS = [
        ("ctrl+s", "submit", "Submit"),
        ("escape", "quit_app", "Quit"),
    ]

    def __init__(
        self, variables: dict[str, Any], defaults: dict[str, Any] | None = None
    ):
        super().__init__()
        self.variables = variables
        self.defaults = defaults or {}
        self._error_label: Static | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Footer()

        with ScrollableContainer(id="form-container"):
            for name, t in self.variables.items():
                if _is_choice(t):
                    type_hint = "choice"
                elif t is bool:
                    type_hint = "bool"
                elif t is int:
                    type_hint = "int"
                elif t is float:
                    type_hint = "float"
                else:
                    type_hint = "str"

                with Horizontal(classes="field-block"):
                    yield Label(name.replace("_", " ").title(), classes="field-label")
                    yield Label(type_hint, classes="type-hint")

                    default = self.defaults.get(name)

                    if _is_choice(t):
                        options = [(c, c) for c in t.choices]
                        yield Select(
                            options,
                            id=f"field_{name}",
                            prompt="Select…",
                            value=str(default) if default is not None else Select.BLANK,
                        )

                    elif t is bool:
                        yield Checkbox(
                            "",
                            id=f"field_{name}",
                            value=bool(default) if default is not None else False,
                        )

                    elif t is int:
                        yield Input(
                            value=str(default) if default is not None else "",
                            placeholder="integer…",
                            id=f"field_{name}",
                            validators=[
                                Function(
                                    lambda v: v.lstrip("-").isdigit(),
                                    "Must be a whole number",
                                )
                            ],
                        )

                    elif t is float:
                        yield Input(
                            value=str(default) if default is not None else "",
                            placeholder="number…",
                            id=f"field_{name}",
                            validators=[
                                Function(
                                    lambda v: _is_valid_float(v),
                                    "Must be a valid number",
                                )
                            ],
                        )

                    else:
                        yield Input(
                            value=str(default) if default is not None else "",
                            placeholder="text…",
                            id=f"field_{name}",
                        )

            yield Static("", id="error-msg", classes="error-msg")

        with Horizontal(id="button-bar"):
            yield Button("Cancel", variant="default", id="btn-cancel")
            yield Button("Submit", variant="primary", id="btn-submit")

    def action_submit(self) -> None:
        self._do_submit()

    def action_quit_app(self) -> None:
        self.exit(None)

    @on(Button.Pressed, "#btn-submit")
    def handle_submit(self) -> None:
        self._do_submit()

    @on(Button.Pressed, "#btn-cancel")
    def handle_cancel(self) -> None:
        self.exit(None)

    def _do_submit(self) -> None:
        results: dict[str, Any] = {}
        errors: list[str] = []

        for name, t in self.variables.items():
            widget_id = f"field_{name}"

            if _is_choice(t):
                widget: Select = self.query_one(f"#{widget_id}", Select)
                if widget.value is Select.BLANK:
                    errors.append(f"'{name}' requires a selection.")
                    continue
                results[name] = str(widget.value)

            elif t is bool:
                widget: Checkbox = self.query_one(f"#{widget_id}", Checkbox)
                results[name] = widget.value

            else:
                widget: Input = self.query_one(f"#{widget_id}", Input)
                raw = widget.value.strip()

                if not raw:
                    errors.append(f"'{name}' cannot be empty.")
                    continue

                validation_result = widget.validate(raw)
                if validation_result is not None and validation_result.failures:
                    errors.append(f"'{name}' has an invalid value.")
                    continue

                try:
                    results[name] = _coerce(raw, t)
                except (ValueError, TypeError):
                    errors.append(f"'{name}' could not be converted to {t.__name__}.")

        error_widget = self.query_one("#error-msg", Static)
        if errors:
            error_widget.update("\n".join(errors))
        else:
            error_widget.update("")
            self.exit(results)


def _is_valid_float(v: str) -> bool:
    try:
        float(v)
        return True
    except ValueError:
        return False


def run_form(
    variables: dict[str, Any], defaults: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """
    Launch the Textual form and return the filled values dict.

    Args:
        variables: Mapping of variable_name -> type.  Duplicate keys are
                   collapsed automatically (last definition wins, preserving
                   insertion order of first occurrence).
        defaults:  Optional mapping of variable_name -> default value.
                   Pre-fills the corresponding widget; user can override.

    Returns:
        A dict of {variable_name: coerced_value}, or None if the user
        cancelled.
    """
    seen: dict[str, Any] = {}
    for name, t in variables.items():
        if name not in seen:
            seen[name] = t

    app = TemplateFormApp(seen, defaults=defaults)
    return app.run()
