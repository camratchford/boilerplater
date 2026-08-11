from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from boilerplater.template_config import (
    BaseTemplateConfig,
    ModuleTemplateConfig,
    ProjectTemplateConfig,
)


class TestBaseTemplateConfigDefaults:
    def test_name_is_required(self):
        with pytest.raises(ValidationError):
            BaseTemplateConfig()

    def test_default_field_values(self):
        config = BaseTemplateConfig(name="base")
        assert config.description == ""
        assert config.path is None
        assert config.requirements == []
        assert config.available_modules is None
        assert config.variable_default_values == {}
        assert config.exclude_patterns == ["boilerplater.yml"]
        assert config.force_copy_patterns == ["*.j2"]
        assert config.cleanup_patterns == [".placeholder", ".gitkeep"]
        assert config.run_on_complete_scripts == []


class TestBaseTemplateConfigEquality:
    def test_equal_to_other_config_with_same_name(self):
        a = BaseTemplateConfig(name="shared")
        b = BaseTemplateConfig(name="shared")
        assert a == b

    def test_not_equal_to_other_config_with_different_name(self):
        a = BaseTemplateConfig(name="a")
        b = BaseTemplateConfig(name="b")
        assert a != b

    def test_equal_to_matching_string(self):
        config = BaseTemplateConfig(name="docker")
        assert config == "docker"

    def test_not_equal_to_non_matching_string(self):
        config = BaseTemplateConfig(name="docker")
        assert config != "other"

    def test_membership_check_against_string_list(self):
        config = BaseTemplateConfig(name="docker")
        assert config in ["docker", "other"]


class TestBaseTemplateConfigHash:
    def test_hash_matches_name_hash(self):
        config = BaseTemplateConfig(name="docker")
        assert hash(config) == hash("docker")

    def test_configs_with_same_name_share_hash(self):
        a = BaseTemplateConfig(name="docker")
        b = BaseTemplateConfig(name="docker")
        assert hash(a) == hash(b)

    def test_usable_as_set_member_for_dedupe(self):
        a = BaseTemplateConfig(name="docker")
        b = BaseTemplateConfig(name="docker", description="different")
        assert len({a, b}) == 1


class TestModuleTemplateConfigValidateCategories:
    def test_unset_target_categories_becomes_empty_list(self, tmp_path):
        config = ModuleTemplateConfig(name="mod", path=tmp_path)
        assert config.target_categories == []

    def test_star_expands_to_all_categories(self, tmp_path):
        mock_config = MagicMock()
        mock_config.list_categories.return_value = ["python", "rust"]
        with patch("boilerplater.config.BoilerplaterConfig", return_value=mock_config):
            config = ModuleTemplateConfig(
                name="mod", path=tmp_path, target_categories="*"
            )
        assert config.target_categories == ["python", "rust"]

    def test_valid_categories_are_kept(self, tmp_path):
        mock_config = MagicMock()
        mock_config.list_categories.return_value = ["python", "rust"]
        with patch("boilerplater.config.BoilerplaterConfig", return_value=mock_config):
            config = ModuleTemplateConfig(
                name="mod", path=tmp_path, target_categories=["python"]
            )
        assert config.target_categories == ["python"]

    def test_invalid_category_raises_validation_error(self, tmp_path):
        mock_config = MagicMock()
        mock_config.list_categories.return_value = ["python"]
        with patch("boilerplater.config.BoilerplaterConfig", return_value=mock_config):
            with pytest.raises(ValidationError):
                ModuleTemplateConfig(
                    name="mod", path=tmp_path, target_categories=["rust"]
                )

    def test_one_invalid_category_among_valid_ones_raises(self, tmp_path):
        mock_config = MagicMock()
        mock_config.list_categories.return_value = ["python"]
        with patch("boilerplater.config.BoilerplaterConfig", return_value=mock_config):
            with pytest.raises(ValidationError):
                ModuleTemplateConfig(
                    name="mod", path=tmp_path, target_categories=["python", "rust"]
                )


class TestProjectTemplateConfigValidateAddOns:
    def test_category_is_required(self, tmp_path):
        with pytest.raises(ValidationError):
            ProjectTemplateConfig(name="proj", path=tmp_path)

    def test_no_add_ons_by_default(self, tmp_path):
        config = ProjectTemplateConfig(name="proj", category="python", path=tmp_path)
        assert config.add_ons == []

    def test_valid_add_on_is_kept(self, tmp_path):
        mock_config = MagicMock()
        mock_config.module_configs = {"docker": MagicMock()}
        with patch("boilerplater.config.BoilerplaterConfig", return_value=mock_config):
            config = ProjectTemplateConfig(
                name="proj", category="python", path=tmp_path, add_ons=["docker"]
            )
        assert config.add_ons == ["docker"]

    def test_invalid_add_on_raises_key_error(self, tmp_path):
        mock_config = MagicMock()
        mock_config.module_configs = {}
        with patch("boilerplater.config.BoilerplaterConfig", return_value=mock_config):
            with pytest.raises(KeyError):
                ProjectTemplateConfig(
                    name="proj", category="python", path=tmp_path, add_ons=["missing"]
                )

    def test_one_invalid_add_on_among_valid_ones_raises(self, tmp_path):
        mock_config = MagicMock()
        mock_config.module_configs = {"docker": MagicMock()}
        with patch("boilerplater.config.BoilerplaterConfig", return_value=mock_config):
            with pytest.raises(KeyError):
                ProjectTemplateConfig(
                    name="proj",
                    category="python",
                    path=tmp_path,
                    add_ons=["docker", "missing"],
                )
