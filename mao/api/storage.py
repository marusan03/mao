"""Storage backend for contact form submissions.

This module provides file-based and in-memory storage for contact form entries.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Protocol

import aiofiles

from mao.api.models import ContactFormEntry


class StorageBackend(Protocol):
    """Protocol for contact form storage backends."""

    async def save(self, entry: ContactFormEntry) -> None:
        """Save a contact form entry.

        Args:
            entry: The contact form entry to save
        """
        ...

    async def get(self, submission_id: str) -> ContactFormEntry | None:
        """Retrieve a contact form entry by ID.

        Args:
            submission_id: The unique submission ID

        Returns:
            The contact form entry if found, None otherwise
        """
        ...

    async def list_all(self) -> list[ContactFormEntry]:
        """List all contact form entries.

        Returns:
            List of all stored contact form entries
        """
        ...


class FileStorageBackend:
    """File-based storage backend for contact form submissions.

    Stores each submission as a separate JSON file in the configured directory.

    Attributes:
        storage_dir: Directory where submissions are stored
    """

    def __init__(self, storage_dir: Path | str = ".mao/contact_forms") -> None:
        """Initialize the file storage backend.

        Args:
            storage_dir: Directory path for storing submissions
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, entry: ContactFormEntry) -> None:
        """Save a contact form entry to a JSON file.

        Args:
            entry: The contact form entry to save
        """
        file_path = self.storage_dir / f"{entry.submission_id}.json"
        async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
            await f.write(entry.model_dump_json(indent=2))

    async def get(self, submission_id: str) -> ContactFormEntry | None:
        """Retrieve a contact form entry by ID.

        Args:
            submission_id: The unique submission ID

        Returns:
            The contact form entry if found, None otherwise
        """
        file_path = self.storage_dir / f"{submission_id}.json"
        if not file_path.exists():
            return None

        try:
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                return ContactFormEntry(**data)
        except (json.JSONDecodeError, ValueError):
            return None

    async def list_all(self) -> list[ContactFormEntry]:
        """List all contact form entries.

        Returns:
            List of all stored contact form entries, sorted by submission time
        """
        entries = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                    content = await f.read()
                    data = json.loads(content)
                    entries.append(ContactFormEntry(**data))
            except (json.JSONDecodeError, ValueError):
                # Skip invalid files
                continue

        # Sort by submission time (newest first)
        entries.sort(key=lambda x: x.submitted_at, reverse=True)
        return entries


class InMemoryStorageBackend:
    """In-memory storage backend for contact form submissions.

    Useful for testing or temporary storage. Data is lost on process restart.

    Attributes:
        _storage: Dictionary storing entries by submission_id
    """

    def __init__(self) -> None:
        """Initialize the in-memory storage backend."""
        self._storage: dict[str, ContactFormEntry] = {}

    async def save(self, entry: ContactFormEntry) -> None:
        """Save a contact form entry to memory.

        Args:
            entry: The contact form entry to save
        """
        self._storage[entry.submission_id] = entry

    async def get(self, submission_id: str) -> ContactFormEntry | None:
        """Retrieve a contact form entry by ID.

        Args:
            submission_id: The unique submission ID

        Returns:
            The contact form entry if found, None otherwise
        """
        return self._storage.get(submission_id)

    async def list_all(self) -> list[ContactFormEntry]:
        """List all contact form entries.

        Returns:
            List of all stored contact form entries, sorted by submission time
        """
        entries = list(self._storage.values())
        entries.sort(key=lambda x: x.submitted_at, reverse=True)
        return entries


def generate_submission_id() -> str:
    """Generate a unique submission ID.

    Returns:
        A unique submission ID in the format: cf_YYYYMMDD_HHMMSS_hash
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    hash_suffix = hex(hash(now))[2:8]
    return f"cf_{timestamp}_{hash_suffix}"
