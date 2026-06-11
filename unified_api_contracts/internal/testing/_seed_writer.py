"""Seed-data parquet/JSON output writer + instrument-key helper.

Split out of :mod:`unified_api_contracts.internal.testing.synthetic`
(2026-06-11 >900-line ratchet): generation (``SyntheticDataGenerator``) stays
in ``synthetic``; persistence (``SeedDataWriter`` + ``_df_to_parquet``) and
the ``build_instrument_key`` helper live here.

Import surface is UNCHANGED for consumers: every name here is re-exported by
``synthetic`` (and the internal facade) — import from there.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Instrument definitions generator
# ---------------------------------------------------------------------------


def build_instrument_key(venue: str, symbol: str, instrument_type: str = "SPOT_PAIR") -> str:
    """Return canonical instrument_key in VENUE:TYPE:SYMBOL format."""
    clean_symbol = symbol.replace("/", "").replace("-", "")
    return f"{venue.upper()}:{instrument_type}:{clean_symbol}"


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------


def _df_to_parquet(df: pd.DataFrame, out_path: Path) -> None:
    """Write a DataFrame to a Parquet file (snappy compression).

    Isolated helper so pyarrow unknown-type errors are contained to one place.
    """
    table: object = pa.Table.from_pandas(  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        df, preserve_index=False
    )
    pq.write_table(table, out_path, compression="snappy")  # pyright: ignore[reportUnknownMemberType,reportArgumentType]


class SeedDataWriter:
    """Writes seed data to Parquet files organised by partition template."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def write_ohlcv(self, df: pd.DataFrame, symbol: str, venue: str) -> Path:
        """Write OHLCV parquet file partitioned by symbol/YYYY/MM/DD."""
        if df.empty:
            log.warning("Empty OHLCV dataframe for %s/%s — skipping", venue, symbol)
            return self._output_dir
        clean_symbol = symbol.replace("/", "_").replace("-", "_")
        min_date = pd.to_datetime(df["timestamp"]).min()
        year = min_date.year
        month = f"{min_date.month:02d}"
        day = f"{min_date.day:02d}"
        out_dir = self._output_dir / "ohlcv" / clean_symbol / str(year) / month / day
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "data.parquet"
        _df_to_parquet(df, out_path)
        log.info("Wrote %d rows → %s", len(df), out_path)
        return out_path

    def write_tick(self, df: pd.DataFrame, symbol: str, venue: str) -> Path:
        """Write tick trades parquet file."""
        if df.empty:
            log.warning("Empty tick dataframe for %s/%s — skipping", venue, symbol)
            return self._output_dir
        clean_symbol = symbol.replace("/", "_").replace("-", "_")
        out_dir = self._output_dir / "tick" / venue / clean_symbol
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "data.parquet"
        _df_to_parquet(df, out_path)
        log.info("Wrote %d tick rows → %s", len(df), out_path)
        return out_path

    def write_defi(self, df: pd.DataFrame, protocol: str, asset: str) -> Path:
        """Write DeFi yield series parquet file."""
        if df.empty:
            log.warning("Empty DeFi dataframe for %s/%s — skipping", protocol, asset)
            return self._output_dir
        out_dir = self._output_dir / "defi" / protocol / asset
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "yields.parquet"
        _df_to_parquet(df, out_path)
        log.info("Wrote %d DeFi rows → %s", len(df), out_path)
        return out_path

    def write_sports(self, df: pd.DataFrame, league: str, venue: str) -> Path:
        """Write sports odds parquet file."""
        if df.empty:
            log.warning("Empty sports dataframe for %s/%s — skipping", venue, league)
            return self._output_dir
        out_dir = self._output_dir / "sports" / venue / league
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "odds.parquet"
        _df_to_parquet(df, out_path)
        log.info("Wrote %d sports rows → %s", len(df), out_path)
        return out_path

    def write_orderbook(self, snapshots: list[dict[str, Any]], symbol: str, venue: str) -> Path:
        """Write orderbook snapshots to a JSON file."""
        if not snapshots:
            log.warning("Empty orderbook snapshots for %s/%s — skipping", venue, symbol)
            return self._output_dir
        clean_symbol = symbol.replace("/", "_").replace("-", "_")
        out_dir = self._output_dir / "orderbook" / venue / clean_symbol
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "snapshots.json"
        out_path.write_text(json.dumps(snapshots, indent=2, default=str))
        log.info("Wrote %d orderbook snapshots → %s", len(snapshots), out_path)
        return out_path

    def write_manifest(self, manifest: dict[str, Any]) -> Path:
        """Write a JSON manifest summarising all generated files."""
        out_path = self._output_dir / "seed_manifest.json"
        out_path.write_text(json.dumps(manifest, indent=2, default=str))
        log.info("Manifest written → %s", out_path)
        return out_path
