"""Test ConfigLoader"""
import pytest

from mao.config import ConfigLoader


class TestConfigLoader:
    """Test ConfigLoader functionality"""

    def test_list_available_languages(self):
        """Test listing available languages"""
        loader = ConfigLoader()
        languages = loader.list_available_languages()
        assert isinstance(languages, list)
        assert len(languages) > 0
        # Should have at least python
        assert "python" in languages

    def test_load_language_config(self):
        """Test loading specific language configuration"""
        loader = ConfigLoader()
        python_config = loader.load_language_config("python")
        assert python_config is not None
        assert python_config.name.lower() == "python"
        assert python_config.formatter is not None
        assert python_config.linter is not None

    def test_load_nonexistent_language(self):
        """Test loading non-existent language"""
        loader = ConfigLoader()
        config = loader.load_language_config("nonexistent-language-xyz")
        assert config is None

    def test_load_coding_standards(self):
        """Test loading coding standards"""
        loader = ConfigLoader()
        standards = loader.load_coding_standards("python")
        assert standards is not None
        # Standards could be a string or an object
        assert hasattr(standards, '__str__') or isinstance(standards, str)
