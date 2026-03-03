# Testing

How to run tests and use VCR in unified-api-contracts.

## Running tests

- **Setup**: `bash scripts/setup.sh` or `make setup` (see [README — Development Setup](../README.md#development-setup)).
- **Quality gates** (lint, typecheck, tests): `bash scripts/quality-gates.sh` (or `--no-fix` for CI).
- **Tests only**: `uv run pytest tests/` (or `make test` if defined in Makefile).
- **Schema coverage**: `tests/test_venue_contract_coverage.py`, `tests/test_contracts_vs_reality.py`; schema validation in `tests/test_schema_validation.py`.

## VCR (record and replay)

- **Record cassettes**: Done in the **six interfaces** (unified-market-interface, unified-trade-execution-interface, unified-sports-execution-interface, unified-reference-data-interface, unified-position-interface, unified-cloud-interface); they hold API keys. AC does not run recording scripts.
- **Replay**: In AC, tests use cassettes under `unified_api_contracts/<venue>/mocks/`; CI runs replay only (no live requests). See [docs/MOCKS_AND_VCR.md](MOCKS_AND_VCR.md) for cassette layout, secret filtering, and per-venue notes.
- **VCR ↔ schema alignment**: [docs/VCR_SCHEMA_ALIGNMENT.md](VCR_SCHEMA_ALIGNMENT.md).

## References

- [README — Self-test: schemas and coverage](../README.md#self-test-schemas-and-coverage)
- [docs/API_CONTRACTS_CHAIN_OF_EVENTS.md](API_CONTRACTS_CHAIN_OF_EVENTS.md)
- [CONTRIBUTING.md](../CONTRIBUTING.md)
