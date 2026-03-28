"""Diff processor — truncates diffs exceeding line limits.

Constitution III: Context is limited to 3000 lines to avoid overloading
the embedding and LLM models. Large diffs are truncated with warning.
"""

from __future__ import annotations


def truncate_diff(diff: str, max_lines: int = 3000) -> tuple[str, bool]:
    """Truncate diff if it exceeds max_lines.

    Args:
        diff: The unified diff text.
        max_lines: Maximum number of lines to retain (default 3000).

    Returns:
        Tuple of (processed_diff, was_truncated).
        If truncated, appends warning comment.
    """
    lines = diff.split("\n")

    if len(lines) <= max_lines:
        return diff, False

    # Truncate and add warning
    truncated_lines = lines[:max_lines]
    warning = "# [oute-muscle] Diff truncated at 3000 lines. Full analysis may be incomplete."
    truncated_lines.append(warning)
    processed_diff = "\n".join(truncated_lines)

    return processed_diff, True
