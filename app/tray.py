"""System tray icon for CommHub desktop app."""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path

try:
    import pystray
    from PIL import Image
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


def _load_icon():
    ico_path = Path(__file__).parent / "static" / "app.ico"
    if not ico_path.exists():
        ico_path = Path(__file__).parent.parent / "app.ico"
    if ico_path.exists():
        return Image.open(str(ico_path))
    img = Image.new("RGB", (64, 64), (37, 99, 235))
    return img


def _create_tray(url: str, on_quit):
    if not HAS_TRAY:
        return None

    icon = _load_icon()

    def on_open(icon, item):
        webbrowser.open(url)

    def on_quit_action(icon, item):
        icon.stop()
        on_quit()

    menu = pystray.Menu(
        pystray.MenuItem("Open CommHub", on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit_action),
    )

    tray = pystray.Icon("CommHub", icon, "CommHub", menu)
    return tray


def start_tray(url: str, on_quit=None) -> pystray.Icon | None:
    tray = _create_tray(url, on_quit or (lambda: None))
    if tray:
        t = threading.Thread(target=tray.run, daemon=True)
        t.start()
    return tray
