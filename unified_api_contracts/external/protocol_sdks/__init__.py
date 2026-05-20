"""Protocol SDK schemas: AAVE, Morpho, Euler, Fluid, Lido, Curve, Compound, Uniswap, EtherFi.

This package contains SDK type stubs for DeFi protocols. It is NOT a data source --
it provides typed Pydantic wrappers around third-party protocol ABIs and REST APIs.
Kept in external/ (same rationale as external/defi/) because these schemas mirror
upstream protocol interfaces, not our canonical domain.
Used as a dependency by external/defi/schemas.py.
"""

from .schemas import *
