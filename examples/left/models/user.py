"""User model."""

from __future__ import annotations

from models.base import BaseModel


class User(BaseModel):
    """Represents an application user."""

    def __init__(self, name: str, email: str) -> None:
        super().__init__()
        self.name = name
        self.email = email

    def to_dict(self) -> dict[str, str]:
        """Serialize to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
        }

    def __repr__(self) -> str:
        return f"User(name={self.name!r}, email={self.email!r})"
