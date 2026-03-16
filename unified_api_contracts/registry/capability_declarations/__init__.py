"""Capability declaration sub-modules, split by source category."""

from __future__ import annotations

from ._altdata import ALTDATA_CAPABILITIES
from ._cefi import CEFI_CAPABILITIES
from ._defi import DEFI_CAPABILITIES
from ._sports import SPORTS_CAPABILITIES
from ._tradfi import TRADFI_CAPABILITIES

__all__ = [
    "ALTDATA_CAPABILITIES",
    "CEFI_CAPABILITIES",
    "DEFI_CAPABILITIES",
    "SPORTS_CAPABILITIES",
    "TRADFI_CAPABILITIES",
]
