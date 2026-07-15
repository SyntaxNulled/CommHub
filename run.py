"""CommHub launcher — starts the server and opens the browser."""

import sys
import webbrowser
import uvicorn
from pathlib import Path


def main():
    if getattr(sys, "frozen", False):
        import app.config
        app.config.settings.debug = False

    from app.main import app
    from app.config import settings

    url = f"http://{settings.host}:{settings.port}"
    print(f"  == CommHub v{settings.app_version} ==")
    print(f"  Opening {url}")
    webbrowser.open(url)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
