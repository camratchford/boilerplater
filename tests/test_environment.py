from jinja2 import FileSystemLoader

from boilerplater.environment import VariablePromptingEnvironment
from boilerplater.__main__ import boilerplater_config


def make_env(tmp_path, start_str: str = "{{", end_str: str = "}}") -> VariablePromptingEnvironment:
    variable_str_kwargs = {"variable_start_string": start_str, "variable_end_string": end_str}
    return VariablePromptingEnvironment(loader=FileSystemLoader(str(tmp_path)), **variable_str_kwargs)


def write_template(tmp_path, name: str, content: str):
    (tmp_path / name).write_text(content)


class TestTypeRegistry:
    def test_untyped_variable_defaults_to_str(self, tmp_path):
        env = make_env(tmp_path)
        env.preprocess("{{ name }}")
        assert env.type_registry.get("name", str) is str

    def test_typed_variable_is_registered(self, tmp_path):
        env = make_env(tmp_path)
        env.preprocess("{{ count: int }}")
        assert env.type_registry["count"] is int

    def test_typed_variable_works_when_var_string_is_changed(self, tmp_path):
        env = make_env(tmp_path, start_str="{&", end_str="&}")
        env.preprocess("{& count: int &}")
        assert env.type_registry["count"] is int

    def test_choice_type(self, tmp_path):
        from click import Choice
        env = make_env(tmp_path)
        env.preprocess("{{ x_enabled: Choice(['true', 'false']) }}")
        assert isinstance(env.type_registry["x_enabled"], Choice)

    def test_all_builtin_types_resolve(self, tmp_path):
        env = make_env(tmp_path)
        source = "{{ a: int }} {{ b: float }} {{ c: bool }} {{ d: str }}"
        env.preprocess(source)
        assert env.type_registry["a"] is int
        assert env.type_registry["b"] is float
        assert env.type_registry["c"] is bool
        assert env.type_registry["d"] is str

    def test_unknown_type_falls_back_to_str(self, tmp_path):
        env = make_env(tmp_path)
        env.preprocess("{{ thing: NonExistentType }}")
        assert env.type_registry["thing"] is str

    def test_type_annotation_stripped_from_output(self, tmp_path):
        env = make_env(tmp_path)
        result = env.preprocess("{{ name: str }}")
        assert ": str" not in result
        assert "{{ name }}" in result

    def test_untyped_variable_not_modified(self, tmp_path):
        env = make_env(tmp_path)
        result = env.preprocess("{{ name }}")
        assert "{{ name }}" in result

    def test_multiple_variables_all_registered(self, tmp_path):
        env = make_env(tmp_path)
        env.preprocess("{{ x: int }} {{ y: float }} {{ z }}")
        assert env.type_registry["x"] is int
        assert env.type_registry["y"] is float
        assert "z" not in env.type_registry  # untyped, not registered

    def test_whitespace_variants_are_matched(self, tmp_path):
        env = make_env(tmp_path)
        env.preprocess("{{x:int}}")
        # pattern requires \s* so no-space should still match
        assert env.type_registry.get("x") is int

    def test_registry_accumulates_across_calls(self, tmp_path):
        env = make_env(tmp_path)
        env.preprocess("{{ a: int }}")
        env.preprocess("{{ b: float }}")
        assert "a" in env.type_registry
        assert "b" in env.type_registry

    def test_later_type_overwrites_earlier(self, tmp_path):
        env = make_env(tmp_path)
        env.preprocess("{{ x: int }}")
        env.preprocess("{{ x: float }}")
        assert env.type_registry["x"] is float


class TestUndeclaredVariables:
    def test_undeclared_variable_is_tracked(self, tmp_path):
        env = make_env(tmp_path)
        env.update_undeclared_variables("{{ name }}")
        assert "name" in env.undeclared_variables

    def test_declared_variable_not_tracked(self, tmp_path):
        env = make_env(tmp_path)
        env.globals["name"] = "already set"
        env.update_undeclared_variables("{{ name }}")
        assert "name" not in env.undeclared_variables

    def test_typed_variable_uses_registry_type(self, tmp_path):
        env = make_env(tmp_path)
        env.preprocess("{{ count: int }}")
        env.update_undeclared_variables("{{ count }}")
        assert env.undeclared_variables["count"] is int

    def test_untyped_undeclared_defaults_to_str(self, tmp_path):
        env = make_env(tmp_path)
        env.update_undeclared_variables("{{ name }}")
        assert env.undeclared_variables["name"] is str

    def test_no_undeclared_variables_leaves_dict_empty(self, tmp_path):
        env = make_env(tmp_path)
        # A template with no variables
        env.update_undeclared_variables("hello world")
        assert env.undeclared_variables == {}

    def test_undeclared_accumulates_across_calls(self, tmp_path):
        env = make_env(tmp_path)
        env.update_undeclared_variables("{{ a }}")
        env.update_undeclared_variables("{{ b }}")
        assert "a" in env.undeclared_variables
        assert "b" in env.undeclared_variables

    def test_control_flow_variables_detected(self, tmp_path):
        env = make_env(tmp_path)
        env.update_undeclared_variables("{% for item in items %}{{ item }}{% endfor %}")
        # 'items' is undeclared; 'item' is the loop variable, not undeclared
        assert "items" in env.undeclared_variables
        assert "item" not in env.undeclared_variables


class TestFromString:
    def test_renders_simple_variable(self, tmp_path):
        env = make_env(tmp_path)
        t = env.from_string("Hello {{ name }}")
        assert t.render(name="world") == "Hello world"

    def test_typed_variable_stripped_before_render(self, tmp_path):
        env = make_env(tmp_path)
        t = env.from_string("{{ count: int }}")
        assert t.render(count=42) == "42"

    def test_registers_undeclared_via_from_string(self, tmp_path):
        env = make_env(tmp_path)
        env.from_string("{{ name: str }} {{ age: int }}")
        assert env.undeclared_variables["name"] is str
        assert env.undeclared_variables["age"] is int

    def test_multiple_templates_accumulate_undeclared(self, tmp_path):
        env = make_env(tmp_path)
        env.from_string("{{ a }}")
        env.from_string("{{ b }}")
        assert "a" in env.undeclared_variables
        assert "b" in env.undeclared_variables


class TestGetTemplate:
    def test_renders_simple_template_file(self, tmp_path):
        write_template(tmp_path, "hello.txt", "Hello {{ name }}")
        env = make_env(tmp_path)
        t = env.get_template("hello.txt")
        assert t.render(name="world") == "Hello world"

    def test_typed_variable_stripped_in_file(self, tmp_path):
        write_template(tmp_path, "t.txt", "{{ count: int }}")
        env = make_env(tmp_path)
        t = env.get_template("t.txt")
        assert t.render(count=5) == "5"

    def test_registers_type_from_file(self, tmp_path):
        write_template(tmp_path, "t.txt", "{{ score: float }}")
        env = make_env(tmp_path)
        env.get_template("t.txt")
        assert env.type_registry["score"] is float

    def test_registers_undeclared_from_file(self, tmp_path):
        write_template(tmp_path, "t.txt", "{{ name: str }} {{ age: int }}")
        env = make_env(tmp_path)
        env.get_template("t.txt")
        assert env.undeclared_variables["name"] is str
        assert env.undeclared_variables["age"] is int

    def test_passing_template_instance_returns_it(self, tmp_path):
        write_template(tmp_path, "t.txt", "{{ x }}")
        env = make_env(tmp_path)
        t = env.get_template("t.txt")
        assert env.get_template(t) is t

    def test_multiple_files_accumulate_undeclared(self, tmp_path):
        write_template(tmp_path, "a.txt", "{{ foo }}")
        write_template(tmp_path, "b.txt", "{{ bar }}")
        env = make_env(tmp_path)
        env.get_template("a.txt")
        env.get_template("b.txt")
        assert "foo" in env.undeclared_variables
        assert "bar" in env.undeclared_variables

    def test_same_variable_in_multiple_files(self, tmp_path):
        write_template(tmp_path, "a.txt", "{{ name: str }}")
        write_template(tmp_path, "b.txt", "{{ name }}")
        env = make_env(tmp_path)
        env.get_template("a.txt")
        env.get_template("b.txt")
        # type from first registration should be preserved
        assert env.undeclared_variables["name"] is str
