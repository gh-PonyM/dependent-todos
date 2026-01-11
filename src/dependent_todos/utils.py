"""Utility functions for the dependent todos application."""

import re

from dependent_todos.constants import TASK_ID_MAX_LEN


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a URL-compatible slug.

    Args:
        text: Text to convert
        max_length: Maximum length of the slug

    Returns:
        Slugified version of the text
    """
    # Convert to lowercase
    slug = text.lower()

    # Replace spaces and special chars with hyphens
    slug = re.sub(
        r"[^\w\s-]", "", slug
    )  # Remove special chars except spaces and hyphens
    slug = re.sub(
        r"[-\s]+", "-", slug
    )  # Replace spaces and multiple hyphens with single hyphen

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    # Truncate to max length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")

    return slug


def generate_unique_id(
    message: str, existing_ids: set[str], max_length: int = TASK_ID_MAX_LEN
) -> str:
    """Generate a unique slug ID from a message.

    Args:
        message: Task message to generate ID from
        existing_ids: Set of existing task IDs to avoid conflicts
        max_length: Maximum length of the ID

    Returns:
        Unique slug ID
    """
    # TODO: rewrite this in a way that a max length is given but: define split chars, and return only complete chunks of a word/split.
    # A part of a split should not be added truncated
    base_slug = slugify(message, max_length)

    if base_slug not in existing_ids:
        return base_slug

    # If base slug exists, append numbers until unique
    counter = 1
    while True:
        candidate = f"{base_slug}-{counter}"
        if len(candidate) > max_length:
            # Truncate base_slug to make room for counter
            base_slug = base_slug[: max_length - len(str(counter)) - 1]
            candidate = f"{base_slug}-{counter}"

        if candidate not in existing_ids:
            return candidate
        counter += 1
