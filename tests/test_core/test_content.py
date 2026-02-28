"""Tests for deep_diff.core.content."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import TYPE_CHECKING

import pytest

from deep_diff.core.content import _HASH_BUFFER_SIZE, ContentComparator
from deep_diff.core.models import FileComparison, FileStatus

if TYPE_CHECKING:
    from pathlib import Path

_EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class TestContentComparatorInit:
    """Verify constructor defaults and explicit settings."""

    def test_default_hash_algo(self) -> None:
        comp = ContentComparator()
        assert comp._hash_algo == "sha256"

    def test_custom_hash_algo(self) -> None:
        comp = ContentComparator(hash_algo="md5")
        assert comp._hash_algo == "md5"

    def test_custom_hash_algo_blake2b(self) -> None:
        comp = ContentComparator(hash_algo="blake2b")
        assert comp._hash_algo == "blake2b"


class TestContentComparatorIdentical:
    """Identical files produce matching hashes and similarity 1.0."""

    def test_identical_text_files(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("hello world\n")
        right.write_text("hello world\n")

        result = ContentComparator().compare(left, right)

        assert result.status == FileStatus.identical
        assert result.similarity == 1.0
        assert result.content_hash_left == result.content_hash_right

    def test_identical_binary_files(self, tmp_path: Path) -> None:
        data = b"\x00\x01\x02\x03\xff"
        left = tmp_path / "a.bin"
        right = tmp_path / "b.bin"
        left.write_bytes(data)
        right.write_bytes(data)

        result = ContentComparator().compare(left, right)

        assert result.status == FileStatus.identical
        assert result.similarity == 1.0
        assert result.content_hash_left == result.content_hash_right

    def test_identical_empty_files(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("")
        right.write_text("")

        result = ContentComparator().compare(left, right)

        assert result.status == FileStatus.identical
        assert result.similarity == 1.0


class TestContentComparatorModified:
    """Different files produce different hashes and status modified."""

    def test_different_text_files(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("hello\n")
        right.write_text("world\n")

        result = ContentComparator().compare(left, right)

        assert result.status == FileStatus.modified
        assert result.similarity is None
        assert result.content_hash_left != result.content_hash_right

    def test_different_binary_files(self, binary_files: tuple[Path, Path]) -> None:
        left, right = binary_files
        result = ContentComparator().compare(left, right)

        assert result.status == FileStatus.modified
        assert result.content_hash_left != result.content_hash_right

    def test_one_byte_difference(self, tmp_path: Path) -> None:
        left = tmp_path / "a.bin"
        right = tmp_path / "b.bin"
        left.write_bytes(b"identical prefix\x00")
        right.write_bytes(b"identical prefix\x01")

        result = ContentComparator().compare(left, right)

        assert result.status == FileStatus.modified
        assert result.content_hash_left != result.content_hash_right


class TestContentComparatorHashes:
    """Verify hash output format and field population."""

    def test_hash_format_is_hex_string(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("test\n")

        result = ContentComparator().compare(f, f)

        assert result.content_hash_left is not None
        int(result.content_hash_left, 16)  # raises ValueError if not hex

    def test_hash_length_sha256(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("test\n")

        result = ContentComparator().compare(f, f)

        assert result.content_hash_left is not None
        assert len(result.content_hash_left) == 64

    def test_hash_length_md5(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("test\n")

        result = ContentComparator(hash_algo="md5").compare(f, f)

        assert result.content_hash_left is not None
        assert len(result.content_hash_left) == 32

    def test_hash_is_deterministic(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("deterministic\n")
        comp = ContentComparator()

        result1 = comp.compare(f, f)
        result2 = comp.compare(f, f)

        assert result1.content_hash_left == result2.content_hash_left

    def test_content_hash_left_populated(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("left\n")
        right.write_text("right\n")

        result = ContentComparator().compare(left, right)
        assert result.content_hash_left is not None

    def test_content_hash_right_populated(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("left\n")
        right.write_text("right\n")

        result = ContentComparator().compare(left, right)
        assert result.content_hash_right is not None

    def test_hashes_match_for_identical(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("same\n")
        right.write_text("same\n")

        result = ContentComparator().compare(left, right)
        assert result.content_hash_left == result.content_hash_right

    def test_hashes_differ_for_modified(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("alpha\n")
        right.write_text("beta\n")

        result = ContentComparator().compare(left, right)
        assert result.content_hash_left != result.content_hash_right


class TestContentComparatorHashAlgo:
    """Verify configurable hash algorithm."""

    def test_sha256_default(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("test\n")

        result = ContentComparator().compare(f, f)

        assert result.content_hash_left is not None
        assert len(result.content_hash_left) == 64

    def test_md5_produces_shorter_hash(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("test\n")

        result = ContentComparator(hash_algo="md5").compare(f, f)

        assert result.content_hash_left is not None
        assert len(result.content_hash_left) == 32

    def test_sha512_produces_longer_hash(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("test\n")

        result = ContentComparator(hash_algo="sha512").compare(f, f)

        assert result.content_hash_left is not None
        assert len(result.content_hash_left) == 128

    def test_invalid_hash_algo_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("test\n")

        with pytest.raises(ValueError):
            ContentComparator(hash_algo="not_a_real_algo").compare(f, f)


class TestContentComparatorEmpty:
    """Edge cases with empty files."""

    def test_both_empty_identical(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("")
        right.write_text("")

        result = ContentComparator().compare(left, right)

        assert result.status == FileStatus.identical
        assert result.content_hash_left == result.content_hash_right

    def test_empty_vs_nonempty(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("")
        right.write_text("content\n")

        result = ContentComparator().compare(left, right)

        assert result.status == FileStatus.modified
        assert result.content_hash_left != result.content_hash_right

    def test_empty_file_has_known_sha256(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.txt"
        f.write_text("")

        result = ContentComparator().compare(f, f)

        assert result.content_hash_left == _EMPTY_SHA256


class TestContentComparatorLargeFile:
    """Verify streaming works for files larger than the buffer size."""

    def test_large_file_streaming(self, tmp_path: Path) -> None:
        data = b"x" * (_HASH_BUFFER_SIZE * 2)
        left = tmp_path / "large_a.bin"
        right = tmp_path / "large_b.bin"
        left.write_bytes(data)
        right.write_bytes(data)

        result = ContentComparator().compare(left, right)

        assert result.status == FileStatus.identical
        assert result.content_hash_left == result.content_hash_right

    def test_large_file_non_multiple_of_buffer(self, tmp_path: Path) -> None:
        data = b"x" * (_HASH_BUFFER_SIZE * 2 + 123)
        left = tmp_path / "large_a.bin"
        right = tmp_path / "large_b.bin"
        left.write_bytes(data)
        right.write_bytes(data)

        result = ContentComparator().compare(left, right)

        assert result.status == FileStatus.identical
        assert result.content_hash_left == result.content_hash_right

    def test_large_file_different(self, tmp_path: Path) -> None:
        left = tmp_path / "large_a.bin"
        right = tmp_path / "large_b.bin"
        left.write_bytes(b"x" * (_HASH_BUFFER_SIZE * 2))
        right.write_bytes(b"y" * (_HASH_BUFFER_SIZE * 2))

        result = ContentComparator().compare(left, right)

        assert result.status == FileStatus.modified
        assert result.content_hash_left != result.content_hash_right


class TestContentComparatorResults:
    """Verify result type, immutability, and field defaults."""

    def test_returns_file_comparison(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("test\n")

        result = ContentComparator().compare(f, f)
        assert isinstance(result, FileComparison)

    def test_result_is_frozen(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("test\n")

        result = ContentComparator().compare(f, f)
        with pytest.raises(FrozenInstanceError):
            result.status = FileStatus.modified  # type: ignore[misc]

    def test_relative_path_defaults_to_filename(self, tmp_path: Path) -> None:
        left = tmp_path / "myfile.txt"
        right = tmp_path / "other.txt"
        left.write_text("a\n")
        right.write_text("b\n")

        result = ContentComparator().compare(left, right)
        assert result.relative_path == "myfile.txt"

    def test_custom_relative_path(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("a\n")
        right.write_text("b\n")

        result = ContentComparator().compare(left, right, relative_path="custom/path.txt")
        assert result.relative_path == "custom/path.txt"

    def test_hunks_are_empty(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("hello\n")
        right.write_text("world\n")

        result = ContentComparator().compare(left, right)
        assert result.hunks == ()

    def test_left_and_right_paths_set(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("a\n")
        right.write_text("b\n")

        result = ContentComparator().compare(left, right)
        assert result.left_path == left
        assert result.right_path == right

    def test_similarity_is_1_for_identical(self, tmp_path: Path) -> None:
        f = tmp_path / "a.txt"
        f.write_text("same\n")

        result = ContentComparator().compare(f, f)
        assert result.similarity == 1.0

    def test_similarity_is_none_for_modified(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        right = tmp_path / "b.txt"
        left.write_text("alpha\n")
        right.write_text("beta\n")

        result = ContentComparator().compare(left, right)
        assert result.similarity is None


class TestContentComparatorPathValidation:
    """Verify explicit errors for missing or non-file paths."""

    def test_missing_left_raises(self, tmp_path: Path) -> None:
        right = tmp_path / "b.txt"
        right.write_text("content\n")
        missing = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError, match="Left path does not exist"):
            ContentComparator().compare(missing, right)

    def test_missing_right_raises(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        left.write_text("content\n")
        missing = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError, match="Right path does not exist"):
            ContentComparator().compare(left, missing)

    def test_directory_left_raises(self, tmp_path: Path) -> None:
        left = tmp_path / "dir"
        left.mkdir()
        right = tmp_path / "b.txt"
        right.write_text("content\n")

        with pytest.raises(IsADirectoryError, match="Left path is a directory"):
            ContentComparator().compare(left, right)

    def test_directory_right_raises(self, tmp_path: Path) -> None:
        left = tmp_path / "a.txt"
        left.write_text("content\n")
        right = tmp_path / "dir"
        right.mkdir()

        with pytest.raises(IsADirectoryError, match="Right path is a directory"):
            ContentComparator().compare(left, right)
