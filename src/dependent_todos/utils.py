"""Utility functions for the dependent todos application."""

import re

from dependent_todos.constants import TASK_ID_MAX_LEN
from dependent_todos.constants import (
    MAX_MESSAGE_DISPLAY_LENGTH,
    MESSAGE_TRUNCATE_LENGTH,
    TRUNCATION_SUFFIX,
)


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

    Truncates at word boundaries when max_length is exceeded, ensuring
    complete words are preserved rather than cutting words in the middle.

    Args:
        message: Task message to generate ID from
        existing_ids: Set of existing task IDs to avoid conflicts
        max_length: Maximum length of the ID

    Returns:
        Unique slug ID
    """
    # First, create a full slug without length limit
    full_slug = slugify(message)

    # Handle empty slug case
    if not full_slug:
        full_slug = "task"

    # If it fits and is unique, return it
    if len(full_slug) <= max_length and full_slug not in existing_ids:
        return full_slug

    # Need to truncate, but respect word boundaries
    # Split by hyphens (word boundaries in slugs)
    parts = full_slug.split("-")

    # Build slug by adding complete parts until we hit the limit
    result_parts = []
    current_length = 0

    for part in parts:
        # Calculate length if we add this part (+1 for hyphen, except for first part)
        additional_length = len(part) + (1 if result_parts else 0)

        if current_length + additional_length <= max_length:
            result_parts.append(part)
            current_length += additional_length
        else:
            break

    # If no parts fit, take as much of the first part as possible
    if not result_parts:
        base_slug = parts[0][:max_length] if parts else "task"
    else:
        base_slug = "-".join(result_parts)

    # Ensure we don't end with a hyphen
    base_slug = base_slug.rstrip("-")

    # If still empty, use a fallback
    if not base_slug:
        base_slug = "task"

    if base_slug not in existing_ids:
        return base_slug

    # If base slug exists, append numbers until unique
    counter = 1
    while True:
        candidate = f"{base_slug}-{counter}"
        if len(candidate) > max_length:
            # Truncate base_slug to make room for counter, but respect word boundaries
            available_length = max_length - len(str(counter)) - 1
            if available_length > 0:
                # Re-apply word boundary truncation to the available length
                truncated_parts = []
                temp_length = 0
                for part in parts:
                    additional_length = len(part) + (1 if truncated_parts else 0)
                    if temp_length + additional_length <= available_length:
                        truncated_parts.append(part)
                        temp_length += additional_length
                    else:
                        break
                if truncated_parts:
                    base_slug = "-".join(truncated_parts).rstrip("-")
                else:
                    base_slug = parts[0][:available_length] if parts else "task"
                if not base_slug:
                    base_slug = "task"
            else:
                base_slug = "task"
            candidate = f"{base_slug}-{counter}"

        if candidate not in existing_ids:
            return candidate
        counter += 1


def truncate(message: str):
    if len(message) > MAX_MESSAGE_DISPLAY_LENGTH:
        message = message[:MESSAGE_TRUNCATE_LENGTH] + TRUNCATION_SUFFIX
    return message
