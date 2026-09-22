"""Validation helpers that do not depend on Home Assistant runtime state."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def is_valid_timezone(value: str) -> bool:
    """Return whether value is a valid IANA timezone name."""
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return False
    return True
