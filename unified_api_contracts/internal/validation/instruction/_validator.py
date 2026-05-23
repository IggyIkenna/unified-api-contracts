"""Main instruction validator implementation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ArchetypeCapability,
    archetypes_for_pair,
)

from ._main_models import (
    ClientInstruction,
    InstructionFieldError,
    InstructionValidationResult,
)
from ._nested_models import InstrumentVenueContext
from ._scoring import compute_integration_depth


class InstructionValidator:
    """Stateless stage-3b-contract validator.

    ``validate()`` is the single entry point — called by the
    execution-service pre-handler middleware. All methods are pure
    functions of their arguments; construction is cheap.

    Heavy work (archetype lookup) goes through the module-level
    ``archetypes_for_pair()`` helper which consults the frozen
    ``ARCHETYPE_CAPABILITY_REGISTRY`` from G1.8.
    """

    def validate(self, instruction: ClientInstruction) -> InstructionValidationResult:
        """Return a pass/fail result for a (pre-parsed) ClientInstruction.

        Parse errors are the caller's responsibility — the middleware
        catches ``pydantic.ValidationError`` from ``model_validate`` and
        translates it into ``InstructionFieldError`` rows itself (see
        :meth:`errors_from_pydantic`). This entry point assumes a
        well-shaped :class:`ClientInstruction` and focuses on
        cross-field business rules:

        1. Is the (asset_group, instrument_type) pair declared SUPPORTED
           or PARTIAL by any registered archetype?
        2. Is the chosen venue in any matching archetype's
           ``supported_venues``?
        3. If ATOMIC, do the legs map onto a cell flagged ATOMIC-capable?

        On success — return ok=True with an
        ``integration_depth`` score. On failure — return ok=False with
        one :class:`InstructionFieldError` per violation.
        """

        errors: list[InstructionFieldError] = []
        ctx = instruction.instrument_venue_context

        matching = archetypes_for_pair(
            ctx.asset_group,
            ctx.instrument_type,
            include_partial=True,
        )
        pair_error = self._validate_pair(ctx, matching)
        if pair_error is not None:
            errors.append(pair_error)

        if matching:
            venue_error = self._validate_venue(ctx, matching)
            if venue_error is not None:
                errors.append(venue_error)

        if errors:
            return InstructionValidationResult(
                ok=False,
                integration_depth=0.0,
                errors=tuple(errors),
            )

        return InstructionValidationResult(
            ok=True,
            integration_depth=compute_integration_depth(instruction),
            errors=(),
        )

    @staticmethod
    def _validate_pair(
        ctx: InstrumentVenueContext,
        matching: Sequence[ArchetypeCapability],
    ) -> InstructionFieldError | None:
        """Pair must be declared SUPPORTED or PARTIAL by some archetype."""

        if matching:
            return None
        return InstructionFieldError(
            field="instrument_venue_context.asset_group+instrument_type",
            violation=(f"no registered archetype supports ({ctx.asset_group.value}, {ctx.instrument_type.value})"),
            allowed=_allowed_pairs_digest(),
            why=(
                "UAC ArchetypeCapabilityRegistry has zero SUPPORTED or PARTIAL "
                "cells for this pair — routing would land in a BL-* block-list "
                "group (see codex/09-strategy/architecture-v2/"
                "category-instrument-coverage.md)."
            ),
        )

    @staticmethod
    def _validate_venue(
        ctx: InstrumentVenueContext,
        matching: Sequence[ArchetypeCapability],
    ) -> InstructionFieldError | None:
        """Venue must be in supported_venues of at least one matching archetype."""

        allowed_venues: set[str] = set()
        for archetype in matching:
            allowed_venues.update(archetype.supported_venues)
        if ctx.venue in allowed_venues:
            return None
        return InstructionFieldError(
            field="instrument_venue_context.venue",
            violation=(
                f"venue {ctx.venue!r} not in supported_venues for any "
                f"archetype covering ({ctx.asset_group.value}, "
                f"{ctx.instrument_type.value})"
            ),
            allowed=tuple(sorted(allowed_venues)),
            why=(
                "Venue must appear in at least one non-BLOCKED cell of a "
                "matching ArchetypeCapability row. Check "
                "archetype_capability_manifest.json for the authoritative "
                "venue list."
            ),
        )

    @staticmethod
    def errors_from_pydantic(
        pydantic_errors: Sequence[dict[str, object]],
    ) -> tuple[InstructionFieldError, ...]:
        """Translate ``pydantic.ValidationError.errors()`` output.

        Utility for middleware that does ``ClientInstruction.model_validate``
        on the raw payload and catches ``ValidationError``. Each pydantic
        row becomes one :class:`InstructionFieldError` so the caller can
        return a uniformly-shaped 400 regardless of whether the failure
        came from structural parsing or business-rule validation.
        """

        out: list[InstructionFieldError] = []
        for err in pydantic_errors:
            loc_raw: object = err.get("loc", ())
            if isinstance(loc_raw, tuple | list):
                parts = cast("tuple[object, ...] | list[object]", loc_raw)
                field_path = ".".join(str(part) for part in parts)
            else:
                field_path = str(loc_raw)
            msg = str(err.get("msg", "validation failed"))
            err_type = str(err.get("type", "value_error"))
            out.append(
                InstructionFieldError(
                    field=field_path or "<root>",
                    violation=msg,
                    allowed=(),
                    why=(
                        "Pydantic-layer rejection — see stage-3b §2 for the authoritative "
                        f"field contract. Error type: {err_type}."
                    ),
                ),
            )
        return tuple(out)


def _allowed_pairs_digest() -> tuple[str, ...]:
    """Deterministic flat list of (asset_group, instrument_type) pair names.

    Used in error copy so clients see a concrete allowed-value hint
    without pulling the full manifest in. Non-exhaustive on purpose —
    the manifest is the SSOT.
    """

    # Hand-picked representative pairs — ordered, deduplicated.
    return (
        "CEFI:spot",
        "CEFI:perp",
        "CEFI:option",
        "CEFI:dated_future",
        "DEFI:spot",
        "DEFI:perp",
        "DEFI:lending",
        "DEFI:staking",
        "DEFI:lp",
        "TRADFI:spot",
        "TRADFI:option",
        "TRADFI:dated_future",
        "SPORTS:event_settled",
        "PREDICTION:event_settled",
    )


__all__ = [
    "InstructionValidator",
]
