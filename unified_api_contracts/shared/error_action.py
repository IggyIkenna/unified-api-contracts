"""Error action classification for venue API errors.

Every venue error schema implements a .classify() classmethod that maps
a vendor error code to an ErrorAction, enabling consistent retry/reconnect
logic across all venue adapters.
"""

import enum


class ErrorAction(enum.Enum):
    """Action to take when a venue API error occurs."""

    RETRY_WITH_BACKOFF = "retry_backoff"
    """Transient server error or rate limit — retry with exponential backoff."""

    RECONNECT = "reconnect"
    """Session/token expired or WS connection must be rebuilt — reconnect and reauth."""

    FAIL_HARD = "fail_hard"
    """Permanent error (auth failure, invalid params, banned) — do not retry, raise immediately."""

    IGNORE = "ignore"
    """Duplicate request or no-op — log warning and continue."""
