"""CommHub launcher — starts the server and opens the browser."""

import sys
import webbrowser
import uvicorn
from app.config import settings


def main():
    url = f"http://{settings.host}:{settings.port}"
    print(f"  🔄 CommHub v{settings.app_version}")
    print(f"  🌐 Opening {url}")
    webbrowser.open(url)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning",
    )


if __name__ == "__main__":
    main()
