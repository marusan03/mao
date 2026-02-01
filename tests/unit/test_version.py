"""Test version module"""
import pytest

from mao.version import __version__, get_git_commit


class TestVersion:
    """Test version functionality"""

    def test_version_format(self):
        """Test version format"""
        assert __version__ is not None
        assert isinstance(__version__, str)
        # Should match semver format (x.y.z)
        parts = __version__.split(".")
        assert len(parts) >= 2

    def test_get_git_commit(self):
        """Test getting git commit"""
        commit = get_git_commit()
        # Should return commit hash or None
        assert commit is None or isinstance(commit, str)
        if commit:
            # Should be hex string
            assert all(c in "0123456789abcdef" for c in commit.lower())
