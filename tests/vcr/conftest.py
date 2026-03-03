"""VCR replay tests: marked integration so default run stays fast (no I/O to cassettes)."""

import pytest

pytestmark = pytest.mark.integration
