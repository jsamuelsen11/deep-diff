"""Git integration for deep-diff."""

from deep_diff.git.commands import GitError
from deep_diff.git.resolver import GitResolver, is_git_ref

__all__ = ["GitError", "GitResolver", "is_git_ref"]
