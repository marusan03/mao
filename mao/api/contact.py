"""Contact form API endpoint.

This module implements the contact form submission endpoint with validation,
error handling, and storage.
"""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from mao.api.models import ContactFormEntry, ContactFormRequest, ContactFormResponse
from mao.api.storage import FileStorageBackend, generate_submission_id

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["contact"])

# Initialize storage backend
storage = FileStorageBackend()


@router.post(
    "/contact",
    response_model=ContactFormResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Contact form submitted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Contact form submitted successfully",
                        "submission_id": "cf_20260202_123456_abc123",
                        "timestamp": "2026-02-02T12:34:56.789123",
                    }
                }
            },
        },
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Validation failed: name cannot be empty",
                        "submission_id": None,
                        "timestamp": "2026-02-02T12:34:56.789123",
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Failed to process contact form submission",
                        "submission_id": None,
                        "timestamp": "2026-02-02T12:34:56.789123",
                    }
                }
            },
        },
    },
    summary="Submit a contact form",
    description="""
    Submit a contact form with name, email, and message.

    **Validation Rules:**
    - Name: 2-100 characters, alphanumeric with spaces, hyphens, apostrophes, and periods
    - Email: Valid email address format
    - Message: 10-5000 characters, non-empty after trimming whitespace

    **Storage:**
    - Submissions are stored in `.mao/contact_forms/` directory
    - Each submission gets a unique ID in format: `cf_YYYYMMDD_HHMMSS_hash`

    **Rate Limiting:**
    - Consider implementing rate limiting in production to prevent abuse
    """,
)
async def submit_contact_form(
    request: Request,
    form_data: ContactFormRequest,
) -> ContactFormResponse:
    """Submit a contact form.

    Args:
        request: FastAPI request object (for getting client IP)
        form_data: Validated contact form data

    Returns:
        ContactFormResponse with submission details

    Raises:
        HTTPException: On validation or storage errors
    """
    try:
        # Generate unique submission ID
        submission_id = generate_submission_id()

        # Get client IP address (for logging/analytics)
        client_ip = request.client.host if request.client else None

        # Create entry
        entry = ContactFormEntry(
            submission_id=submission_id,
            name=form_data.name,
            email=form_data.email,
            message=form_data.message,
            submitted_at=datetime.now().isoformat(),
            ip_address=client_ip,
        )

        # Save to storage
        await storage.save(entry)

        # Log successful submission
        logger.info(
            "Contact form submitted",
            extra={
                "submission_id": submission_id,
                "email": form_data.email,
                "ip_address": client_ip,
            },
        )

        return ContactFormResponse(
            status="success",
            message="Contact form submitted successfully",
            submission_id=submission_id,
        )

    except ValueError as e:
        # Validation errors (should be caught by Pydantic, but handle edge cases)
        logger.warning(
            "Contact form validation error",
            extra={"error": str(e), "form_data": form_data.model_dump()},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation failed: {e}",
        ) from e

    except Exception as e:
        # Unexpected errors
        logger.error(
            "Contact form submission failed",
            extra={"error": str(e), "form_data": form_data.model_dump()},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process contact form submission",
        ) from e


@router.get(
    "/contact/{submission_id}",
    response_model=ContactFormEntry,
    responses={
        200: {
            "description": "Contact form entry found",
            "content": {
                "application/json": {
                    "example": {
                        "submission_id": "cf_20260202_123456_abc123",
                        "name": "John Doe",
                        "email": "john.doe@example.com",
                        "message": "I would like to inquire about your services...",
                        "submitted_at": "2026-02-02T12:34:56.789123",
                        "ip_address": "192.168.1.1",
                    }
                }
            },
        },
        404: {"description": "Contact form entry not found"},
    },
    summary="Get a contact form submission by ID",
    description="Retrieve a previously submitted contact form by its unique submission ID.",
)
async def get_contact_form(submission_id: str) -> ContactFormEntry:
    """Get a contact form submission by ID.

    Args:
        submission_id: Unique submission ID

    Returns:
        ContactFormEntry if found

    Raises:
        HTTPException: If submission not found
    """
    entry = await storage.get(submission_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact form submission {submission_id} not found",
        )
    return entry


@router.get(
    "/contact",
    response_model=list[ContactFormEntry],
    summary="List all contact form submissions",
    description="""
    List all contact form submissions, sorted by submission time (newest first).

    **Note:** In production, consider adding pagination and authentication
    to protect this endpoint.
    """,
)
async def list_contact_forms() -> list[ContactFormEntry]:
    """List all contact form submissions.

    Returns:
        List of all stored contact form entries
    """
    return await storage.list_all()


@router.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Custom exception handler for HTTPException.

    Args:
        request: FastAPI request object
        exc: HTTPException instance

    Returns:
        JSONResponse with error details
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=ContactFormResponse(
            status="error",
            message=str(exc.detail),
            submission_id=None,
        ).model_dump(),
    )


@router.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Generic exception handler for unexpected errors.

    Args:
        request: FastAPI request object
        exc: Exception instance

    Returns:
        JSONResponse with error details
    """
    logger.error("Unexpected error in contact form API", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ContactFormResponse(
            status="error",
            message="An unexpected error occurred",
            submission_id=None,
        ).model_dump(),
    )
