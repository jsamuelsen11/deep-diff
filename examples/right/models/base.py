"""Base model with shared functionality."""

from __future__ import annotations

import uuid


class BaseModel:
    """Base class for all data models."""

    def __init__(self) -> None:
        self.id = str(uuid.uuid4())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseModel):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
