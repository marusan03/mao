"""FastAPI application factory for MAO API.

This module provides the main FastAPI application with all routes and middleware.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mao.api.contact import router as contact_router
from mao.version import __version__

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None during application runtime
    """
    # Startup
    logger.info("Starting MAO API server")
    logger.info("Version: %s", __version__)

    yield

    # Shutdown
    logger.info("Shutting down MAO API server")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="MAO API",
        description="""
        Multi-Agent Orchestrator API

        This API provides endpoints for external integrations with the MAO system.

        ## Features

        - **Contact Form**: Submit and retrieve contact form submissions
        - **Validation**: Automatic request validation with Pydantic
        - **Error Handling**: Comprehensive error responses
        - **Documentation**: Interactive API documentation (this page)

        ## Storage

        - Contact form submissions are stored in `.mao/contact_forms/` directory
        - Each submission is saved as a JSON file with a unique ID
        """,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(contact_router)

    # Root endpoint
    @app.get(
        "/",
        summary="API Root",
        description="Get basic information about the API",
        tags=["root"],
    )
    async def root() -> JSONResponse:
        """Root endpoint providing API information.

        Returns:
            JSONResponse with API details
        """
        return JSONResponse(
            content={
                "name": "MAO API",
                "version": __version__,
                "description": "Multi-Agent Orchestrator API",
                "docs": "/docs",
                "openapi": "/openapi.json",
            }
        )

    # Health check endpoint
    @app.get(
        "/health",
        summary="Health Check",
        description="Check if the API is running",
        tags=["health"],
    )
    async def health_check() -> JSONResponse:
        """Health check endpoint.

        Returns:
            JSONResponse indicating service health
        """
        return JSONResponse(
            content={
                "status": "healthy",
                "version": __version__,
            }
        )

    return app


# Create default app instance
app = create_app()


def main() -> None:
    """Main entry point for running the API server via CLI.

    This function is used by the mao-api command.
    """
    import uvicorn

    uvicorn.run(
        "mao.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
