import logging
from pathlib import Path
from typing import Annotated

from click import Choice
from rich.logging import RichHandler
from typer import Argument, Context, Option, Typer

from boilerplater.config import BoilerplaterConfig, LogLevel
from boilerplater.form import run_form
from boilerplater.rendering import render_project_template

cli = Typer(pretty_exceptions_enable=False)
boilerplater_config = BoilerplaterConfig()
logger = logging.getLogger(__name__)
logger.addHandler(RichHandler(show_time=False))


default_templates_dir = (
    Path().home().joinpath(".local/opt/boilerplater/templates").resolve()
)
default_data_dir = Path().home().joinpath(".local/opt/boilerplater/data").resolve()


def get_templates_dir(ctx: Context):
    if not ctx.params.get("templates_dir"):
        return None

    templates_dir = Path(
        str(ctx.params.get("templates_dir", boilerplater_config.template_dir))
    )

    if not templates_dir.resolve().is_dir():
        return None

    return templates_dir


def complete_category(ctx: Context, incomplete: str):
    templates_dir = get_templates_dir(ctx)
    categories = [
        directory for directory in templates_dir.iterdir() if directory.is_dir()
    ]
    for path in categories:
        if path.name.startswith(incomplete) and path.name:
            yield path.name.replace(" ", r"\ "), path
    return ""


def complete_template(ctx: Context, incomplete: str):
    templates_dir = get_templates_dir(ctx)

    category = ctx.params.get("category", "")
    if not category:
        return ""

    category_dir = templates_dir / category
    for path in [subdir for subdir in category_dir.iterdir() if subdir.is_dir()]:
        if path.name.startswith(incomplete) and path.name:
            yield path.name.replace(" ", r"\ "), path

    return ""


def prompt_for_missing_cli_params(category: str, template: str):
    category_is_set = category is not None
    template_is_set = template is not None

    if category_is_set:
        boilerplater_config.category = boilerplater_config.templates_dir / category

    if not category_is_set and not template_is_set:
        category_choices = Choice(boilerplater_config.list_categories())
        category_value = run_form({"category": category_choices})
        if category_value is None:
            logger.info("Cancelled form input. Exiting.")
            raise SystemExit(0)
        category = Path(category_value["category"])
        boilerplater_config.category = boilerplater_config.templates_dir / category

        template_choices = Choice(boilerplater_config.list_templates())
        template_value = run_form({"template": template_choices})
        if template_value is None:
            logger.info("Cancelled form input. Exiting.")
            raise SystemExit(0)
        boilerplater_config.project_template = (
            boilerplater_config.category / template_value["template"]
        )

    elif category_is_set and not template_is_set:
        boilerplater_config.category = boilerplater_config.templates_dir / category
        if not boilerplater_config.category.exists():
            logger.error(f"Category '{boilerplater_config.category}' does not exist")
            raise SystemExit(1)

        template_choices = Choice(boilerplater_config.list_templates())
        form_fields = {"template": template_choices}
        template_value = run_form(form_fields)
        if template_value is None:
            logger.info("Cancelled form input. Exiting.")
            raise SystemExit(0)
        boilerplater_config.project_template = (
            boilerplater_config.category / template_value["template"]
        )

    if template_is_set:
        boilerplater_config.category = boilerplater_config.templates_dir / category
        boilerplater_config.project_template = boilerplater_config.category / template
        if not boilerplater_config.project_template.exists():
            logger.error(
                f"Template '{boilerplater_config.project_template}' does not exist"
            )
            raise SystemExit(1)

    if not boilerplater_config.category or not boilerplater_config.project_template:
        logger.error('You must provide both "--category" and  "--template" parameters')
        raise SystemExit(1)


# Todo: Add
#  --list-categories - A tree of the categories and templates
#  --list-modules    - A table
#  --get-module
#  --get-template
@cli.command()
def main(
    target_path: Annotated[Path, Argument(dir_okay=True)],
    init: Annotated[
        bool,
        Option(
            "--init",
            help="Creates the templates-dir, modules-dir, and data-dir directories if they do not already exist.",
        ),
    ] = False,
    templates_dir: Annotated[
        Path,
        Option(
            "--templates-dir",
            help=f"Location of your project templates. "
            f"[dim](default: {boilerplater_config.template_dir.as_posix()})",
            dir_okay=True,
            # envvar="BOILERPLATER_TEMPLATE_DIR",
        ),
    ] = boilerplater_config.template_dir,
    data_dir: Annotated[
        Path,
        Option(
            "--data-dir",
            help="Location of your YAML variable files. "
            f"[dim](default: {boilerplater_config.data_dir.as_posix()})",
            dir_okay=True,
            # envvar="BOILERPLATER_DATA_DIR",
        ),
    ] = boilerplater_config.data_dir,
    modules_dir: Annotated[
        Path,
        Option(
            "--modules-dir",
            help="Location of template modules. "
            f"[dim](default: {boilerplater_config.modules_dir.as_posix()})",
            dir_okay=True,
            # envvar="BOILERPLATER_MODULES_DIR",
        ),
    ] = boilerplater_config.modules_dir,
    category: Annotated[
        Path | None,
        Option(
            "-c",
            "--category",
            autocompletion=complete_category,
            help="Select which language / framework the templates belong to. "
            "[dim](Will prompt if none is provided.)",
            dir_okay=True,
        ),
    ] = None,
    project_template: Annotated[
        Path | None,
        Option(
            "-t",
            "--template",
            autocompletion=complete_template,
            help="Select a project template [dim](Will prompt if none is provided.)",
            dir_okay=True,
        ),
    ] = None,
    log_level: Annotated[
        LogLevel | None,
        Option(
            "--log-level",
            help="The stdlib logging module's log level"
            f"[dim](defaut: {boilerplater_config.log_level.value})",
        ),
    ] = boilerplater_config.log_level,
    dry_run: Annotated[
        bool,
        Option(
            "--dry-run",
            help="Do not copy or render templates",
        ),
    ] = boilerplater_config.dry_run,
):

    boilerplater_config.update(
        templates_dir=templates_dir,
        data_dir=data_dir,
        modules_dir=modules_dir,
        target_path=target_path,
        log_level=log_level,
        dry_run=dry_run,
    )

    logging.basicConfig(level=log_level.value, format="%(levelname)s: %(message)s")

    if init:
        if not boilerplater_config.templates_dir.resolve().is_dir():
            logger.info(
                f"templates-dir {boilerplater_config.templates_dir} does not exist. Creating directory"
            )
            if not boilerplater_config.dry_run:
                boilerplater_config.templates_dir.mkdir(parents=True, mode=0o644)
        if not boilerplater_config.data_dir.resolve().is_dir():
            logger.info(
                f"data-dir {boilerplater_config.data_dir} does not exist. Creating directory"
            )
            if not boilerplater_config.dry_run:
                boilerplater_config.data_dir.mkdir(parents=True, mode=0o644)
        if not boilerplater_config.modules_dir.resolve().is_dir():
            logger.info(
                f"modules-dir {boilerplater_config.modules_dir} does not exist. Creating directory"
            )
            if not boilerplater_config.dry_run:
                boilerplater_config.modules_dir.mkdir(parents=True, mode=0o644)

    if not len([i for i in boilerplater_config.templates_dir.iterdir()]):
        logger.error(
            f"Value for --templates-dir '{boilerplater_config.templates_dir}' is empty. No templates available. "
            f"Use the --init option, or"
        )
        raise SystemExit(1)

    prompt_for_missing_cli_params(category, project_template)
    boilerplater_config.load_defaults()

    render_project_template()


if __name__ == "__main__":
    cli()
