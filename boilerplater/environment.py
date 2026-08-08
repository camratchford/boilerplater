import builtins
import re
from typing import Any, MutableMapping, Optional, Type, Union

from jinja2 import FileSystemLoader
from jinja2.environment import Environment, Template
from jinja2.meta import find_undeclared_variables
from jinja2.runtime import StrictUndefined


class VariablePromptingEnvironment(Environment):
    """
    Jinja2 Environment that pre-processes templates to support typed variables.
    Allows template authors to specify variable types using PEP 484 annotation syntax.
    Typed variables can be useful when prompting users for the value of undefined variables.
    """

    loader: FileSystemLoader

    def __init__(self, *args, **kwargs):
        """
        StrictUndefined is required as jinja2.meta.find_undeclared_variables will not detect any
        undeclared variables when the default of jinja2.runtime.Undefined is used.
        """
        super().__init__(*args, **kwargs, undefined=StrictUndefined)
        self.type_registry = {}
        self.undeclared_variables = {}

    def preprocess(self, source, name=None, filename=None):
        """
        - Extracts the PEP 484 type from the template variable tag, if it exists.
        - The variable name and type are stored in a dict 'Environment.type_registry'.
        - If no type annotation is found, the variable will be mapped to type 'str'.
        - The type annotation (: $type_name) is removed from the template source before handing it back
          to the parent class jinja2.environment.Environment's 'preprocess' method.
        """

        # In case it's not '{{' and '}}', we need to escape them because they probably still contain braces
        start_string = "".join(["\\" + char for char in self.variable_start_string])
        end_string = "".join(["\\" + char for char in self.variable_end_string])
        type_pattern = start_string + r"s*(\w+)\s*:\s*(\w+)\s*" + end_string
        """
        Matches '{{ $var_name : $type_name }}' where:
          - '{{' and '}}' are self.variable_start_string and self.variable_end_string respectively
          - '$var_name', '$type_name' are any word 
          - whitespace is optional
        """

        for match in re.finditer(type_pattern, source):
            var_name, var_type_str = match.groups()
            var_type_str = var_type_str if var_name is not None else "str"
            var_type = (
                getattr(builtins, var_type_str)
                if hasattr(builtins, var_type_str)
                else str
            )
            self.type_registry[var_name] = var_type

        clean_source = re.sub(
            type_pattern,
            rf"{self.variable_start_string} \1 {self.variable_start_string}",
            source,
        )
        return super().preprocess(clean_source, name, filename)

    def update_undeclared_variables(self, source: str):
        ast = self.parse(source)
        undeclared_variables = list(find_undeclared_variables(ast))
        if undeclared_variables:
            input_variables = {
                var_name: self.type_registry.get(var_name, str)
                for var_name in undeclared_variables
            }
            self.undeclared_variables.update(input_variables)

    def get_template(
        self,
        name: Union[str, "Template"],
        parent: Optional[str] = None,
        _globals: Optional[MutableMapping[str, Any]] = None,
    ) -> "Template":
        if isinstance(name, Template):
            return name

        if parent is not None:
            name: str = self.join_path(name, parent)

        source, _, _ = self.loader.get_source(self, name)
        self.update_undeclared_variables(source)

        template = self._load_template(name, _globals)
        return template

    def from_string(
        self,
        source: Union[str],
        _globals: Optional[MutableMapping[str, Any]] = None,
        template_class: Optional[Type[Template]] = None,
    ) -> "Template":
        self.update_undeclared_variables(source)
        gs = self.make_globals(_globals)
        cls = template_class or self.template_class
        return cls.from_code(self, self.compile(source), gs, None)
