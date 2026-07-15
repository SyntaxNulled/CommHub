"""CommHub launcher — starts the server, opens the browser, and sets up system tray."""

import sys
import signal
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

    try:
        from app.tray import start_tray
        start_tray(url, on_quit=lambda: signal.raise_signal(signal.SIGINT))
    except ImportError:
        pass

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
