from pydantic import model_validator
from typing_extensions import Self

from boilerplater.template_config.base_template import BaseTemplateConfig


class ProjectTemplateConfig(BaseTemplateConfig):
    category: str
    add_ons: list[str] = []

    @model_validator(mode="after")
    def validate_add_ons(self) -> Self:
        """
        Make sure that the provided add_ons exist
        """
        from boilerplater.config import BoilerplaterConfig

        boilerplater_config = BoilerplaterConfig()
        for add_on in self.add_ons:
            add_on_config = boilerplater_config.module_configs.get(add_on)
            if not add_on_config:
                raise KeyError(
                    f"Cannot process add-ons for project template {self.name}. "
                    f"No module with name '{add_on}' exists."
                )

        return self
