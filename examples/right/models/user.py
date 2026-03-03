"""User model."""

from __future__ import annotations

from models.base import BaseModel


class User(BaseModel):
    """Represents an application user."""

    def __init__(self, name: str, email: str, role: str = "viewer") -> None:
        super().__init__()
        self.name = name
        self.email = email
        self.role = role

    def to_dict(self) -> dict[str, str]:
        """Serialize to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
        }

    def is_admin(self) -> bool:
        """Check if the user has admin privileges."""
        return self.role == "admin"

    def __repr__(self) -> str:
        return f"User(name={self.name!r}, email={self.email!r}, role={self.role!r})"
