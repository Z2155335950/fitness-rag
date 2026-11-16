"""Compatibility import for the old parser-side linker location.

The maintained implementation lives in :mod:`src.query.entity_linker`.
"""

from src.query.entity_linker import EntityLinker
from src.query.schema import Entity, EntityType

__all__ = ["EntityLinker", "Entity", "EntityType"]
