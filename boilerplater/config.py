import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from pprint import pformat
from typing import Any, Union

from byoconfig import Config
from byoconfig.singleton import SingletonMetaclass
from slugify import slugify

from boilerplater.form import run_form
from boilerplater.template_config import (
    BaseTemplateConfig,
    ModuleTemplateConfig,
    ProjectTemplateConfig,
)

logger = logging.getLogger(__name__)
home = Path().home()
default_templates_dir = home / ".local/opt/boilerplater/templates"
default_data_dir = home / ".local/opt/boilerplater/data"


class LogLevel(str, Enum):
    debug = "DEBUG"
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"
    critical = "CRITICAL"


class BoilerplaterConfig(Config, metaclass=SingletonMetaclass):
    config_file: Path = None
    templates_dir: Path | None = default_templates_dir.resolve()
    data_dir: Path | None = default_data_dir.resolve()
    modules_dir: Path | None = None
    _log_level: LogLevel = LogLevel.info
    dry_run: bool = False
    target_path: Path | None = None
    category: Path | None = None
    template: Path | None = None

    jinja2_block_start_string: str = "{%"
    jinja2_block_end_string: str = "%}"
    jinja2_variable_start_string: str = "{{"
    jinja2_variable_end_string: str = "}}"
    jinja2_comment_start_string: str = "{#"
    jinja2_comment_end_string: str = "#}"
    jinja2_line_statement_prefix: str = None
    jinja2_line_comment_prefix: str = None
    jinja2_trim_blocks: bool = False
    jinja2_lstrip_blocks: bool = False
    jinja2_newline_sequence: str = "\n"
    jinja2_keep_trailing_newline: bool = False

    module_configs: dict[str, ModuleTemplateConfig] | None = {}
    project_template_config: ProjectTemplateConfig | None = None
    variables: dict[str, Any] = {"now": datetime.now()}

    exclude_patterns: list[str] = []
    force_copy_patterns: list[str] = []
    cleanup_patterns: list[str] = []
    run_on_complete_scripts: list[Path] = []

    requirements: list[ModuleTemplateConfig] | None = []
    available_modules: list[ModuleTemplateConfig] | None = None
    variable_default_values: dict[str, Any] = {}

    def __init__(self, **kwargs):
        # Prevent missing CLI params from overriding our defaults
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        super().__init__(
            **kwargs,
            env_prefix="BOILERPLATER",
            env_trim_prefix=True,
            config_assign_attrs=False,
        )
        if not self.modules_dir and self.templates_dir.joinpath("modules").exists():
            self.modules_dir = self.templates_dir / "modules"

    def load_yaml(self, path: Path) -> dict[str, Any]:
        if path is None or not path.is_file():
            return {}

        try:
            data = self._load_yaml(path)
            if not data:
                return {}

        except Exception as e:
            logger.warning(
                f"Error while loading YAML file '{path.as_posix()}': {e.args}",
                exc_info=e,
            )
            return {}

        if not isinstance(data, dict):
            raise TypeError(
                f"YAML file '{path}' top-level data structure must be a mapping."
            )

        return data

    def load_add_ons(self):
        if not self.project_template_config.add_ons:
            return []
        available_add_ons = {
            module: bool
            for module in self.module_configs
            if module in self.project_template_config.add_ons
        }

        selected_addons = run_form(
            variables=available_add_ons, title="Select Add-ons", defaults={}
        )
        if not selected_addons:
            return []
        add_ons = [add_on for add_on, enabled in selected_addons.items() if enabled]
        return add_ons

    def load_modules(self):
        if not self.modules_dir or not self.modules_dir.is_dir():
            logger.debug(f"Modules dir '{self.modules_dir}' does not exist. Skipping.")
            return

        for module in self.modules_dir.iterdir():
            if module.name in self.module_configs:
                continue

            module_config_file = module / "boilerplater.yml"
            if not module_config_file.is_file():
                continue

            module_data = self.load_yaml(module_config_file)
            if not module_data:
                continue

            if not isinstance(module_data, dict):
                raise TypeError(f"Module config {module_config_file} is not a mapping.")

            self.module_configs[module.name] = ModuleTemplateConfig(
                name=module.name,  # Goes first so can be overwritten by module_data
                **module_data,
                path=module,
            )
            self.exclude_patterns.extend(
                self.module_configs[module.name].exclude_patterns
            )
            self.force_copy_patterns.extend(
                self.module_configs[module.name].force_copy_patterns
            )
            self.cleanup_patterns.extend(
                self.module_configs[module.name].cleanup_patterns
            )
            self.run_on_complete_scripts.extend(
                self.module_configs[module.name].run_on_complete_scripts
            )

    def load_defaults(self):
        default_package_name = self.target_path.stem
        default_module_name = slugify(default_package_name, separator="_")
        defaults = {
            "module_name": default_module_name,
            "package_name": default_package_name,
        }

        logger.debug(f"Defaults: {pformat(defaults, indent=2, width=100)}")
        self.variable_default_values = defaults

    def load_variables(self):
        if not self.data_dir:
            return
        if not self.data_dir.is_dir():
            logger.debug(f"Data dir '{self.data_dir}' does not exist. Skipping.")
            return

        for data_file in self.data_dir.iterdir():
            if data_file.suffix not in [".yml", ".yaml"]:
                continue
            logger.info(f"Loading variables from: {data_file}")
            self.variables.update(self.load_yaml(data_file))

    @property
    def log_level(self):
        return self._log_level

    @log_level.setter
    def log_level(self, level: Union[int, str, LogLevel]):
        if isinstance(level, int):
            level_str = logging.getLevelName(level)
            # The 'level not found' return according to
            # https://docs.python.org/3.14/library/logging.html#logging.getLevelName
            if not level_str.startswith("Level "):
                self._log_level = LogLevel.__members__[level_str.lower()]
        elif isinstance(level, str):
            self._log_level = LogLevel.__members__[level.lower()]
        elif isinstance(level, LogLevel):
            self._log_level = level
        else:
            # I would show them a warning, but the logger isn't intialized yet.
            print(
                f"Invalid type for log level '{str(level)}': {type(level)}. "
                f"Acceptable types are int, str, and {type(LogLevel.info)}"
            )

    @property
    def project_template(self):
        return self.template

    @project_template.setter
    def project_template(self, template_path: Path):
        self.load_defaults()
        self.load_variables()
        self.load_modules()

        self.template = template_path
        template_config_data = self.load_yaml(self.template / "boilerplater.yml")
        self.project_template_config = ProjectTemplateConfig(
            name=self.template.name,  # Goes first so it can be overwritten by template_config_data
            **template_config_data,
            path=self.template,
            category=self.category.name,
        )
        self.exclude_patterns.extend(self.project_template_config.exclude_patterns)
        self.force_copy_patterns.extend(
            self.project_template_config.force_copy_patterns
        )
        self.cleanup_patterns.extend(self.project_template_config.cleanup_patterns)
        self.run_on_complete_scripts.extend(
            self.project_template_config.run_on_complete_scripts
        )

        self.project_template_config.requirements.extend(self.load_add_ons())
        self.requirements.extend(self.get_requirements(self.project_template_config))

    def get_requirements(
        self,
        template_config: BaseTemplateConfig,
        requirements: list[ModuleTemplateConfig] = None,
    ):
        self.load_modules()
        if not requirements:
            requirements = []

        for requirement in template_config.requirements:
            if requirement not in self.module_configs:
                raise KeyError(f"No module with name: {requirement}")

            if requirement in requirements:
                continue

            module_config = self.module_configs[requirement]
            if module_config.requirements:
                self.get_requirements(module_config, requirements)

            if template_config.category not in module_config.target_categories:
                raise ValueError(
                    f"Listed required module '{module_config.name}' "
                    f"does not support the selected template's category."
                )

            requirements.append(module_config)

        return requirements

    def list_categories(self):
        return [category.name for category in self.templates_dir.iterdir()]

    def list_templates(self, with_category: str = None):
        if with_category and with_category in self.list_categories():
            return [
                template.name
                for template in self.templates_dir.joinpath(with_category).iterdir()
            ]

        if not self.category:
            return []

        return [template.name for template in self.category.iterdir()]
