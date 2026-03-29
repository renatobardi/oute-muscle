"""Root conftest — polyfills for running the test suite on Python < 3.11.

The codebase targets Python 3.12+ but CI sandbox may use 3.10.
This conftest patches ``datetime.UTC`` and ``enum.StrEnum`` at import
time so every test module that does ``from datetime import UTC`` or
``from enum import StrEnum`` works regardless of runtime version.

These patches are harmless no-ops on Python 3.11+.
"""

from __future__ import annotations

import datetime
import enum
import sys

# ---------------------------------------------------------------------------
# datetime.UTC  (added in 3.11)
# ---------------------------------------------------------------------------
if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.timezone.utc  # type: ignore[attr-defined]  # noqa: UP017

# ---------------------------------------------------------------------------
# enum.StrEnum  (added in 3.11)
# ---------------------------------------------------------------------------
if not hasattr(enum, "StrEnum"):

    class _StrEnum(str, enum.Enum):  # noqa: UP042
        """Minimal StrEnum backport for Python < 3.11."""

        pass

    enum.StrEnum = _StrEnum  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Ensure the patched modules are visible to subsequent imports
# ---------------------------------------------------------------------------
sys.modules["datetime"] = datetime
sys.modules["enum"] = enum
