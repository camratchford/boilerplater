import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from pprint import pformat
from typing import Any

from byoconfig import Config
from byoconfig.singleton import SingletonMetaclass
from slugify import slugify

from boilerplater.template_config import (
    ModuleTemplateConfig,
    ProjectTemplateConfig,
    BaseTemplateConfig,
)
from boilerplater.form import run_form

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
    template_dir: Path | None = default_templates_dir.resolve()
    data_dir: Path | None = default_data_dir.resolve()
    modules_dir: Path | None = None

    log_level: LogLevel = LogLevel.info
    dry_run: bool = False

    target_path: Path | None = None
    category: Path | None = None
    template_path: Path | None = None

    module_configs: dict[str, ModuleTemplateConfig] | None = {}
    project_template_config: ProjectTemplateConfig | None = None
    variables: dict[str, Any] = {"now": datetime.now()}

    requirements: list[ModuleTemplateConfig] | None = []
    available_modules: list[ModuleTemplateConfig] | None = None
    variable_default_values: dict[str, Any] = {}

    def __init__(self, **kwargs):
        # Prevent missing CLI params from overriding our defaults
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        super().__init__(**kwargs, env_prefix="BOILERPLATER", env_trim_prefix=True)
        if not self.modules_dir:
            self.modules_dir = self.template_dir / "modules"

    def load_yaml(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
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

        selected_addons = run_form(variables=available_add_ons, title="Select Add-ons", defaults={})
        if not selected_addons:
            return []
        add_ons = [
            add_on
            for add_on, enabled in selected_addons.items()
            if enabled
        ]
        return add_ons

    def load_modules(self):
        for module in self.modules_dir.iterdir():
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
        if not self.data_dir.resolve().is_dir():
            raise FileNotFoundError(f"Data dir '{self.data_dir}' does not exist")

        for data_file in self.data_dir.iterdir():
            if data_file.suffix not in [".yml", ".yaml"]:
                continue
            logger.info(f"Loading variables from: {data_file}")
            self.variables.update(self.load_yaml(data_file))

    @property
    def project_template(self):
        return self.template_path

    @project_template.setter
    def project_template(self, template_path: Path):
        self.load_defaults()
        self.load_variables()
        self.load_modules()

        self.template_path = template_path
        template_config_data = self.load_yaml(self.template_path / "boilerplater.yml")
        self.project_template_config = ProjectTemplateConfig(
            name=self.template_path.name,  # Goes first so it can be overwritten by template_config_data
            **template_config_data,
            path=self.template_path,
            category=self.category.name,
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
        return [category.name for category in self.template_dir.iterdir()]

    def list_templates(self, with_category: str = None):
        if with_category and with_category in self.list_categories():
            return [
                template.name
                for template in self.template_dir.joinpath(with_category).iterdir()
            ]

        if not self.category:
            return []

        return [template.name for template in self.category.iterdir()]
