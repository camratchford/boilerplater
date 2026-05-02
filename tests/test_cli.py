from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from boilerplater.__main__ import cli

runner = CliRunner()

MOCK_RENDER = "boilerplater.__main__.render_template_directory"
MOCK_FORM = "boilerplater.__main__.run_form"


@pytest.fixture()
def templates_dir(tmp_path: Path) -> Path:
    """A templates directory with two categories, each with two templates."""
    t = tmp_path / "templates"
    (t / "python" / "cli").mkdir(parents=True)
    (t / "python" / "library").mkdir(parents=True)
    (t / "rust" / "cli").mkdir(parents=True)
    return t


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    """An empty data directory."""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture()
def target_path(tmp_path: Path) -> Path:
    return tmp_path / "my-project"


def invoke(templates_dir, data_dir, target_path, extra_args=(), **kwargs):
    """Helper to invoke the CLI with standard base args."""
    args = [
        str(target_path),
        "--templates-dir",
        str(templates_dir),
        "--data-dir",
        str(data_dir),
        *extra_args,
    ]
    return runner.invoke(cli, args, **kwargs)


class TestArgumentValidation:
    def test_missing_target_path_exits_nonzero(self, templates_dir, data_dir):
        with patch(MOCK_RENDER), patch(MOCK_FORM, return_value=None):
            result = runner.invoke(
                cli,
                [
                    "--templates-dir",
                    str(templates_dir),
                    "--data-dir",
                    str(data_dir),
                ],
            )
            assert result.exit_code != 0

    def test_empty_templates_dir_exits_1(self, tmp_path, data_dir, target_path):
        with patch(MOCK_RENDER), patch(MOCK_FORM, return_value=None):
            empty = tmp_path / "empty_templates"
            empty.mkdir()
            result = invoke(empty, data_dir, target_path)
            assert result.exit_code == 1

    def test_invalid_template_directory_exits_1(
        self, templates_dir, data_dir, target_path
    ):
        with patch(MOCK_RENDER), patch(MOCK_FORM):
            result = invoke(
                templates_dir,
                data_dir,
                target_path,
                extra_args=["--category", "python", "--template", "nonexistent"],
            )
        assert result.exit_code == 1

    def test_missing_both_category_and_template_prompts_form(
        self, templates_dir, data_dir, target_path
    ):
        with (
            patch(
                MOCK_FORM,
                side_effect=[
                    {"category": "python"},
                    {"template": "cli"},
                ],
            ),
            patch(MOCK_RENDER),
        ):
            result = invoke(templates_dir, data_dir, target_path)
        assert result.exit_code == 0

    def test_category_provided_template_missing_prompts_form(
        self, templates_dir, data_dir, target_path
    ):
        with patch(MOCK_FORM, return_value={"template": "cli"}):
            result = invoke(
                templates_dir,
                data_dir,
                target_path,
                extra_args=["--category", "python"],
            )
        assert result.exit_code == 0

    def test_both_provided_skips_form(self, templates_dir, data_dir, target_path):
        with patch(MOCK_FORM) as mock_form, patch(MOCK_RENDER):
            result = invoke(
                templates_dir,
                data_dir,
                target_path,
                extra_args=["--category", "python", "--template", "cli"],
            )
        mock_form.assert_not_called()
        assert result.exit_code == 0


class TestFormCancellation:
    def test_cancel_category_form_exits_0(self, templates_dir, data_dir, target_path):
        with patch(MOCK_FORM, return_value=None), patch(MOCK_RENDER):
            result = invoke(templates_dir, data_dir, target_path)
        assert result.exit_code == 0

    def test_cancel_template_form_exits_0(self, templates_dir, data_dir, target_path):
        with (
            patch(MOCK_FORM, side_effect=[{"category": "python"}, None]),
            patch(MOCK_RENDER),
        ):
            result = invoke(templates_dir, data_dir, target_path)
        assert result.exit_code == 0

    def test_cancel_template_form_with_category_provided_exits_0(
        self, templates_dir, data_dir, target_path
    ):
        with patch(MOCK_FORM, return_value=None), patch(MOCK_RENDER):
            result = invoke(
                templates_dir,
                data_dir,
                target_path,
                extra_args=["--category", "python"],
            )
        assert result.exit_code == 0


class TestTemplateResolution:
    def test_correct_template_dir_passed_to_render(
        self, templates_dir, data_dir, target_path
    ):
        with patch(MOCK_RENDER) as mock_render, patch(MOCK_FORM, return_value=None):
            invoke(
                templates_dir,
                data_dir,
                target_path,
                extra_args=["--category", "python", "--template", "cli"],
            )
        called_template_dir = mock_render.call_args[0][0]
        assert called_template_dir == templates_dir / "python" / "cli"

    def test_correct_target_path_passed_to_render(
        self, templates_dir, data_dir, target_path
    ):
        with patch(MOCK_RENDER) as mock_render, patch(MOCK_FORM, return_value=None):
            invoke(
                templates_dir,
                data_dir,
                target_path,
                extra_args=["--category", "python", "--template", "cli"],
            )
        called_target = mock_render.call_args[0][1]
        assert called_target == target_path

    def test_category_from_form_used_for_resolution(
        self, templates_dir, data_dir, target_path
    ):
        with (
            patch(
                MOCK_FORM,
                side_effect=[
                    {"category": "rust"},
                    {"template": "cli"},
                ],
            ),
            patch(MOCK_RENDER) as mock_render,
        ):
            invoke(templates_dir, data_dir, target_path)

        called_template_dir = mock_render.call_args[0][0]
        assert called_template_dir == templates_dir / "rust" / "cli"


class TestDataFileLoading:
    def test_yaml_data_passed_as_variables(self, templates_dir, data_dir, target_path):
        (data_dir / "user.yaml").write_text("author: Alice\nemail: alice@example.com\n")

        with patch(MOCK_RENDER) as mock_render, patch(MOCK_FORM, return_value=None):
            invoke(
                templates_dir,
                data_dir,
                target_path,
                extra_args=["--category", "python", "--template", "cli"],
            )

        variables = mock_render.call_args[0][2]
        assert variables["author"] == "Alice"
        assert variables["email"] == "alice@example.com"

    def test_multiple_yaml_files_merged(self, templates_dir, data_dir, target_path):
        (data_dir / "a.yaml").write_text("x: 1\n")
        (data_dir / "b.yaml").write_text("y: 2\n")

        with patch(MOCK_RENDER) as mock_render, patch(MOCK_FORM, return_value=None):
            invoke(
                templates_dir,
                data_dir,
                target_path,
                extra_args=["--category", "python", "--template", "cli"],
            )

        variables = mock_render.call_args[0][2]
        assert variables["x"] == 1
        assert variables["y"] == 2

    def test_empty_yaml_file_ignored(self, templates_dir, data_dir, target_path):
        (data_dir / "empty.yaml").write_text("")

        with patch(MOCK_RENDER), patch(MOCK_FORM, return_value=None):
            result = invoke(
                templates_dir,
                data_dir,
                target_path,
                extra_args=["--category", "python", "--template", "cli"],
            )

        assert result.exit_code == 0

    def test_non_dict_yaml_ignored(self, templates_dir, data_dir, target_path):
        (data_dir / "list.yaml").write_text("- item1\n- item2\n")

        with patch(MOCK_RENDER) as mock_render, patch(MOCK_FORM, return_value=None):
            invoke(
                templates_dir,
                data_dir,
                target_path,
                extra_args=["--category", "python", "--template", "cli"],
            )

        variables = mock_render.call_args[0][2]
        assert "0" not in variables  # list items should not bleed in

    def test_now_variable_always_present(self, templates_dir, data_dir, target_path):
        from datetime import datetime

        with patch(MOCK_RENDER) as mock_render, patch(MOCK_FORM, return_value=None):
            invoke(
                templates_dir,
                data_dir,
                target_path,
                extra_args=["--category", "python", "--template", "cli"],
            )

        variables = mock_render.call_args[0][2]
        assert "now" in variables
        assert isinstance(variables["now"], datetime)

    def test_missing_data_dir_is_created(self, templates_dir, tmp_path, target_path):
        nonexistent_data = tmp_path / "new_data_dir"
        assert not nonexistent_data.exists()

        with patch(MOCK_RENDER), patch(MOCK_FORM, return_value=None):
            invoke(
                templates_dir,
                nonexistent_data,
                target_path,
                extra_args=["--category", "python", "--template", "cli"],
            )

        assert nonexistent_data.is_dir()


class TestDefaults:
    def test_module_name_default_derived_from_target(
        self, templates_dir, data_dir, tmp_path
    ):
        target = tmp_path / "my-cool-project"

        with patch(MOCK_RENDER) as mock_render, patch(MOCK_FORM, return_value=None):
            invoke(
                templates_dir,
                data_dir,
                target,
                extra_args=["--category", "python", "--template", "cli"],
            )

        defaults = mock_render.call_args[0][3]
        assert defaults["module_name"] == "my_cool_project"

    def test_package_name_default_derived_from_target(
        self, templates_dir, data_dir, tmp_path
    ):
        target = tmp_path / "my-cool-project"

        with patch(MOCK_RENDER) as mock_render, patch(MOCK_FORM, return_value=None):
            invoke(
                templates_dir,
                data_dir,
                target,
                extra_args=["--category", "python", "--template", "cli"],
            )

        defaults = mock_render.call_args[0][3]
        assert defaults["package_name"] == "my-cool-project"
