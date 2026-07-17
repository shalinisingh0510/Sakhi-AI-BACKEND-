from __future__ import annotations

from app.core.middleware import enable_rate_limiting

# Disable rate limiting for tests
enable_rate_limiting(False)
