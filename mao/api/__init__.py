"""API module for MAO.

This module provides HTTP API endpoints for external integrations.
"""

from mao.api.app import create_app
from mao.api.contact import router as contact_router

__all__ = ["create_app", "contact_router"]
