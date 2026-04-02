"""API-Football player name → canonical player ID normalization.

Canonical player IDs follow the ``LASTNAME_INITIAL`` or ``LASTNAME_FIRSTNAME``
pattern:

- ``"J. Pickford"``      → ``"PICKFORD_J"``
- ``"Bruno Fernandes"``  → ``"FERNANDES_BRUNO"``
- ``"De Gea"``           → ``"DE_GEA"``
- ``"G. Sigurðsson"``    → ``"SIGURDSSON_G"``

Diacritics are stripped via ``unicodedata.normalize("NFKD")``.

Source: Ported from footballbets/utils/mapping.py
"""

from __future__ import annotations

import re
import unicodedata


def get_canonical_player_name_from_api_football(
    player_name: str,
    player_id: int,
) -> str:
    """Convert API-Football player name to canonical player ID.

    Handles:
    - Accents / diacritics: ``"Müller"`` → ``"MULLER"``
    - Initial + surname: ``"J. Pickford"`` → ``"PICKFORD_J"``
    - Full name: ``"Bruno Fernandes"`` → ``"FERNANDES_BRUNO"``
    - Compound surname: ``"De Gea"`` → ``"DE_GEA"``
    - Fallback for empty / un-parseable names: ``"PLAYER_{player_id}"``

    Args:
        player_name: Player name as returned by the API-Football API.
        player_id: API-Football numeric player ID (used as fallback key).

    Returns:
        Canonical player ID in SCREAMING_SNAKE_CASE.
    """
    if not player_name:
        return f"PLAYER_{player_id}"

    # Strip diacritics: "Müller" → "Muller", "Sigurðsson" → "Sigurdsson"
    normalized = unicodedata.normalize("NFKD", player_name)
    ascii_name = "".join(c for c in normalized if not unicodedata.combining(c))

    # Remove special chars except spaces, periods, hyphens
    cleaned = re.sub(r"[^\w\s.\-]", "", ascii_name)

    parts = cleaned.split()

    if not parts:
        return f"PLAYER_{player_id}"

    # First part looks like an initial (1-2 chars, optional period)
    if len(parts) >= 2 and len(parts[0].replace(".", "")) <= 2:
        # "J. Pickford" → "PICKFORD_J"
        initial = parts[0].replace(".", "").upper()
        last_name = "_".join(parts[1:]).upper()
        return f"{last_name}_{initial}"

    if len(parts) == 1:
        return parts[0].upper()

    if len(parts) == 2:
        # "Bruno Fernandes" → "FERNANDES_BRUNO"
        return f"{parts[1].upper()}_{parts[0].upper()}"

    # 3+ parts: last 2 assumed compound surname, rest = first name
    # "Bruno Miguel Fernandes" → "FERNANDES_BRUNO"
    first_name = parts[0].upper()
    last_name = "_".join(parts[1:]).upper()
    return f"{last_name}_{first_name}"


def get_canonical_referee_name_from_api_football(
    referee_name: str,
    referee_id: int,
) -> str:
    """Convert API-Football referee name to canonical referee ID.

    Uses the same normalization as player names.

    Args:
        referee_name: Referee name from API-Football.
        referee_id: API-Football numeric referee ID (fallback).

    Returns:
        Canonical referee ID (e.g. ``"ATKINSON_M"``).
    """
    if not referee_name:
        return f"REFEREE_{referee_id}"
    return get_canonical_player_name_from_api_football(referee_name, referee_id)


__all__ = [
    "get_canonical_player_name_from_api_football",
    "get_canonical_referee_name_from_api_football",
]
