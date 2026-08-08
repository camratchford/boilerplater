from pydantic import model_validator
from typing_extensions import Self

from boilerplater.template_config.base_template import BaseTemplateConfig


class ModuleTemplateConfig(BaseTemplateConfig):
    target_categories: list[str] | str | None = None  # None for disabled '*' for all

    @model_validator(mode="after")
    def validate_categories(self) -> Self:
        """
        Make sure that the provided target_categories exist
        and handle glob star value by implicitly adding all categories
        """
        from boilerplater.config import BoilerplaterConfig

        boilerplater_config = BoilerplaterConfig()
        if self.target_categories == "*":
            self.target_categories = boilerplater_config.list_categories()
            return self

        if not hasattr(self.target_categories, "__iter__"):
            self.target_categories = []
            return self

        for category in self.target_categories:
            if category not in boilerplater_config.list_categories():
                raise ValueError(f"No category with name: {category}")

        return self
