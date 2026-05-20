"""Schema for the trading-agent-service inference cache contract.

Every external API call output (Anthropic SDK response, ML inference) is
persisted under this schema so backtest replay can substitute live calls with
cached outputs, eliminating forward-looking bias.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AgentInferenceCacheRecord(BaseModel):
    input_hash: str = Field(description="SHA-256 of the serialised input to the external call")
    model_id: str = Field(description="Model identifier, e.g. 'claude-opus-4-7' or 'ml-feature-v2'")
    mode_used: str = Field(description="Mode during which this call was made: live | paper | backtest_continuation")
    output_bytes: bytes = Field(description="Serialised output bytes (JSON-encoded response body)")
    timestamp_called: datetime = Field(description="UTC timestamp when the live call was made")
    available_at: datetime = Field(description="Write-time timestamp per per-row available_at rule")
