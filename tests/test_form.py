import click
import pytest
from textual.widgets import Checkbox, Input, Select, Static

from boilerplater.form import TemplateFormApp, _coerce_to_type, _is_choice


class TestIsChoice:
    def test_click_choice_recognised(self):
        assert _is_choice(click.Choice(["a", "b"])) is True

    def test_str_not_recognised(self):
        assert _is_choice(str) is False

    def test_bool_not_recognised(self):
        assert _is_choice(bool) is False


class TestCoerce:
    def test_str(self):
        assert _coerce_to_type("hello", str) == "hello"
        assert isinstance(_coerce_to_type("hello", str), str)

    def test_int(self):
        assert _coerce_to_type("42", int) == 42
        assert isinstance(_coerce_to_type("42", int), int)

    def test_float(self):
        assert _coerce_to_type("3.14", float) == pytest.approx(3.14)
        assert isinstance(_coerce_to_type("3.14", float), float)

    def test_bool_truthy(self):
        assert _coerce_to_type(True, bool) is True

    def test_bool_falsy(self):
        assert _coerce_to_type(False, bool) is False

    def test_choice(self):
        t = click.Choice(["a", "b"])
        assert _coerce_to_type("a", t) == "a"
        assert isinstance(_coerce_to_type("a", t), str)


class TestWidgetRendering:
    async def test_str_renders_input(self):
        app = TemplateFormApp({"name": str})
        async with app.run_test():
            assert app.query_one("#field_name", Input)

    async def test_int_renders_input(self):
        app = TemplateFormApp({"count": int})
        async with app.run_test():
            assert app.query_one("#field_count", Input)

    async def test_float_renders_input(self):
        app = TemplateFormApp({"ratio": float})
        async with app.run_test():
            assert app.query_one("#field_ratio", Input)

    async def test_bool_renders_checkbox(self):
        app = TemplateFormApp({"enabled": bool})
        async with app.run_test():
            assert app.query_one("#field_enabled", Checkbox)

    async def test_choice_renders_select(self):
        app = TemplateFormApp({"level": click.Choice(["a", "b"])})
        async with app.run_test():
            assert app.query_one("#field_level", Select)

    async def test_multiple_fields_all_rendered(self):
        variables = {
            "name": str,
            "debug": bool,
            "retries": int,
            "level": click.Choice(["INFO", "DEBUG"]),
        }
        app = TemplateFormApp(variables)
        async with app.run_test():
            assert app.query_one("#field_name", Input)
            assert app.query_one("#field_debug", Checkbox)
            assert app.query_one("#field_retries", Input)
            assert app.query_one("#field_level", Select)


class TestDefaults:
    async def test_str_default_prefills_input(self):
        app = TemplateFormApp({"name": str}, defaults={"name": "myproject"})
        async with app.run_test():
            widget = app.query_one("#field_name", Input)
            assert widget.value == "myproject"

    async def test_int_default_prefills_input(self):
        app = TemplateFormApp({"retries": int}, defaults={"retries": 3})
        async with app.run_test():
            widget = app.query_one("#field_retries", Input)
            assert widget.value == "3"

    async def test_float_default_prefills_input(self):
        app = TemplateFormApp({"version": float}, defaults={"version": 1.5})
        async with app.run_test():
            widget = app.query_one("#field_version", Input)
            assert widget.value == "1.5"

    async def test_bool_default_true(self):
        app = TemplateFormApp({"debug": bool}, defaults={"debug": True})
        async with app.run_test():
            widget = app.query_one("#field_debug", Checkbox)
            assert widget.value is True

    async def test_bool_default_false(self):
        app = TemplateFormApp({"debug": bool}, defaults={"debug": False})
        async with app.run_test():
            widget = app.query_one("#field_debug", Checkbox)
            assert widget.value is False

    async def test_choice_default_selected(self):
        app = TemplateFormApp(
            {"level": click.Choice(["DEBUG", "INFO", "WARNING"])},
            defaults={"level": "INFO"},
        )
        async with app.run_test():
            widget = app.query_one("#field_level", Select)
            assert widget.value == "INFO"

    async def test_missing_default_leaves_input_empty(self):
        app = TemplateFormApp({"name": str}, defaults={})
        async with app.run_test():
            widget = app.query_one("#field_name", Input)
            assert widget.value == ""


class TestSubmission:
    async def test_submit_str_field(self):
        app = TemplateFormApp({"name": str})
        async with app.run_test() as pilot:
            await pilot.click("#field_name")
            await pilot.press(*"myapp")
            await pilot.click("#btn-submit")
            await pilot.pause()

        assert app.return_value == {"name": "myapp"}

    async def test_submit_int_field(self):
        app = TemplateFormApp({"retries": int})
        async with app.run_test() as pilot:
            await pilot.click("#field_retries")
            await pilot.press(*"5")
            await pilot.click("#btn-submit")
            await pilot.pause()

        assert app.return_value == {"retries": 5}

    async def test_submit_float_field(self):
        app = TemplateFormApp({"version": float})
        async with app.run_test() as pilot:
            await pilot.click("#field_version")
            await pilot.press(*"2.5")
            await pilot.click("#btn-submit")
            await pilot.pause()

        assert app.return_value == {"version": pytest.approx(2.5)}

    async def test_submit_bool_field_default_false(self):
        app = TemplateFormApp({"debug": bool})
        async with app.run_test() as pilot:
            await pilot.click("#btn-submit")
            await pilot.pause()

        assert app.return_value == {"debug": False}

    async def test_submit_bool_field_checked(self):
        app = TemplateFormApp({"debug": bool})
        async with app.run_test() as pilot:
            await pilot.click("#field_debug")
            await pilot.click("#btn-submit")
            await pilot.pause()

        assert app.return_value == {"debug": True}

    async def test_submit_with_defaults_unchanged(self):
        app = TemplateFormApp({"name": str}, defaults={"name": "default"})
        async with app.run_test() as pilot:
            await pilot.click("#btn-submit")
            await pilot.pause()

        assert app.return_value == {"name": "default"}

    async def test_submit_with_default_overridden(self):
        app = TemplateFormApp({"name": str}, defaults={"name": "old"})
        async with app.run_test() as pilot:
            # Clear the pre-filled value and type a new one
            app.query_one("#field_name", Input).clear()
            await pilot.click("#field_name")
            await pilot.press(*"new")
            await pilot.click("#btn-submit")
            await pilot.pause()

        assert app.return_value == {"name": "new"}

    async def test_ctrl_s_submits(self):
        app = TemplateFormApp({"name": str}, defaults={"name": "hello"})
        async with app.run_test() as pilot:
            await pilot.press("ctrl+s")
            await pilot.pause()

        assert app.return_value == {"name": "hello"}


class TestValidation:
    async def test_empty_str_shows_error(self):
        app = TemplateFormApp({"name": str})
        async with app.run_test() as pilot:
            await pilot.click("#btn-submit")
            await pilot.pause()

            error = app.query_one("#error-msg", Static)
            assert "name" in str(error.render()).lower()

        # App should NOT have exited with a value
        assert app.return_value is None

    async def test_invalid_int_shows_error(self):
        app = TemplateFormApp({"retries": int})
        async with app.run_test() as pilot:
            await pilot.click("#field_retries")
            await pilot.press(*"abc")
            await pilot.click("#btn-submit")
            await pilot.pause()

            error = app.query_one("#error-msg", Static)
            assert str(error.render()) != ""

        assert app.return_value is None

    async def test_invalid_float_shows_error(self):
        app = TemplateFormApp({"ratio": float})
        async with app.run_test() as pilot:
            await pilot.click("#field_ratio")
            await pilot.press(*"not_a_float")
            await pilot.click("#btn-submit")
            await pilot.pause()

            error = app.query_one("#error-msg", Static)
            assert str(error.render()) != ""

        assert app.return_value is None

    async def test_unselected_choice_shows_error(self):
        app = TemplateFormApp({"level": click.Choice(["a", "b"])})
        async with app.run_test() as pilot:
            await pilot.click("#btn-submit")
            await pilot.pause()

            error = app.query_one("#error-msg", Static)
            assert str(error.render()) != ""

        assert app.return_value is None

    async def test_multiple_errors_reported(self):
        app = TemplateFormApp({"name": str, "count": int})
        async with app.run_test() as pilot:
            await pilot.click("#btn-submit")
            await pilot.pause()

            error = app.query_one("#error-msg", Static)
            text = str(error.render())
            assert "name" in text.lower()
            assert "count" in text.lower()


class TestCancellation:
    async def test_cancel_button_returns_none(self):
        app = TemplateFormApp({"name": str})
        async with app.run_test() as pilot:
            await pilot.click("#btn-cancel")
            await pilot.pause()

        assert app.return_value is None

    async def test_escape_returns_none(self):
        app = TemplateFormApp({"name": str})
        async with app.run_test() as pilot:
            await pilot.press("escape")
            await pilot.pause()

        assert app.return_value is None
