"""Run the API with: python -m graphite.api"""

from __future__ import annotations

import uvicorn

from ..config import get_settings
from .app import create_app

app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()
