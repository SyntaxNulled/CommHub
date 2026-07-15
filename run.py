"""CommHub launcher — starts the server, opens the browser once ready, and sets up the system tray."""

import sys
import threading
import time
import urllib.request
import webbrowser

import uvicorn


def _open_browser_when_ready(url: str, timeout: float = 15.0) -> None:
    """Poll /api/health and open the browser only once the server responds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=1):
                break
        except Exception:
            time.sleep(0.2)
    webbrowser.open(url)


def main():
    from app.main import app
    from app.config import settings

    url = f"http://{settings.host}:{settings.port}"
    print(f"  == CommHub v{settings.app_version} ==")
    print(f"  Serving on {url}")

    threading.Thread(target=_open_browser_when_ready, args=(url,), daemon=True).start()

    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    try:
        from app.tray import start_tray

        def quit_app():
            server.should_exit = True

        start_tray(url, on_quit=quit_app)
    except Exception:
        pass  # tray is optional — never block launch

    server.run()


if __name__ == "__main__":
    main()
