import pytest

from boilerplater.__main__ import boilerplater_config


@pytest.fixture(autouse=True)
def isolate_boilerplater_dirs(tmp_path):
    """
    Point templates_dir/data_dir/modules_dir at empty, per-test directories.

    Without this, the singleton config falls back to whatever BOILERPLATER_*
    env vars or ~/.local/opt/boilerplater directories happen to exist on the
    machine running the tests, which is what made some tests pass locally
    but fail in CI (or on any other clean machine).
    """
    templates_dir = tmp_path / "conftest_templates"
    templates_dir.mkdir()
    data_dir = tmp_path / "conftest_data"
    data_dir.mkdir()
    modules_dir = tmp_path / "conftest_modules"
    modules_dir.mkdir()

    boilerplater_config.templates_dir = templates_dir
    boilerplater_config.data_dir = data_dir
    boilerplater_config.modules_dir = modules_dir

    yield
