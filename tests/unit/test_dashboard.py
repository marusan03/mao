"""Test Dashboard UI module"""
import pytest


class TestDashboard:
    """Test Dashboard functionality"""

    def test_dashboard_import(self):
        """Test that Dashboard can be imported without errors"""
        from mao.ui.dashboard import Dashboard
        assert Dashboard is not None

    def test_dashboard_has_required_methods(self):
        """Test that Dashboard has required methods"""
        from mao.ui.dashboard import Dashboard
        # Check that class has expected methods
        assert hasattr(Dashboard, 'compose')
        assert hasattr(Dashboard, 'on_mount')

    def test_typing_imports(self):
        """Test that typing module imports are correct"""
        # This test ensures List, Dict, Any are properly imported
        import mao.ui.dashboard as dashboard_module
        # Should not raise ImportError or NameError
        assert hasattr(dashboard_module, 'Dashboard')
