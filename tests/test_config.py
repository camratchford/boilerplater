from pathlib import Path

from boilerplater.__main__ import boilerplater_config


def write_module(modules_dir: Path, name: str) -> Path:
    module_dir = modules_dir / name
    module_dir.mkdir(parents=True)
    (module_dir / "boilerplater.yml").write_text("description: test module\n")
    return module_dir


class TestLoadModules:
    def test_calling_twice_does_not_duplicate_patterns(self, tmp_path):
        modules_dir = tmp_path / "modules"
        write_module(modules_dir, "docker")

        original_modules_dir = boilerplater_config.modules_dir
        boilerplater_config.modules_dir = modules_dir
        boilerplater_config.module_configs = {}
        boilerplater_config.cleanup_patterns = []
        boilerplater_config.exclude_patterns = []
        boilerplater_config.force_copy_patterns = []
        boilerplater_config.run_on_complete_scripts = []
        try:
            boilerplater_config.load_modules()
            boilerplater_config.load_modules()

            assert boilerplater_config.cleanup_patterns.count(".placeholder") == 1
            assert boilerplater_config.cleanup_patterns.count(".gitkeep") == 1
        finally:
            boilerplater_config.modules_dir = original_modules_dir
            boilerplater_config.module_configs = {}
            boilerplater_config.cleanup_patterns = []
            boilerplater_config.exclude_patterns = []
            boilerplater_config.force_copy_patterns = []
            boilerplater_config.run_on_complete_scripts = []

    def test_second_call_does_not_reload_known_module(self, tmp_path):
        modules_dir = tmp_path / "modules"
        write_module(modules_dir, "docker")

        original_modules_dir = boilerplater_config.modules_dir
        boilerplater_config.modules_dir = modules_dir
        boilerplater_config.module_configs = {}
        try:
            boilerplater_config.load_modules()
            first_config = boilerplater_config.module_configs["docker"]
            boilerplater_config.load_modules()
            second_config = boilerplater_config.module_configs["docker"]

            assert first_config is second_config
        finally:
            boilerplater_config.modules_dir = original_modules_dir
            boilerplater_config.module_configs = {}
