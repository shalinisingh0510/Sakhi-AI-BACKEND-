from __future__ import annotations

import os

import uvicorn

from app.main import app


def main() -> None:
    port = int(os.getenv("PORT", "5000"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
