# AGENTS.md — unified-api-contracts

## Quick Reference for AI Agents

### Key Commands

- **Quality gates**: `cd unified-api-contracts && bash scripts/quality-gates.sh`
- **Source dir**: `unified-api-contracts/unified_api_contracts/` (underscored)
- **Typecheck**: `run_timeout 120 basedpyright unified_api_contracts/`

### Mandatory Rules

Before any action, read:
`unified-trading-pm/cursor-configs/SUB_AGENT_MANDATORY_RULES.md`

### Rules Summary

- `uv pip install` not `pip install`
- Flat deps only — no `[project.optional-dependencies]`
- `basedpyright` not `pyright`
- `UnifiedCloudConfig` not `os.getenv()`
- No `# type: ignore` to hide architectural violations
- No `try/except ImportError` fallbacks
- Import surface: `from unified_api_contracts.{domain} import ...` only — never `canonical.*` or `normalize_utils.*`

### Workspace

WORKSPACE_ROOT: `/Users/ikennaigboaka/Code/unified-trading-system-repos`
