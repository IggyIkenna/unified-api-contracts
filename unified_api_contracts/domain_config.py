"""
Domain Configuration Protocols

Protocol definitions for domain configuration objects used across unified-trading-library.
Eliminates type errors from optional unified-config-interface dependency.

NOTE (2026-03-09): All four Protocol classes (DomainConfigProtocol, DataTypeConfigProtocol,
ExchangeInstrumentConfigProtocol, MLConfigProtocol) were confirmed orphans — no downstream
repo imports them.  instruments-service and strategy-service reference the name only in
docstrings, not in import statements.  The classes have been removed.  If a consumer needs
structural typing against config objects, define a Protocol in that consumer's own module or
in unified-trading-library.
"""
