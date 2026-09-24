"""Config-entry configuration helpers."""

from collections.abc import Mapping
from typing import Any


def effective_entry_data(entry: Any) -> dict[str, Any]:
    """Return initial config data with user-editable options applied."""
    return {**entry.data, **entry.options}
