from pathlib import Path
from unittest.mock import patch

import pytest
from jinja2 import FileSystemLoader

from boilerplater.__main__ import boilerplater_config
from boilerplater.environment import VariablePromptingEnvironment
from boilerplater.rendering import (
    render_output_path,
    render_project_template,
    should_copy,
)


def make_env(tmp_path: Path) -> VariablePromptingEnvironment:
    return VariablePromptingEnvironment(loader=FileSystemLoader(str(tmp_path)))


def write(path: Path, content: str, mode: int = 0o644) -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)
    return path


def write_bytes(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path


# Minimal valid PNG header (magic bytes only — libmagic sniffs this)
PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + bytes(8)

# Minimal gzip/tar.gz header
GZIP_MAGIC = b"\x1f\x8b" + bytes(10)


class TestShouldRender:
    def test_plain_text_file(self, tmp_path):
        f = write(tmp_path / "readme.txt", "hello world")
        assert should_copy(f) is False

    def test_python_file(self, tmp_path):
        f = write(tmp_path / "main.py", "print('hello')")
        assert should_copy(f) is False

    def test_json_file(self, tmp_path):
        f = write(tmp_path / "config.json", '{"key": "value"}')
        assert should_copy(f) is False

    def test_yaml_file(self, tmp_path):
        f = write(tmp_path / "config.yaml", "key: value\n")
        assert should_copy(f) is False

    def test_toml_file(self, tmp_path):
        f = write(tmp_path / "pyproject.toml", "[tool.pytest]\n")
        assert should_copy(f) is False

    def test_xml_file(self, tmp_path):
        f = write(tmp_path / "config.xml", "<?xml version='1.0'?><root/>")
        assert should_copy(f) is False

    def test_markdown_file(self, tmp_path):
        f = write(tmp_path / "README.md", "# Hello")
        assert should_copy(f) is False

    def test_html_file(self, tmp_path):
        f = write(tmp_path / "index.html", "<html></html>")
        assert should_copy(f) is False

    def test_png_image_not_rendered(self, tmp_path):
        f = write_bytes(tmp_path / "image.png", PNG_MAGIC)
        assert should_copy(f) is True

    def test_elf_binary_not_rendered(self, tmp_path):
        import shutil

        f = shutil.copy("/bin/sh", tmp_path / "sh")
        assert should_copy(Path(f)) is True

    def test_gzip_archive_not_rendered(self, tmp_path):
        f = write_bytes(tmp_path / "archive.tar.gz", GZIP_MAGIC)
        assert should_copy(f) is True

    def test_shell_script(self, tmp_path):
        f = write(tmp_path / "run.sh", "#!/bin/bash\necho hello\n")
        assert should_copy(f) is False

    def test_makefile(self, tmp_path):
        f = write(tmp_path / "Makefile", "all:\n\techo done\n")
        assert should_copy(f) is False

    def test_dockerfile(self, tmp_path):
        f = write(tmp_path / "Dockerfile", "FROM python:3.12\n")
        assert should_copy(f) is False

    def test_gitignore(self, tmp_path):
        f = write(tmp_path / ".gitignore", "*.pyc\n__pycache__/\n")
        assert should_copy(f) is False


class TestRenderOutputPath:
    def test_plain_template_name(self, tmp_path):
        target = tmp_path / "output"
        env = make_env(tmp_path)
        result = render_output_path(env, "main.py", target)
        assert result.render() == str(target / "main.py")

    def test_template_name_with_variable(self, tmp_path):
        target = tmp_path / "output"
        env = make_env(tmp_path)
        env.globals["project_name"] = "myapp"
        result = render_output_path(env, "{{ project_name }}/main.py", target)
        assert result.render() == str(target / "myapp" / "main.py")

    def test_nested_template_path(self, tmp_path):
        target = tmp_path / "output"
        env = make_env(tmp_path)
        result = render_output_path(env, "src/core/utils.py", target)
        assert result.render() == str(target / "src" / "core" / "utils.py")

    def test_variable_in_path_registers_as_undeclared(self, tmp_path):
        target = tmp_path / "output"
        env = make_env(tmp_path)
        render_output_path(env, "{{ project_name }}/main.py", target)
        assert "project_name" in env.undeclared_variables

    def test_returns_template_object(self, tmp_path):
        from jinja2 import Template

        target = tmp_path / "output"
        env = make_env(tmp_path)
        result = render_output_path(env, "main.py", target)
        assert isinstance(result, Template)


class TestRenderTemplateDirectory:
    def test_renders_simple_text_template(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write(src / "hello.txt", "Hello {{ name }}")
        out = tmp_path / "out"
        boilerplater_config.category = tmp_path
        boilerplater_config.target_path = out
        boilerplater_config.project_template = src
        boilerplater_config.variables = {"name": "world"}
        render_project_template()

        assert (out / "hello.txt").read_text() == "Hello world"

    def test_copies_binary_file_unchanged(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write_bytes(src / "image.png", PNG_MAGIC)
        out = tmp_path / "out"

        boilerplater_config.category = tmp_path
        boilerplater_config.target_path = out
        boilerplater_config.project_template = src
        render_project_template()

        assert (out / "image.png").read_bytes() == PNG_MAGIC

    def test_preserves_file_permissions_on_render(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write(src / "script.sh", "#!/bin/bash\n", mode=0o755)
        out = tmp_path / "out"

        boilerplater_config.category = tmp_path
        boilerplater_config.target_path = out
        boilerplater_config.project_template = src
        render_project_template()

        mode = (out / "script.sh").stat().st_mode & 0o777
        assert mode == 0o755

    def test_creates_nested_output_directories(self, tmp_path):
        src = tmp_path / "src"
        (src / "a" / "b").mkdir(parents=True)
        write(src / "a" / "b" / "file.txt", "content")
        out = tmp_path / "out"

        boilerplater_config.category = tmp_path
        boilerplater_config.target_path = out
        boilerplater_config.project_template = src
        render_project_template()

        assert (out / "a" / "b" / "file.txt").exists()

    def test_template_variable_in_filename(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write(src / "{{ project_name }}.py", "# {{ project_name }}")
        out = tmp_path / "out"

        boilerplater_config.category = tmp_path
        boilerplater_config.target_path = out
        boilerplater_config.project_template = src
        boilerplater_config.variables = {"project_name": "myapp"}
        render_project_template()

        assert (out / "myapp.py").exists()
        assert (out / "myapp.py").read_text() == "# myapp"

    def test_multiple_templates_all_rendered(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write(src / "a.txt", "{{ x }}")
        write(src / "b.txt", "{{ y }}")
        out = tmp_path / "out"

        boilerplater_config.category = tmp_path
        boilerplater_config.target_path = out
        boilerplater_config.project_template = src
        boilerplater_config.variables = {"x": "hello", "y": "world"}
        render_project_template()

        assert (out / "a.txt").read_text() == "hello"
        assert (out / "b.txt").read_text() == "world"

    def test_typed_variable_in_template(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write(src / "f.txt", "{{ count: int }}")
        out = tmp_path / "out"

        with patch("boilerplater.rendering.run_form", return_value={"count": 42}):
            boilerplater_config.category = tmp_path
            boilerplater_config.target_path = out
            boilerplater_config.project_template = src
            render_project_template()
        assert (out / "f.txt").read_text() == "42"
