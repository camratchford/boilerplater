import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated

from click import Choice
from rich.logging import RichHandler
from slugify import slugify
from typer import Argument, Context, Option, Typer
from yaml import safe_load

from boilerplater.form import run_form
from boilerplater.rendering import render_template_directory

cli = Typer(pretty_exceptions_enable=False)
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(show_time=False))


default_templates_dir = (
    Path().home().joinpath(".local/opt/boilerplater/templates").resolve()
)
default_data_dir = Path().home().joinpath(".local/opt/boilerplater/data").resolve()


class LogLevel(str, Enum):
    debug = "DEBUG"
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"
    critical = "CRITICAL"


def complete_category(ctx: Context, incomplete: str):
    templates_dir_str = str(ctx.params.get("templates_dir"))
    templates_dir = Path(str(ctx.params.get("templates_dir")))
    if not templates_dir_str or not templates_dir.is_dir():
        return ""
    categories = [
        directory for directory in templates_dir.iterdir() if directory.is_dir()
    ]
    for path in categories:
        if path.name.startswith(incomplete) and path.name:
            yield path.name.replace(" ", r"\ "), path
    return ""


def complete_template(ctx: Context, incomplete: str):
    templates_dir_str = str(ctx.params.get("templates_dir"))
    templates_dir = Path(str(ctx.params.get("templates_dir")))
    if not templates_dir_str or not templates_dir.is_dir():
        return ""

    category = ctx.params.get("category", "")
    if not category:
        return ""

    category_dir = templates_dir / category
    for path in [subdir for subdir in category_dir.iterdir() if subdir.is_dir()]:
        if path.name.startswith(incomplete) and path.name:
            yield path.name.replace(" ", r"\ "), path

    return ""


@cli.command()
def main(
    target_path: Annotated[Path, Argument(dir_okay=True)],
    templates_dir: Annotated[
        Path,
        Option(
            "--templates-dir",
            help="Location of your project templates",
            envvar="BOILERPLATER_TEMPLATE_DIR",
            dir_okay=True,
        ),
    ] = default_templates_dir,
    data_dir: Annotated[
        Path,
        Option(
            "--data-dir",
            help="Location of your YAML variable files",
            envvar="BOILERPLATER_DATA_DIR",
            dir_okay=True,
        ),
    ] = default_data_dir,
    category: Annotated[
        Path,
        Option(
            "-p",
            "--category",
            autocompletion=complete_category,
            help="Select which language / framework the templates belong to",
            dir_okay=True,
        ),
    ] = None,
    template: Annotated[
        Path,
        Option(
            "-t",
            "--template",
            autocompletion=complete_template,
            help="Select a project template",
            dir_okay=True,
        ),
    ] = None,
    log_level: Annotated[
        LogLevel,
        Option(
            "--log-level",
        ),
    ] = LogLevel.warning,
):

    logger.setLevel(log_level.value)

    if not templates_dir.is_dir():
        logger.info(
            f"Value for --templates-dir does not exist. Creating directory {templates_dir}"
        )
        templates_dir.mkdir(parents=True, mode=0o644)

    if not len([i for i in templates_dir.iterdir()]):
        logger.error(
            f"Value for --templates-dir '{templates_dir}' is empty. No templates available."
        )
        raise SystemExit(1)

    if not data_dir.is_dir():
        logger.info(
            f"Value for --data-dir does not exist. Creating directory {data_dir}"
        )
        data_dir.mkdir(parents=True, mode=0o644)

    required_params = {
        param for param in ("category", "template") if locals().get(param) is None
    }
    if "category" in required_params and "template" in required_params:
        category_choices = Choice(
            [subdir.name for subdir in templates_dir.iterdir() if subdir.is_dir()]
        )
        category_value = run_form({"category": category_choices})
        if category_value is None:
            raise SystemExit(1)
        category = Path(category_value["category"])
        category_dir = templates_dir / category

        template_choices = Choice(
            [subdir.name for subdir in category_dir.iterdir() if subdir.is_dir()]
        )
        template_value = run_form({"template": template_choices})
        if template_value is None:
            raise SystemExit(1)
        template = template_value["template"]

    elif "category" not in required_params and "template" in required_params:
        category_dir = templates_dir / category
        template_choices = Choice(
            [subdir.name for subdir in category_dir.iterdir() if subdir.is_dir()]
        )
        form_fields = {"template": template_choices}
        template_value = run_form(form_fields)
        if template_value is None:
            raise SystemExit(1)
        template = Path(template_value["template"])

    if not category or not template:
        raise ValueError(
            'You must provide both "--category" and  "--template" parameters'
        )

    directory_template = templates_dir / category / template
    assert isinstance(directory_template, Path) and directory_template.is_dir()

    data_files = [data_file for data_file in data_dir.iterdir() if data_file.is_file()]
    variables = {"now": datetime.now()}
    for data_file in data_files:
        yaml_text = data_file.read_text()
        if not yaml_text:
            continue
        data = safe_load(yaml_text)
        if isinstance(data, dict):
            variables.update(data)

    default_package_name = target_path.stem
    default_module_name = slugify(default_package_name, separator="_")
    defaults = {
        "module_name": default_module_name,
        "package_name": default_package_name,
    }
    render_template_directory(directory_template, target_path, variables, defaults)


if __name__ == "__main__":
    cli()
