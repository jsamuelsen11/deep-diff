"""New helper utilities added in v2."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime


def generate_token(seed: str) -> str:
    """Generate a simple hash-based token."""
    raw = f"{seed}:{datetime.now(tz=UTC).isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def paginate(items: list, page: int = 1, per_page: int = 20) -> dict:
    """Paginate a list of items."""
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "items": items[start:end],
        "page": page,
        "per_page": per_page,
        "total": len(items),
    }
