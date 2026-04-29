from pathlib import Path
from shutil import copy2

from jinja2 import FileSystemLoader
from magic import from_file

from boilerplater.environment import VariablePromptingEnvironment
from boilerplater.form import run_form


def should_render(path: Path) -> bool:
    mimetype = from_file(str(path), mime=True)
    return (
        mimetype.startswith("text/")
        or mimetype
        in {
            "application/json",
            "application/xml",
            "application/x-yaml",
            "application/toml",
        }
        or path.suffix
        in {
            ".md",
            ".html",
        }
        and path.suffix not in {".j2"}
    )


def render_output_path(
    env: VariablePromptingEnvironment, template: str, target_path: Path
):
    """output_path may contain a template tag '{{ var }}' that needs rendering as well"""
    name_path = Path(target_path) / template
    env.from_string(name_path.resolve().as_posix())
    return env.from_string(str(name_path))


def render_template_directory(
    directory_template: Path, target_path: Path, variables: dict, defaults: dict
):
    template_loader = FileSystemLoader(directory_template)
    template_env = VariablePromptingEnvironment(loader=template_loader)
    template_env.globals.update(**variables)

    copy_files = []
    output_templates = []

    for template in template_env.list_templates():
        template_path = directory_template / template
        path_data = [
            render_output_path(template_env, template, target_path),
            template_path,
        ]

        if should_render(template_path) and template_path.suffix != ".j2":
            path_data.append(template_env.get_template(template))
            output_templates.append(path_data)
            continue

        copy_files.append(path_data)

    if template_env.undeclared_variables:
        new_variables = run_form(
            variables=template_env.undeclared_variables, defaults=defaults
        )
        if new_variables is None:
            raise SystemExit()
        template_env.globals.update(new_variables)

    for output_path_template, template_path, template in output_templates:
        output_path = Path(output_path_template.render())
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(template.render(), encoding="utf-8")
        output_path.chmod(mode=template_path.stat().st_mode)

    for output_path_template, template_path in copy_files:
        output_path = Path(output_path_template.render())
        output_path.parent.mkdir(parents=True, exist_ok=True)
        copy2(template_path, output_path)
