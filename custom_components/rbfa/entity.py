"""Base entity for the RBFA integration."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import RbfaCoordinator


class RbfaEntity(CoordinatorEntity[RbfaCoordinator]):
    """Defines a RBFA entity."""

    _attr_has_entity_name = True
