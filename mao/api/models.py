"""Data models for API endpoints.

This module defines Pydantic models for request/response validation.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class ContactFormRequest(BaseModel):
    """Contact form submission request model.

    Attributes:
        name: Full name of the person submitting the form (2-100 characters)
        email: Valid email address
        message: Message content (10-5000 characters)
    """

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Full name of the person submitting the form",
        examples=["John Doe"],
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address",
        examples=["john.doe@example.com"],
    )
    message: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Message content",
        examples=["I would like to inquire about your services..."],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate name field.

        Args:
            value: Name to validate

        Returns:
            Validated and trimmed name

        Raises:
            ValueError: If name contains only whitespace or invalid characters
        """
        name = value.strip()
        if not name:
            raise ValueError("Name cannot be empty or only whitespace")
        if not all(char.isalnum() or char.isspace() or char in "'-." for char in name):
            raise ValueError("Name contains invalid characters")
        return name

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        """Validate message field.

        Args:
            value: Message to validate

        Returns:
            Validated and trimmed message

        Raises:
            ValueError: If message contains only whitespace
        """
        message = value.strip()
        if not message:
            raise ValueError("Message cannot be empty or only whitespace")
        return message


class ContactFormResponse(BaseModel):
    """Contact form submission response model.

    Attributes:
        status: Status of the submission (success or error)
        message: Human-readable message about the result
        submission_id: Unique identifier for the submission (only on success)
        timestamp: ISO 8601 formatted timestamp of the response
    """

    status: Literal["success", "error"] = Field(
        ...,
        description="Status of the submission",
    )
    message: str = Field(
        ...,
        description="Human-readable message about the result",
        examples=["Contact form submitted successfully"],
    )
    submission_id: str | None = Field(
        default=None,
        description="Unique identifier for the submission",
        examples=["cf_20260202_123456_abc123"],
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO 8601 formatted timestamp of the response",
        examples=["2026-02-02T12:34:56.789123"],
    )


class ContactFormEntry(BaseModel):
    """Stored contact form entry.

    Attributes:
        submission_id: Unique identifier
        name: Submitter's name
        email: Submitter's email
        message: Message content
        submitted_at: ISO 8601 formatted timestamp of submission
        ip_address: Optional IP address of the submitter
    """

    submission_id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Submitter's name")
    email: str = Field(..., description="Submitter's email")
    message: str = Field(..., description="Message content")
    submitted_at: str = Field(..., description="ISO 8601 formatted timestamp of submission")
    ip_address: str | None = Field(
        default=None,
        description="IP address of the submitter",
    )
