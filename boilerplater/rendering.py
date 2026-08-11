import logging
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2
from subprocess import run, PIPE

from jinja2 import FileSystemLoader, Template
from magic import from_file

from boilerplater.config import BoilerplaterConfig
from boilerplater.environment import VariablePromptingEnvironment
from boilerplater.form import run_form
from boilerplater.template_config import BaseTemplateConfig


boilerplater_config = BoilerplaterConfig()
logger = logging.getLogger(__name__)


@dataclass()
class OutputData:
    output_path_template: Template
    subtemplate_path: Path
    subtemplate: Template = None
    will_copy: bool = False


def should_copy(path: Path) -> bool:
    mimetype = from_file(str(path), mime=True)
    force_copy_paths = []
    if boilerplater_config.project_template_config:
        force_copy_paths = [
            file
            for pattern in boilerplater_config.force_copy_patterns
            for file in path.parent.glob(pattern)
        ]

    return (
        path in force_copy_paths
        or not mimetype.startswith("text/")
        and mimetype
        not in {
            "application/json",
            "application/xml",
            "application/x-yaml",
            "application/toml",
        }
        and path.suffix
        not in {
            ".md",
            ".html",
        }
    )


def should_skip(path: Path):
    if boilerplater_config.project_template_config:
        return path in [
            file
            for pattern in boilerplater_config.exclude_patterns
            for file in path.parent.glob(pattern)
        ]
    return []


def render_output_path(
    env: VariablePromptingEnvironment,
    template: str,
    target_path: Path,
):
    """output_path may contain a template tag '{{ var }}' that needs rendering as well"""
    name_path = Path(target_path) / template
    env.from_string(name_path.resolve().as_posix())
    return env.from_string(str(name_path))


def render_template_data(
    template_config: BaseTemplateConfig,
) -> list[OutputData]:

    template_loader = FileSystemLoader(template_config.path)
    jinaj2_settings = boilerplater_config.get_by_prefix("jinja2")
    template_env = VariablePromptingEnvironment(
        loader=template_loader, **jinaj2_settings
    )
    template_env.globals.update(**boilerplater_config.variables)
    defaults = {
        **boilerplater_config.variable_default_values,
        **template_config.variable_default_values,
    }

    payload_data = []
    for sub_template in template_env.list_templates():
        subtemplate_path = template_config.path / sub_template
        if should_skip(subtemplate_path):
            continue

        will_copy = should_copy(subtemplate_path)
        output_data = OutputData(
            output_path_template=render_output_path(
                template_env, sub_template, boilerplater_config.target_path
            ),
            subtemplate_path=subtemplate_path,
            subtemplate=template_env.get_template(sub_template)
            if not will_copy
            else None,
            will_copy=will_copy,
        )

        payload_data.append(output_data)

    if template_env.undeclared_variables:
        new_variables = run_form(
            variables=template_env.undeclared_variables, defaults=defaults
        )
        if new_variables is None:
            logger.info("Operation cancelled")
            raise SystemExit(0)
        boilerplater_config.variables.update(new_variables)
        template_env.globals.update(new_variables)

    return payload_data


def execute_run_on_complete_scripts():
    for script in boilerplater_config.run_on_complete_scripts:
        script_path = boilerplater_config.target_path / script
        if not script_path.exists():
            logger.warning(f'run_on_complete_scripts script {script_path} does not exist')
            continue
        script_process = run(
            args=f"./{script}",
            cwd=boilerplater_config.target_path.as_posix(),
            text=True,
            stdout=PIPE,
            stderr=PIPE
        )
        if script_process.returncode:
            logger.warning(
                f'run_on_complete_scripts script {script_path} exited with error code {script_process.returncode}: ' +
                script_process.stdout if script_process.stdout else "" +
                script_process.stderr if script_process.stderr else ""
            )
            return

        print(script_process.stdout)


def cleanup_files_matching_cleanup_patterns():
    if boilerplater_config.project_template_config:
        cleanup_paths = [
            file
            for pattern in boilerplater_config.cleanup_patterns
            for file in boilerplater_config.target_path.glob(pattern)
        ]
        for file in cleanup_paths:
            file.unlink()


def render_project_template():
    template_list = [
        boilerplater_config.project_template_config
        if boilerplater_config.project_template_config
        else ...,
        *boilerplater_config.requirements,
    ]
    payload_data = [
        output_data
        for template_config in template_list
        for output_data in render_template_data(template_config)
    ]

    for output_data in payload_data:
        output_path = Path(output_data.output_path_template.render())
        if not boilerplater_config.dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_data.will_copy:
            logger.debug(f"Copying: {output_data.subtemplate_path} to {output_path}")
            if boilerplater_config.dry_run:
                continue

            copy2(output_data.subtemplate_path, output_path)
            continue

        logger.debug(f"Rendering: {output_data.subtemplate_path} to {output_path}")
        if boilerplater_config.dry_run:
            continue

        output_path.write_text(output_data.subtemplate.render(), encoding="utf-8")
        output_path.chmod(mode=output_data.subtemplate_path.stat().st_mode)

    execute_run_on_complete_scripts()
    cleanup_files_matching_cleanup_patterns()
