from pathlib import Path
from typing import Any

from pydantic import BaseModel


class SentinelNone:
    """Sentinel Type because the annotated type could be 'None'"""
    ...


class BaseTemplateConfig(BaseModel):
    name: str
    description: str = ""
    path: Path | None = None
    requirements: list[str] | None = []
    available_modules: list[str] | None = None
    variable_default_values: dict[str, Any] | None = {}
    exclude_patterns: list[str] | None = [
        "boilerplater.yml",
    ]
    force_copy_patterns: list[str] = ["*.j2"]
    cleanup_patterns: list[str] | None = [".placeholder", ".gitkeep"]

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if hasattr(other, "name"):
            return self.name == other.name

        return self.name == other
