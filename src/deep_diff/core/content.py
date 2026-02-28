"""Hash-based content comparison engine."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from deep_diff.core.models import FileComparison, FileStatus

if TYPE_CHECKING:
    from pathlib import Path

_HASH_BUFFER_SIZE = 65536


class ContentComparator:
    """Compares files by streaming hash digest.

    Computes a cryptographic hash (default SHA-256) of each file in a
    streaming fashion to avoid loading entire files into memory.  Two files
    are considered identical when their digests match.
    """

    def __init__(self, *, hash_algo: str = "sha256") -> None:
        """Initialize with hash algorithm configuration.

        Args:
            hash_algo: Hash algorithm name accepted by :func:`hashlib.new`.
                Defaults to ``"sha256"``.
        """
        self._hash_algo = hash_algo

    def compare(
        self,
        left: Path,
        right: Path,
        *,
        relative_path: str = "",
    ) -> FileComparison:
        """Compare two files by streaming hash.

        Args:
            left: Path to the left file.
            right: Path to the right file.
            relative_path: Relative path label for the result.
                Defaults to ``left.name`` when empty.

        Returns:
            A FileComparison with status, content hashes, and similarity.
        """
        if not relative_path:
            relative_path = left.name

        left_hash = self._hash_file(left)
        right_hash = self._hash_file(right)

        if left_hash == right_hash:
            status = FileStatus.identical
            similarity: float | None = 1.0
        else:
            status = FileStatus.modified
            similarity = None

        return FileComparison(
            relative_path=relative_path,
            status=status,
            left_path=left,
            right_path=right,
            content_hash_left=left_hash,
            content_hash_right=right_hash,
            similarity=similarity,
        )

    def _hash_file(self, path: Path) -> str:
        """Compute the hex digest of a file using streaming reads.

        Args:
            path: Path to the file to hash.

        Returns:
            Hexadecimal digest string.
        """
        hasher = hashlib.new(self._hash_algo)
        with path.open("rb") as f:
            while True:
                chunk = f.read(_HASH_BUFFER_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
