"""Helpers for the RBFA integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry


def entry_option(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Return a setting from the entry options, falling back to its data."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)
