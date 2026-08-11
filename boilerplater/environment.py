import builtins
import logging
import re
from typing import Any, MutableMapping, Optional, Type, Union

from click import Choice
from jinja2 import FileSystemLoader, TemplateSyntaxError
from jinja2.environment import Environment, Template
from jinja2.meta import find_undeclared_variables
from jinja2.runtime import StrictUndefined

logger = logging.getLogger(__name__)


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
        self.type_registry: dict[str, type | object] = {}
        """
        Used to assign types to keys in self.undeclared_variables.
        Is populated during pre-process, marking a variable as the found type. Type defaults to str if none is found.
        """

        self.undeclared_variables: dict[str, type] = {}
        """
        Used to produce Textual form fields, allowing the user to set the value for unset variables. 
        Key is the variable name, value is the type of the variable which determines which form field 
        and validator to use in the form.
        """

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
        var_pattern = r"(\w+)"
        type_pattern = r"(\w+)"
        type_args_pattern = r"([\(\[]\[.+\][\)\]])"
        match_pattern = (
            start_string
            + r"\s*"
            + var_pattern
            + r"\s*:\s*"
            + type_pattern
            + r"\s*(?:"
            + type_args_pattern
            + r")?\s*"
            + end_string
        )

        for match in re.finditer(match_pattern, source):
            var_name, var_type_str, var_type_args = match.groups()
            var_type_str = var_type_str if var_name is not None else "str"

            if "Choice" == var_type_str.strip():
                choice_args = var_type_args.lstrip("(").rstrip(")")
                self.type_registry[var_name] = Choice(eval(choice_args))

                continue

            var_type = (
                getattr(builtins, var_type_str)
                if hasattr(builtins, var_type_str)
                else str
            )
            self.type_registry[var_name] = var_type

        clean_source = re.sub(
            match_pattern,
            rf"{self.variable_start_string} \1 {self.variable_end_string}",
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
        """
        Based on jinja2.Environment's original get_template method, adding the call to update_undeclared_variables.
        """
        if isinstance(name, Template):
            return name

        if parent is not None:
            name: str = self.join_path(name, parent)

        source, _, _ = self.loader.get_source(self, name)

        try:
            self.update_undeclared_variables(source)
        except TemplateSyntaxError as e:
            logger.error(f"Syntax error at: {name}:{e.lineno}")
            raise e

        template = self._load_template(name, _globals)
        return template

    def from_string(
        self,
        source: Union[str],
        _globals: Optional[MutableMapping[str, Any]] = None,
        template_class: Optional[Type[Template]] = None,
    ) -> "Template":
        """
        Based on jinja2.Environment's original from_string method, adding the call to update_undeclared_variables.
        """
        self.update_undeclared_variables(source)
        gs = self.make_globals(_globals)
        cls = template_class or self.template_class
        return cls.from_code(self, self.compile(source), gs, None)
