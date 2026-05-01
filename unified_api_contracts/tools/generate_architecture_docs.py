"""Auto-generated architecture-docs CLI (P4.11 -- workspace audit 2026-05-01).

Run::

    python -m unified_api_contracts.tools.generate_architecture_docs
    python -m unified_api_contracts.tools.generate_architecture_docs --out-dir docs/generated

Emits Markdown reports from the canonical UAC registries:

  * ``event_catalog.md``        -- ``EVENT_TOPIC_REGISTRY`` (topic / producer /
                                   consumers / replayable / retention)
  * ``service_contracts.md``    -- ``SERVICE_CONTRACT_MAP`` (owns / emits /
                                   consumes / forbidden imports + exceptions)
  * ``archetype_capability.md`` -- ``ARCHETYPE_CAPABILITY_REGISTRY`` (full cell grid)
  * ``asset_group_ontology.md`` -- ``ASSET_GROUP_ONTOLOGY`` (fill / settlement /
                                   margin model / venues / instrument types)
  * ``README.md``               -- short index linking the four above

Idempotent. Re-running with no upstream changes produces identical output
suitable for `git diff` checks in QG.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from unified_api_contracts.internal.architecture_v2.archetype_capability import (  # noqa: qg-deep-import
    ARCHETYPE_CAPABILITY_REGISTRY,
)
from unified_api_contracts.internal.event_topics import (  # noqa: qg-deep-import
    EVENT_TOPIC_REGISTRY,
)
from unified_api_contracts.registry.archetype_capability_matrix import (  # noqa: qg-deep-import
    ASSET_GROUP_ONTOLOGY,
)
from unified_api_contracts.registry.service_contract_map import (  # noqa: qg-deep-import
    SERVICE_CONTRACT_MAP,
)


def _write_event_catalog(out: TextIO) -> None:
    out.write("# Event topic catalog\n\n")
    out.write("Generated from ``unified_api_contracts.internal.event_topics.EVENT_TOPIC_REGISTRY``.\n\n")
    out.write("| event_type | topic | producer | consumers | replayable | retention (days) |\n")
    out.write("|---|---|---|---|---|---|\n")
    for event_type in sorted(EVENT_TOPIC_REGISTRY.keys()):
        spec = EVENT_TOPIC_REGISTRY[event_type]
        consumers = ", ".join(sorted(spec.consumers)) if spec.consumers else "—"
        out.write(
            f"| `{event_type}` | `{spec.topic}` | "
            f"`{spec.producer}` | {consumers} | "
            f"{'yes' if spec.replayable else 'no'} | {spec.retention_days} |\n"
        )
    out.write(f"\n**Total topics:** {len(EVENT_TOPIC_REGISTRY)}\n")


def _write_service_contracts(out: TextIO) -> None:
    out.write("# Service contract map\n\n")
    out.write("Generated from ``unified_api_contracts.registry.service_contract_map.SERVICE_CONTRACT_MAP``.\n\n")
    for service in sorted(SERVICE_CONTRACT_MAP.keys()):
        contract = SERVICE_CONTRACT_MAP[service]
        out.write(f"## `{service}`\n\n")
        out.write(f"- **owns**: {', '.join(sorted(contract.owns)) or '—'}\n")
        out.write(f"- **emits**: {', '.join(sorted(contract.emits)) or '—'}\n")
        out.write(f"- **consumes**: {', '.join(sorted(contract.consumes)) or '—'}\n")
        out.write(f"- **persists**: {', '.join(sorted(contract.persists)) or '—'}\n")
        forbidden_imports = sorted(contract.forbidden_imports)
        if forbidden_imports:
            out.write("- **forbidden_imports**:\n")
            for imp in forbidden_imports:
                out.write(f"  - `{imp}`\n")
        forbidden_exceptions = sorted(contract.forbidden_exceptions)
        if forbidden_exceptions:
            out.write("- **forbidden_exceptions** (carve-outs):\n")
            for exc in forbidden_exceptions:
                out.write(f"  - `{exc}`\n")
        out.write("\n")


def _write_archetype_capability(out: TextIO) -> None:
    out.write("# Archetype capability matrix\n\n")
    out.write(
        "Generated from "
        "``unified_api_contracts.internal.architecture_v2.archetype_capability."
        "ARCHETYPE_CAPABILITY_REGISTRY``.\n\n"
    )
    out.write("| archetype | family | asset_group | instrument_type | status | venues |\n")
    out.write("|---|---|---|---|---|---|\n")
    for row in ARCHETYPE_CAPABILITY_REGISTRY:
        for cell in row.cells:
            venues = ", ".join(cell.venue_ids) if cell.venue_ids else "—"
            out.write(
                f"| `{row.archetype_id.value}` | `{row.family.value}` | "
                f"`{cell.asset_group.value}` | `{cell.instrument_type.value}` | "
                f"{cell.status.value} | {venues} |\n"
            )
    out.write(f"\n**Archetypes:** {len(ARCHETYPE_CAPABILITY_REGISTRY)}\n")


def _write_asset_group_ontology(out: TextIO) -> None:
    out.write("# Asset-group ontology\n\n")
    out.write("Generated from ``unified_api_contracts.registry.archetype_capability_matrix.ASSET_GROUP_ONTOLOGY``.\n\n")
    for asset_group in sorted(ASSET_GROUP_ONTOLOGY.keys(), key=lambda g: g.value):
        ontology = ASSET_GROUP_ONTOLOGY[asset_group]
        out.write(f"## `{asset_group.value}`\n\n")
        out.write(f"- **state_model**: `{ontology.state_model}`\n")
        out.write(f"- **margin_model**: `{ontology.margin_model_name}`\n")
        out.write(
            f"- **fill_model**: `{ontology.fill_model.name}` "
            f"(slippage={ontology.fill_model.typical_slippage_bps}bps, "
            f"latency={ontology.fill_model.typical_latency_ms}ms, "
            f"commission={ontology.fill_model.commission_bps}bps)\n"
        )
        out.write(
            f"- **settlement_model**: `{ontology.settlement_model.name}` "
            f"(horizon={ontology.settlement_model.horizon}, "
            f"cash_currency={ontology.settlement_model.cash_currency})\n"
        )
        instrument_types = sorted(t.value for t in ontology.instrument_types)
        out.write(f"- **instrument_types**: {', '.join(instrument_types)}\n")
        venues = sorted(ontology.venues)
        out.write(f"- **venues**: {', '.join(venues)}\n")
        out.write(f"- **has_liquidations**: {ontology.has_liquidations}\n")
        out.write(f"- **has_funding**: {ontology.has_funding}\n\n")


def _write_index(out: TextIO) -> None:
    out.write("# Generated architecture docs\n\n")
    out.write("Auto-regenerated by ``python -m unified_api_contracts.tools.generate_architecture_docs``.\n\n")
    out.write("- [event_catalog.md](event_catalog.md) — Pub/Sub topics + producer/consumer wiring\n")
    out.write("- [service_contracts.md](service_contracts.md) — per-service ownership + boundaries\n")
    out.write("- [archetype_capability.md](archetype_capability.md) — full archetype x asset_group cell grid\n")
    out.write(
        "- [asset_group_ontology.md](asset_group_ontology.md) — fill / settlement / margin model per asset group\n"
    )


def _emit(path: Path, writer: object) -> None:
    """Open ``path``, call writer(file_handle), close. Path's parent is auto-created."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        writer(fh)  # type: ignore[operator]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Auto-generate architecture markdown docs from UAC registries.",
    )
    parser.add_argument(
        "--out-dir",
        default="docs/generated",
        help="Output directory (default: docs/generated). Path is repo-relative or absolute.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Emit the index to stdout instead of writing files (smoke-test mode).",
    )
    args = parser.parse_args(argv)

    if args.stdout:
        _write_index(sys.stdout)
        return 0

    out_dir = Path(args.out_dir)
    _emit(out_dir / "event_catalog.md", _write_event_catalog)
    _emit(out_dir / "service_contracts.md", _write_service_contracts)
    _emit(out_dir / "archetype_capability.md", _write_archetype_capability)
    _emit(out_dir / "asset_group_ontology.md", _write_asset_group_ontology)
    _emit(out_dir / "README.md", _write_index)
    sys.stdout.write(f"Wrote 5 files to {out_dir.resolve()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
