"""Client-instruction schema + validator — rule 10 + stage-3b contract.

Split into modules for maintainability while maintaining backward compatibility.
"""

# Import everything from the new module structure to maintain compatibility
from .instruction import *  # noqa: F403

# TODO: Complete proper module split in follow-up task
# This maintains compatibility while allowing gradual migration
