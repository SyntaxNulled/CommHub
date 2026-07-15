"""Build CommHub standalone executable with PyInstaller."""

import subprocess
import sys


def main():
    print("=== CommHub Builder ===")

    print("[1/3] Generating icon...")
    subprocess.run([sys.executable, "build_icon.py"], check=True)

    print("[2/3] Running PyInstaller...")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "commhub.spec"],
        check=True,
    )

    print("[3/3] Done!")
    print("  Executable: dist/commhub.exe")
    print("  Run: dist/commhub.exe")


if __name__ == "__main__":
    main()
